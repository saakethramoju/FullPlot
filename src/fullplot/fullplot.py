from __future__ import annotations

import builtins
import itertools
import posixpath
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from scipy.signal import butter, medfilt, savgol_filter, sosfiltfilt

from fullplot.hdf5 import hdf5_filename, safe_group_name
from fullplot.themes import (
    apply_theme,
    check_theme,
    grid_kwargs,
    style_colorbar,
    style_legend,
    theme_colors,
    theme_settings,
)


class FullPlotError(Exception):
    """Base exception for FullPlot errors."""


class DatasetNotFoundError(FullPlotError):
    """Raised when a dataset or group cannot be found."""


class AmbiguousDatasetError(FullPlotError):
    """Raised when a short dataset or group name matches more than one object."""


class PlotDataError(FullPlotError):
    """Raised when selected data cannot be plotted."""


@dataclass
class LineSeries:
    data: np.ndarray
    label: str
    length: int
    x: np.ndarray | None = None
    role: str = "data"


def _as_1d_numeric_array(values, name: str, omit_nonfinite: bool = False) -> np.ndarray:
    array = np.asarray(values, dtype=float)

    if array.ndim != 1:
        raise PlotDataError(f"{name} must be one-dimensional.")

    if array.size == 0:
        raise PlotDataError(f"{name} cannot be empty.")

    if omit_nonfinite:
        array = array[np.isfinite(array)]

        if array.size == 0:
            raise PlotDataError(f"{name} has no finite values.")

    return array


def _omit_nonfinite_xy(x, y, name: str) -> tuple[np.ndarray, np.ndarray]:
    x_array = np.asarray(x, dtype=float)
    y_array = np.asarray(y, dtype=float)

    if x_array.ndim != 1 or y_array.ndim != 1:
        raise PlotDataError(f"{name} must be one-dimensional after selection.")

    if x_array.shape != y_array.shape:
        raise PlotDataError(
            f"{name} has mismatched x and y lengths: "
            f"{len(x_array)} and {len(y_array)}."
        )

    mask = np.isfinite(x_array) & np.isfinite(y_array)

    if not np.any(mask):
        raise PlotDataError(f"{name} has no finite x/y pairs to plot.")

    return x_array[mask], y_array[mask]


def _odd_window_count(count: int, minimum: int = 3) -> int:
    count = int(count)
    count = max(count, minimum)

    if count % 2 == 0:
        count += 1

    return count


def _trace_window_count(x: np.ndarray, window, minimum: int = 3) -> int:
    if window is None:
        raise ValueError("filter window must be provided for this filter.")

    if isinstance(window, (int, np.integer)):
        return _odd_window_count(int(window), minimum=minimum)

    window = float(window)

    if window <= 0.0:
        raise ValueError("filter window must be positive.")

    if x.size < 2:
        return _odd_window_count(1, minimum=minimum)

    dx = np.median(np.diff(x))

    if dx <= 0.0 or not np.isfinite(dx):
        raise ValueError("time-based filter windows require a strictly increasing x array.")

    return _odd_window_count(round(window / dx), minimum=minimum)


def _role_color(role: str, theme: str):
    role = str(role or "data").lower().strip()
    theme = check_theme(theme)

    role_colors = {
        "dark": {
            "redline": "#ff7a7a",
            "blueline": "#7ab8ff",
            "yellowline": "#ffd36a",
            "amberline": "#ffd36a",
            "warning": "#ffd36a",
            "greenline": "#6aff9a",
        },
        "light": {
            "redline": "#7f1d1d",
            "blueline": "#245a9a",
            "yellowline": "#a87900",
            "amberline": "#a87900",
            "warning": "#a87900",
            "greenline": "#1c6b3f",
        },
    }

    return role_colors[theme].get(role)


def _line_style_for_role(role: str, theme: str, color, linewidth: float) -> dict:
    role = str(role or "data").lower().strip()
    line_color = _role_color(role, theme)

    if role in {"redline", "blueline", "yellowline", "amberline", "warning", "greenline"}:
        return {
            "color": line_color,
            "linestyle": "--",
            "linewidth": 1.15 * linewidth,
            "alpha": 0.95,
        }

    if role == "filtered":
        return {"color": color, "linestyle": "--", "linewidth": linewidth}

    if role == "command":
        return {"color": color, "linestyle": "-", "linewidth": linewidth, "drawstyle": "steps-post"}

    return {"color": color, "linestyle": "-", "linewidth": linewidth}


@dataclass
class Trace:
    """A prepared one-dimensional line of data.

    A Trace is intentionally generic. It can represent simulation output, test
    data, a filtered signal, a command, a redline, a blueline, or any other
    one-dimensional data series. FullPlot uses it for overlaying data from
    different files and for generated lines that do not already exist in HDF5.
    """

    x: np.ndarray
    y: np.ndarray
    name: str = "trace"
    role: str = "data"
    attrs: dict[str, Any] | None = None

    def __post_init__(self):
        self.x = _as_1d_numeric_array(self.x, "Trace x")
        self.y = _as_1d_numeric_array(self.y, "Trace y")

        if self.x.shape != self.y.shape:
            raise PlotDataError(
                f"Trace x and y must have the same length. "
                f"Received {len(self.x)} and {len(self.y)}."
            )

        mask = np.isfinite(self.x) & np.isfinite(self.y)

        if not np.any(mask):
            raise PlotDataError("Trace has no finite x/y pairs.")

        self.x = self.x[mask]
        self.y = self.y[mask]

        self.name = str(self.name)
        self.role = str(self.role or "data")
        self.attrs = {} if self.attrs is None else dict(self.attrs)

    @property
    def time(self) -> np.ndarray:
        return self.x

    @property
    def value(self) -> np.ndarray:
        return self.y

    @classmethod
    def from_arrays(cls, name: str, x, y, role: str = "data", **attrs) -> "Trace":
        return cls(x=np.asarray(x, dtype=float), y=np.asarray(y, dtype=float), name=name, role=role, attrs=attrs)

    @classmethod
    def constant(cls, name: str, x, y: float, role: str = "data", **attrs) -> "Trace":
        x_array = _as_1d_numeric_array(x, "Trace x", omit_nonfinite=True)
        return cls(x=x_array, y=np.full_like(x_array, float(y), dtype=float), name=name, role=role, attrs=attrs)

    @classmethod
    def from_points(cls, name: str, points, x=None, mode: str = "linear", role: str = "data", **attrs) -> "Trace":
        points = np.asarray(points, dtype=float)

        if points.ndim != 2 or points.shape[1] != 2:
            raise PlotDataError("points must be an array-like sequence of (x, y) pairs.")

        finite_points = np.isfinite(points).all(axis=1)
        points = points[finite_points]

        if points.size == 0:
            raise PlotDataError("points must contain at least one finite (x, y) pair.")

        xp = points[:, 0]
        yp = points[:, 1]
        order = np.argsort(xp)
        xp = xp[order]
        yp = yp[order]

        if x is None:
            x_array = xp
        else:
            x_array = _as_1d_numeric_array(x, "Trace x", omit_nonfinite=True)

        mode = str(mode).lower().strip()

        if mode == "linear":
            y_array = np.interp(x_array, xp, yp)
        elif mode in {"previous", "step", "steps-post", "hold"}:
            indices = np.searchsorted(xp, x_array, side="right") - 1
            indices = np.clip(indices, 0, len(yp) - 1)
            y_array = yp[indices]
        else:
            raise ValueError("mode must be 'linear' or 'previous'.")

        return cls(x=x_array, y=y_array, name=name, role=role, attrs=attrs)

    @classmethod
    def from_function(cls, name: str, x, function, role: str = "data", **attrs) -> "Trace":
        x_array = _as_1d_numeric_array(x, "Trace x", omit_nonfinite=True)
        y_array = np.asarray(function(x_array), dtype=float)
        return cls(x=x_array, y=y_array, name=name, role=role, attrs=attrs)

    def copy(self, name: str | None = None, role: str | None = None, **attrs) -> "Trace":
        merged_attrs = dict(self.attrs)
        merged_attrs.update(attrs)
        return Trace(
            x=self.x.copy(),
            y=self.y.copy(),
            name=self.name if name is None else name,
            role=self.role if role is None else role,
            attrs=merged_attrs,
        )

    def window(self, start: float | None = None, stop: float | None = None, name: str | None = None) -> "Trace":
        mask = np.ones_like(self.x, dtype=bool)

        if start is not None:
            mask &= self.x >= float(start)

        if stop is not None:
            mask &= self.x <= float(stop)

        return Trace(x=self.x[mask], y=self.y[mask], name=self.name if name is None else name, role=self.role, attrs=self.attrs)

    def filter(self, method: str = "moving_average", window=None, order: int = 2, cutoff: float | None = None, name: str | None = None) -> "Trace":
        method = str(method).lower().strip().replace("-", "_").replace(" ", "_")

        if method in {"moving_average", "mean", "average"}:
            count = _trace_window_count(self.x, window, minimum=1)
            kernel = np.ones(count, dtype=float) / count
            y = np.convolve(self.y, kernel, mode="same")

        elif method in {"median", "median_filter"}:
            count = _trace_window_count(self.x, window, minimum=3)
            y = medfilt(self.y, kernel_size=count)

        elif method in {"savgol", "savitzky_golay", "savitzky-golay"}:
            count = _trace_window_count(self.x, window, minimum=int(order) + 2)
            if count <= order:
                count = _odd_window_count(order + 2, minimum=order + 2)
            if count > len(self.y):
                count = _odd_window_count(len(self.y) if len(self.y) % 2 else len(self.y) - 1, minimum=3)
            y = savgol_filter(self.y, window_length=count, polyorder=int(order), mode="interp")

        elif method in {"lowpass", "low_pass"}:
            if cutoff is None:
                raise ValueError("lowpass filtering requires cutoff in Hz or cycles per x-unit.")
            if self.x.size < 2:
                raise PlotDataError("lowpass filtering requires at least two samples.")
            dx = np.median(np.diff(self.x))
            if dx <= 0.0 or not np.isfinite(dx):
                raise ValueError("lowpass filtering requires a strictly increasing x array.")
            fs = 1.0 / dx
            normalized_cutoff = float(cutoff) / (0.5 * fs)
            if not 0.0 < normalized_cutoff < 1.0:
                raise ValueError("lowpass cutoff must be between 0 and the Nyquist frequency.")
            sos = butter(N=4, Wn=normalized_cutoff, btype="lowpass", output="sos")
            y = sosfiltfilt(sos, self.y)

        else:
            raise ValueError("Unsupported filter method. Use moving_average, median, savgol, or lowpass.")

        attrs = dict(self.attrs)
        attrs.update({"filter": method, "window": window, "order": order, "cutoff": cutoff, "source": self.name})

        return Trace(
            x=self.x.copy(),
            y=np.asarray(y, dtype=float),
            name=(self.name + " filtered") if name is None else name,
            role="filtered",
            attrs=attrs,
        )

    def scale(self, factor: float, name: str | None = None) -> "Trace":
        return Trace(x=self.x.copy(), y=self.y * float(factor), name=self.name if name is None else name, role=self.role, attrs=self.attrs)

    def offset(self, value: float, name: str | None = None) -> "Trace":
        return Trace(x=self.x.copy(), y=self.y + float(value), name=self.name if name is None else name, role=self.role, attrs=self.attrs)

    def derivative(self, name: str | None = None) -> "Trace":
        return Trace(x=self.x.copy(), y=np.gradient(self.y, self.x), name=(self.name + " derivative") if name is None else name, role=self.role, attrs=self.attrs)

    def resample(self, x, name: str | None = None) -> "Trace":
        x_array = _as_1d_numeric_array(x, "resample x", omit_nonfinite=True)
        return Trace(x=x_array, y=np.interp(x_array, self.x, self.y), name=self.name if name is None else name, role=self.role, attrs=self.attrs)

    def _binary_operation(self, other, operation, symbol: str) -> "Trace":
        if isinstance(other, Trace):
            other_y = other.resample(self.x).y
            name = f"{self.name} {symbol} {other.name}"
        else:
            other_y = other
            name = f"{self.name} {symbol} {other}"

        return Trace(x=self.x.copy(), y=operation(self.y, other_y), name=name, role="derived", attrs={"left": self.name, "operation": symbol})

    def __add__(self, other):
        return self._binary_operation(other, np.add, "+")

    def __sub__(self, other):
        return self._binary_operation(other, np.subtract, "-")

    def __mul__(self, other):
        return self._binary_operation(other, np.multiply, "*")

    def __truediv__(self, other):
        return self._binary_operation(other, np.divide, "/")


def _is_numeric_dtype(dtype) -> bool:
    try:
        return np.issubdtype(dtype, np.number)
    except TypeError:
        return False


def _shape_string(shape) -> str:
    if shape == ():
        return "scalar"

    return str(shape)


def _clean_root(root: str) -> str:
    root = str(root).strip()

    if root == "":
        root = "/"

    if not root.startswith("/"):
        root = "/" + root

    root = posixpath.normpath(root)

    if root == ".":
        root = "/"

    return root


def _join_h5(root: str, name: str) -> str:
    root = _clean_root(root)
    name = str(name).strip()

    if name.startswith("/"):
        return posixpath.normpath(name)

    if root == "/":
        return posixpath.normpath("/" + name)

    return posixpath.normpath(root + "/" + name)


def _basename(path: str) -> str:
    path = str(path).rstrip("/")

    if path == "":
        return ""

    return path.split("/")[-1]


def _relative_path(path: str, root: str) -> str:
    path = _clean_root(path)
    root = _clean_root(root)

    if root == "/":
        return path.lstrip("/")

    prefix = root.rstrip("/") + "/"

    if path.startswith(prefix):
        return path[len(prefix):]

    return path


def _normalize_name(name: str) -> str:
    name = str(name).lower().strip()

    for char in [" ", "\t", "\n", "\r", "_", "-", "[", "]", "(", ")", "{", "}", ".", ",", "/"]:
        name = name.replace(char, "")

    return name


def _as_list(value) -> builtins.list:
    if value is None:
        return []

    if isinstance(value, (builtins.list, tuple)):
        return builtins.list(value)

    return [value]


def _decode_scalar(value):
    if isinstance(value, bytes):
        return value.decode(errors="replace")

    if isinstance(value, np.generic):
        return value.item()

    return value


def _check_scale(scale: str) -> str:
    scale = str(scale).lower().strip()

    if scale not in ("linear", "log"):
        raise ValueError("scale must be either 'linear' or 'log'.")

    return scale


def _check_log_positive(values, name: str):
    values = np.asarray(values)

    if values.size == 0:
        raise PlotDataError(f"{name} is empty and cannot be plotted on a log scale.")

    finite_values = values[np.isfinite(values)]

    if finite_values.size == 0:
        raise PlotDataError(f"{name} has no finite values and cannot be plotted on a log scale.")

    if np.any(finite_values <= 0.0):
        raise PlotDataError(f"{name} contains zero or negative values and cannot be plotted on a log scale.")


def _apply_plot_scales(ax, ax2, x_array, left_series, right_series, xscale, yscale, y2scale):
    xscale = _check_scale(xscale)
    yscale = _check_scale(yscale)
    y2scale = _check_scale(y2scale)

    all_series = builtins.list(left_series) + builtins.list(right_series)

    if xscale == "log":
        if x_array is not None:
            _check_log_positive(x_array, "x")

        for series in all_series:
            if series.x is not None:
                _check_log_positive(series.x, f"x for {series.label}")

    if yscale == "log":
        for series in left_series:
            _check_log_positive(series.data, series.label)

    if y2scale == "log":
        for series in right_series:
            _check_log_positive(series.data, series.label)

    ax.set_xscale(xscale)
    ax.set_yscale(yscale)

    if ax2 is not None:
        ax2.set_yscale(y2scale)


def _normalize_axis(axis: int, ndim: int) -> int:
    axis = int(axis)

    if ndim <= 0:
        raise PlotDataError("Cannot select an axis from scalar data.")

    if axis < 0:
        axis += ndim

    if axis < 0 or axis >= ndim:
        raise PlotDataError(f"axis {axis} is out of range for array with {ndim} dimensions.")

    return axis


def _is_integer_index(value) -> bool:
    return isinstance(value, (int, np.integer))


def _normalize_slice_spec(slice_spec, ndim: int) -> dict[int, object]:
    if slice_spec is None:
        return {}

    if not isinstance(slice_spec, dict):
        raise PlotDataError("slice must be a dictionary such as {0: 3} or {2: (0, 10)}.")

    normalized = {}

    for axis, value in slice_spec.items():
        axis = int(axis)

        if axis < 0:
            axis += ndim

        if axis < 0 or axis >= ndim:
            raise PlotDataError(f"slice axis {axis} is out of range for array with {ndim} dimensions.")

        normalized[axis] = value

    return normalized


def _to_numpy_index(value):
    if isinstance(value, builtins.slice):
        return value

    if isinstance(value, tuple) or isinstance(value, builtins.list):
        if len(value) == 2:
            return builtins.slice(value[0], value[1])

        if len(value) == 3:
            return builtins.slice(value[0], value[1], value[2])

        raise PlotDataError("slice tuple/list values must have length 2 or 3.")

    return value


def _apply_slice_for_lines(array: np.ndarray, axis: int, slice_spec) -> tuple[np.ndarray, int]:
    array = np.asarray(array)

    if array.ndim == 0:
        raise PlotDataError("Cannot line-plot scalar data.")

    original_axis = _normalize_axis(axis, array.ndim)
    normalized_slice = _normalize_slice_spec(slice_spec, array.ndim)

    if original_axis in normalized_slice and _is_integer_index(normalized_slice[original_axis]):
        raise PlotDataError("The plotted axis cannot also be removed with an integer slice.")

    indexer = [builtins.slice(None)] * array.ndim

    for slice_axis, value in normalized_slice.items():
        indexer[slice_axis] = _to_numpy_index(value)

    sliced = array[tuple(indexer)]

    removed_before_axis = 0

    for slice_axis, value in normalized_slice.items():
        if slice_axis < original_axis and _is_integer_index(value):
            removed_before_axis += 1

    new_axis = original_axis - removed_before_axis

    return np.asarray(sliced), new_axis


def _apply_slice_for_map(array: np.ndarray, slice_spec) -> np.ndarray:
    array = np.asarray(array)

    if slice_spec is None:
        return array

    normalized_slice = _normalize_slice_spec(slice_spec, array.ndim)
    indexer = [builtins.slice(None)] * array.ndim

    for slice_axis, value in normalized_slice.items():
        indexer[slice_axis] = _to_numpy_index(value)

    return np.asarray(array[tuple(indexer)])


@dataclass
class H5File:
    filename: str | Path
    root: str = "/"

    def __post_init__(self):
        self.filename = str(self.filename)
        self.root = _clean_root(self.root)

    def at(self, group: str) -> "H5File":
        """
        Return a new H5File scoped to a specific HDF5 group.

        Example
        -------

        file = fplt.open("run.h5")
        run = file.at("/Pipe_Network/transient/runs/base")
        run.plot(x="time", y="tracks/Pipe_Mass_Flow_[kg_s]")
        """

        with h5py.File(self.filename, "r") as h5:
            group_path = self._resolve_group_path(h5, group)

        return H5File(self.filename, group_path)

    def tree(self, max_depth: int | None = None, print_output: bool = True) -> str:
        """
        Print the HDF5 tree under the current root.
        """

        with h5py.File(self.filename, "r") as h5:
            if self.root not in h5:
                raise DatasetNotFoundError(f"Root path {self.root!r} was not found in {self.filename!r}.")

            lines = [f"{Path(self.filename).name}:{self.root}"]

            root_object = h5[self.root]

            if isinstance(root_object, h5py.Dataset):
                lines.append(self._dataset_tree_line(root_object, prefix="└── "))
            else:
                self._append_tree_lines(
                    lines=lines,
                    group=root_object,
                    prefix="",
                    depth=0,
                    max_depth=max_depth,
                )

        text = "\n".join(lines)

        if print_output:
            print(text)

        return text

    def list(self, print_output: bool = True) -> str:
        """
        Print numeric and non-numeric datasets under the current root.
        """

        with h5py.File(self.filename, "r") as h5:
            paths = self._dataset_paths(h5)

            one_d = []
            two_d = []
            multi_d = []
            scalars = []
            non_numeric = []

            for path in paths:
                dataset = h5[path]
                rel = _relative_path(path, self.root)
                shape = dataset.shape
                dtype = dataset.dtype

                if not _is_numeric_dtype(dtype):
                    non_numeric.append((rel, shape, dtype))
                    continue

                if shape == ():
                    scalars.append((rel, shape, dtype))
                elif len(shape) == 1:
                    one_d.append((rel, shape, dtype))
                elif len(shape) == 2:
                    two_d.append((rel, shape, dtype))
                else:
                    multi_d.append((rel, shape, dtype))

        lines = [f"{Path(self.filename).name}:{self.root}", ""]

        if one_d:
            lines.append("1D numeric datasets:")
            lines.extend(self._format_dataset_rows(one_d))
            lines.append("")

        if two_d:
            lines.append("2D numeric datasets:")
            lines.extend(self._format_dataset_rows(two_d))
            lines.append("")

        if multi_d:
            lines.append("3D+ numeric datasets:")
            lines.extend(self._format_dataset_rows(multi_d))
            lines.append("")

        if scalars:
            lines.append("Scalar numeric datasets:")
            lines.extend(self._format_dataset_rows(scalars))
            lines.append("")

        if non_numeric:
            lines.append("Non-numeric datasets:")
            lines.extend(self._format_dataset_rows(non_numeric))
            lines.append("")

        text = "\n".join(lines).rstrip()

        if print_output:
            print(text)

        return text

    def values(self, group: str | None = None, print_output: bool = True) -> dict[str, Any]:
        """
        Read scalar datasets under the current root or under a selected group.
        """

        with h5py.File(self.filename, "r") as h5:
            if group is None:
                root = self.root
            else:
                root = self._resolve_group_path(h5, group)

            values = {}

            if isinstance(h5[root], h5py.Dataset):
                dataset = h5[root]

                if dataset.shape == ():
                    values[_basename(root)] = _decode_scalar(dataset[()])

            else:
                paths = self._dataset_paths(h5, root=root)

                for path in paths:
                    dataset = h5[path]

                    if dataset.shape == ():
                        rel = _relative_path(path, root)
                        values[rel] = _decode_scalar(dataset[()])

        if print_output:
            if values:
                width = max(len(name) for name in values)

                for name, value in values.items():
                    print(f"{name:<{width}}  {value}")
            else:
                print("No scalar datasets found.")

        return values

    def read(self, name: str):
        """
        Read a dataset by absolute path, relative path, or unique short name.
        """

        with h5py.File(self.filename, "r") as h5:
            path = self._resolve_dataset_path(h5, name)
            return h5[path][()]

    def traces(self) -> List[str]:
        """Return numeric one-dimensional dataset paths under the current root."""

        with h5py.File(self.filename, "r") as h5:
            names = []

            for path in self._dataset_paths(h5):
                dataset = h5[path]

                if dataset.shape != () and len(dataset.shape) == 1 and _is_numeric_dtype(dataset.dtype):
                    names.append(_relative_path(path, self.root))

        return names

    def trace(
        self,
        y,
        x=None,
        slice=None,
        axis: int = -1,
        name: str | None = None,
        role: str = "data",
    ) -> Trace:
        """Read one HDF5 dataset as a reusable Trace."""

        if isinstance(y, Trace):
            return y.copy(name=name, role=role)

        with h5py.File(self.filename, "r") as h5:
            x_array = None

            if x is not None:
                x_path = self._resolve_dataset_path(h5, x)
                x_array = np.asarray(h5[x_path][()])

                if x_array.ndim != 1:
                    raise PlotDataError("x must be a 1D dataset.")

                if not _is_numeric_dtype(x_array.dtype):
                    raise PlotDataError("x must be numeric.")

            series = self._build_line_series(
                h5=h5,
                selector=y,
                axis=axis,
                slice_spec=slice,
            )

        if len(series) != 1:
            raise PlotDataError(
                f"trace() expected one 1D trace, but {len(series)} traces were produced. "
                "Use plot() directly for multidimensional trace expansion."
            )

        series_item = series[0]

        if x_array is None:
            x_array = np.arange(series_item.length, dtype=float)

        if len(x_array) != series_item.length:
            raise PlotDataError(
                f"Trace {series_item.label!r} has length {series_item.length}, "
                f"but x has length {len(x_array)}."
            )

        return Trace(
            x=x_array,
            y=series_item.data,
            name=series_item.label if name is None else name,
            role=role,
            attrs={"source_file": self.filename, "source_root": self.root, "source_dataset": str(y)},
        )

    def _series_from_selector(self, h5: h5py.File, selector, axis: int, slice_spec) -> builtins.list[LineSeries]:
        if isinstance(selector, Trace):
            return [
                LineSeries(
                    data=selector.y,
                    label=selector.name,
                    length=len(selector.y),
                    x=selector.x,
                    role=selector.role,
                )
            ]

        return self._build_line_series(
            h5=h5,
            selector=selector,
            axis=axis,
            slice_spec=slice_spec,
        )

    def plot(
        self,
        y=None,
        x=None,
        y2=None,
        slice=None,
        axis: int = -1,
        labels=None,
        y2labels=None,
        xlabel: str | None = None,
        ylabel: str | None = None,
        y2label: str | None = None,
        title: str | None = None,
        xscale: str = "linear",
        yscale: str = "linear",
        y2scale: str = "linear",
        legend: bool = True,
        legend_location: str = "best",
        grid: bool = True,
        theme: str = "dark",
        save: str | Path | None = None,
        dpi: int = 200,
        show: bool = True,
        figsize=(9, 5),
        linewidth: float = 1.6,
    ):
        """Plot HDF5 datasets and/or Trace objects."""

        theme = check_theme(theme)

        if y is None and y2 is None:
            raise PlotDataError("plot requires y, y2, or both.")

        with h5py.File(self.filename, "r") if self.filename else nullcontext(None) as h5:
            x_array = None
            x_name = None

            if x is not None:
                if isinstance(x, Trace):
                    x_array = x.y
                    x_name = x.name
                else:
                    if h5 is None:
                        x_array = np.asarray(x)
                        x_name = "x"
                    else:
                        x_path = self._resolve_dataset_path(h5, x)
                        x_name = _basename(x_path)
                        x_array = np.asarray(h5[x_path][()])

                if x_array.ndim != 1:
                    raise PlotDataError("x must be a 1D dataset, array, or Trace.")

                if not _is_numeric_dtype(x_array.dtype):
                    raise PlotDataError("x must be numeric.")

            left_series = []
            right_series = []

            for selector in _as_list(y):
                left_series.extend(
                    self._series_from_selector(
                        h5=h5,
                        selector=selector,
                        axis=axis,
                        slice_spec=slice,
                    )
                )

            for selector in _as_list(y2):
                right_series.extend(
                    self._series_from_selector(
                        h5=h5,
                        selector=selector,
                        axis=axis,
                        slice_spec=slice,
                    )
                )

        all_series = left_series + right_series

        if not all_series:
            raise PlotDataError("No y data was selected.")

        dataset_series = [series for series in all_series if series.x is None]

        if x_array is None and dataset_series:
            x_length = dataset_series[0].length
            x_array = np.arange(x_length)
            x_name = "Index"
        elif x_array is not None:
            x_length = len(x_array)
        else:
            x_length = None
            x_name = "x"

        if x_array is not None:
            for series in dataset_series:
                if series.length != x_length:
                    raise PlotDataError(
                        f"Trace {series.label!r} has length {series.length}, "
                        f"but x has length {x_length}."
                    )

        for series in all_series:
            if series.x is not None:
                if len(series.x) != series.length:
                    raise PlotDataError(f"Trace {series.label!r} has mismatched x and y lengths.")
                if not _is_numeric_dtype(series.x.dtype):
                    raise PlotDataError(f"Trace {series.label!r} has non-numeric x data.")

        self._apply_user_labels(left_series, labels, "labels")
        self._apply_user_labels(right_series, y2labels, "y2labels")

        fig, ax = plt.subplots(figsize=figsize)

        ax2 = None

        if right_series:
            ax2 = ax.twinx()

        apply_theme(fig, [ax, ax2], theme)

        colors = itertools.cycle(theme_colors(theme))

        for series in left_series:
            color = next(colors)
            x_plot = series.x if series.x is not None else x_array
            x_clean, y_clean = _omit_nonfinite_xy(x_plot, series.data, series.label)
            style = _line_style_for_role(series.role, theme, color, linewidth)
            ax.plot(x_clean, y_clean, label=series.label, **style)

        if ax2 is not None:
            for series in right_series:
                color = next(colors)
                x_plot = series.x if series.x is not None else x_array
                x_clean, y_clean = _omit_nonfinite_xy(x_plot, series.data, series.label)
                style = _line_style_for_role(series.role, theme, color, linewidth)
                ax2.plot(x_clean, y_clean, label=series.label, **style)

        if xlabel is None:
            xlabel = x_name

        if ylabel is None:
            if len(left_series) == 1 and not right_series:
                ylabel = left_series[0].label
            else:
                ylabel = "Value"

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        if ax2 is not None:
            if y2label is None:
                if len(right_series) == 1:
                    y2label = right_series[0].label
                else:
                    y2label = "Value"

            ax2.set_ylabel(y2label)

        if title is not None:
            ax.set_title(title)

        _apply_plot_scales(
            ax=ax,
            ax2=ax2,
            x_array=x_array,
            left_series=left_series,
            right_series=right_series,
            xscale=xscale,
            yscale=yscale,
            y2scale=y2scale,
        )

        if grid:
            ax.grid(True, **grid_kwargs(theme))
        else:
            ax.grid(False)

        if legend:
            handles, legend_labels = ax.get_legend_handles_labels()

            if ax2 is not None:
                handles2, legend_labels2 = ax2.get_legend_handles_labels()
                handles += handles2
                legend_labels += legend_labels2

            if handles:
                legend_object = ax.legend(handles, legend_labels, loc=legend_location)
                style_legend(legend_object, theme)

        fig.tight_layout()

        self._save_and_show(fig=fig, save=save, dpi=dpi, show=show)

        if ax2 is not None:
            return fig, (ax, ax2)

        return fig, ax

    def map(
        self,
        z,
        x=None,
        y=None,
        slice=None,
        xlabel: str | None = None,
        ylabel: str | None = None,
        zlabel: str | None = None,
        title: str | None = None,
        xscale: str = "linear",
        yscale: str = "linear",
        zscale: str = "linear",
        grid: bool = False,
        theme: str = "dark",
        save: str | Path | None = None,
        dpi: int = 200,
        show: bool = True,
        figsize=(8, 6),
    ):
        """
        Plot a 2D dataset as a map.

        Parameters
        ----------
        z:
            One of the following:

            - A 2D dataset name/path.
            - A multidimensional dataset reduced to 2D with slice.
            - A list of 1D dataset names/paths, which will be stacked into
              a 2D array. This is useful for heat maps built from several
              separate time histories.

        x:
            Optional 1D x-axis dataset or array-like values.

        y:
            Optional 1D y-axis dataset or array-like values.

        slice:
            Optional integer-index slicing for 3D+ arrays.

        xscale, yscale, zscale:
            Axis and color scale options. Use "linear" or "log". A log scale
            only changes the displayed scale; it does not transform stored data.
        """

        theme = check_theme(theme)

        with h5py.File(self.filename, "r") as h5:
            z_array, z_name = self._read_map_z(h5, z)

            z_array = _apply_slice_for_map(z_array, slice)

            if z_array.ndim != 2:
                raise PlotDataError(
                    f"map requires 2D data after slicing. "
                    f"Selected data has shape {z_array.shape}."
                )

            rows, cols = z_array.shape

            x_array, x_name = self._read_map_axis(
                h5=h5,
                value=x,
                default=np.arange(cols),
                default_name="Column Index",
                valid_lengths=(cols, cols + 1),
                axis_name="x",
            )

            y_array, y_name = self._read_map_axis(
                h5=h5,
                value=y,
                default=np.arange(rows),
                default_name="Row Index",
                valid_lengths=(rows, rows + 1),
                axis_name="y",
            )

        fig, ax = plt.subplots(figsize=figsize)
        apply_theme(fig, ax, theme)

        xscale = _check_scale(xscale)
        yscale = _check_scale(yscale)
        zscale = _check_scale(zscale)

        if xscale == "log":
            _check_log_positive(x_array, "x")

        if yscale == "log":
            _check_log_positive(y_array, "y")

        norm = None

        if zscale == "log":
            _check_log_positive(z_array, "z")
            norm = LogNorm()

        ax.set_xscale(xscale)
        ax.set_yscale(yscale)

        cmap = theme_settings(theme)["map_cmap"]

        mesh = ax.pcolormesh(
            x_array,
            y_array,
            z_array,
            shading="auto",
            cmap=cmap,
            norm=norm,
        )
        colorbar = fig.colorbar(mesh, ax=ax)
        style_colorbar(colorbar, theme)

        if xlabel is None:
            xlabel = x_name

        if ylabel is None:
            ylabel = y_name

        if zlabel is None:
            zlabel = z_name

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        colorbar.set_label(zlabel)

        if title is not None:
            ax.set_title(title)

        if grid:
            ax.grid(True, **grid_kwargs(theme))
        else:
            ax.grid(False)

        fig.tight_layout()

        self._save_and_show(fig=fig, save=save, dpi=dpi, show=show)

        return fig, ax

    def _resolve_dataset_path(self, h5: h5py.File, selector: str) -> str:
        if not isinstance(selector, str):
            raise DatasetNotFoundError(f"Dataset selector must be a string, got {type(selector)}.")

        selector = selector.strip()

        if selector == "":
            raise DatasetNotFoundError("Empty dataset selector.")

        direct_path = _join_h5(self.root, selector)

        if direct_path in h5:
            if isinstance(h5[direct_path], h5py.Dataset):
                return direct_path

            raise DatasetNotFoundError(f"{direct_path!r} exists, but it is not a dataset.")

        paths = self._dataset_paths(h5)

        exact_matches = []

        for path in paths:
            basename = _basename(path)
            relative = _relative_path(path, self.root)

            if selector == basename or selector == relative:
                exact_matches.append(path)

        if len(exact_matches) == 1:
            return exact_matches[0]

        if len(exact_matches) > 1:
            self._raise_ambiguous(selector, exact_matches)

        normalized_selector = _normalize_name(selector)
        normalized_matches = []

        for path in paths:
            basename = _basename(path)
            relative = _relative_path(path, self.root)

            if (
                _normalize_name(basename) == normalized_selector
                or _normalize_name(relative) == normalized_selector
            ):
                normalized_matches.append(path)

        if len(normalized_matches) == 1:
            return normalized_matches[0]

        if len(normalized_matches) > 1:
            self._raise_ambiguous(selector, normalized_matches)

        raise DatasetNotFoundError(
            f"Could not find dataset {selector!r} under {self.root!r} in {self.filename!r}."
        )

    def _resolve_group_path(self, h5: h5py.File, selector: str) -> str:
        selector = str(selector).strip()

        if selector == "":
            raise DatasetNotFoundError("Empty group selector.")

        direct_path = _join_h5(self.root, selector)

        if direct_path in h5:
            if isinstance(h5[direct_path], h5py.Group):
                return direct_path

            raise DatasetNotFoundError(f"{direct_path!r} exists, but it is not a group.")

        groups = self._group_paths(h5)

        matches = []

        for path in groups:
            basename = _basename(path)
            relative = _relative_path(path, self.root)

            if selector == basename or selector == relative:
                matches.append(path)

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            self._raise_ambiguous(selector, matches)

        raise DatasetNotFoundError(
            f"Could not find group {selector!r} under {self.root!r} in {self.filename!r}."
        )

    def _dataset_paths(self, h5: h5py.File, root: str | None = None) -> builtins.list[str]:
        if root is None:
            root = self.root

        root = _clean_root(root)

        if root not in h5:
            raise DatasetNotFoundError(f"Root path {root!r} was not found in {self.filename!r}.")

        root_object = h5[root]
        paths = []

        if isinstance(root_object, h5py.Dataset):
            return [root]

        def visit(name, object_):
            if isinstance(object_, h5py.Dataset):
                if root == "/":
                    paths.append("/" + name)
                else:
                    paths.append(root.rstrip("/") + "/" + name)

        root_object.visititems(visit)
        paths.sort()

        return paths

    def _group_paths(self, h5: h5py.File) -> builtins.list[str]:
        if self.root not in h5:
            raise DatasetNotFoundError(f"Root path {self.root!r} was not found in {self.filename!r}.")

        root_object = h5[self.root]
        paths = []

        if isinstance(root_object, h5py.Group):
            paths.append(self.root)

            def visit(name, object_):
                if isinstance(object_, h5py.Group):
                    if self.root == "/":
                        paths.append("/" + name)
                    else:
                        paths.append(self.root.rstrip("/") + "/" + name)

            root_object.visititems(visit)

        paths.sort()

        return paths

    def _raise_ambiguous(self, selector: str, matches: builtins.list[str]):
        lines = [f"Dataset/group name {selector!r} is ambiguous. Matches:"]

        for path in matches:
            lines.append(f"  - {path}")

        lines.append("Use a full path or scope the file with file.at(...).")

        raise AmbiguousDatasetError("\n".join(lines))

    def _dataset_tree_line(self, dataset: h5py.Dataset, prefix: str) -> str:
        name = _basename(dataset.name)
        shape = _shape_string(dataset.shape)
        dtype = dataset.dtype

        return f"{prefix}{name}  {shape}  {dtype}"

    def _append_tree_lines(
        self,
        lines: builtins.list[str],
        group: h5py.Group,
        prefix: str,
        depth: int,
        max_depth: int | None,
    ):
        if max_depth is not None and depth >= max_depth:
            return

        items = sorted(group.items(), key=lambda item: item[0])

        for index, (name, object_) in enumerate(items):
            is_last = index == len(items) - 1
            branch = "└── " if is_last else "├── "
            next_prefix = prefix + ("    " if is_last else "│   ")

            if isinstance(object_, h5py.Dataset):
                shape = _shape_string(object_.shape)
                dtype = object_.dtype
                lines.append(f"{prefix}{branch}{name}  {shape}  {dtype}")
            else:
                lines.append(f"{prefix}{branch}{name}/")
                self._append_tree_lines(
                    lines=lines,
                    group=object_,
                    prefix=next_prefix,
                    depth=depth + 1,
                    max_depth=max_depth,
                )

    def _format_dataset_rows(self, rows: builtins.list[tuple[str, Any, Any]]) -> builtins.list[str]:
        if not rows:
            return []

        width = max(len(row[0]) for row in rows)
        formatted = []

        for name, shape, dtype in rows:
            formatted.append(f"  {name:<{width}}  {_shape_string(shape):<16}  {dtype}")

        return formatted

    def _build_line_series(
        self,
        h5: h5py.File,
        selector: str,
        axis: int,
        slice_spec,
    ) -> builtins.list[LineSeries]:
        path = self._resolve_dataset_path(h5, selector)
        base_label = _basename(path)

        array = np.asarray(h5[path][()])

        if not _is_numeric_dtype(array.dtype):
            raise PlotDataError(f"Dataset {path!r} is not numeric.")

        array, plot_axis = _apply_slice_for_lines(array, axis=axis, slice_spec=slice_spec)

        if array.ndim == 0:
            raise PlotDataError(f"Dataset {path!r} became scalar after slicing.")

        plot_axis = _normalize_axis(plot_axis, array.ndim)
        length = array.shape[plot_axis]

        moved = np.moveaxis(array, plot_axis, -1)

        if moved.ndim == 1:
            return [
                LineSeries(
                    data=np.asarray(moved),
                    label=base_label,
                    length=length,
                )
            ]

        trace_shape = moved.shape[:-1]
        flattened = moved.reshape((-1, moved.shape[-1]))
        series = []

        for trace_index, trace in enumerate(flattened):
            multi_index = np.unravel_index(trace_index, trace_shape)

            if len(multi_index) == 1:
                label = f"{base_label}[{multi_index[0]}]"
            else:
                label = f"{base_label}{multi_index}"

            series.append(
                LineSeries(
                    data=np.asarray(trace),
                    label=label,
                    length=length,
                )
            )

        return series

    def _apply_user_labels(self, series: builtins.list[LineSeries], labels, label_name: str):
        if labels is None:
            return

        labels = _as_list(labels)

        if len(labels) != len(series):
            raise PlotDataError(
                f"{label_name} must contain exactly {len(series)} labels. "
                f"Received {len(labels)}."
            )

        for series_item, label in zip(series, labels):
            series_item.label = str(label)

    def _save_and_show(self, fig, save, dpi: int, show: bool):
        if save is not None:
            fig.savefig(
                save,
                dpi=dpi,
                bbox_inches="tight",
                facecolor=fig.get_facecolor(),
            )

        if show:
            plt.show()

    def _read_map_z(self, h5: h5py.File, z):
        if isinstance(z, (builtins.list, tuple)):
            arrays = []

            if len(z) == 0:
                raise PlotDataError("z cannot be an empty list.")

            for selector in z:
                path = self._resolve_dataset_path(h5, selector)
                array = np.asarray(h5[path][()])

                if not _is_numeric_dtype(array.dtype):
                    raise PlotDataError(f"Dataset {path!r} is not numeric.")

                if array.ndim != 1:
                    raise PlotDataError(
                        f"When z is a list, each selected dataset must be 1D. "
                        f"Dataset {path!r} has shape {array.shape}."
                    )

                arrays.append(array)

            lengths = {len(array) for array in arrays}

            if len(lengths) != 1:
                raise PlotDataError("All z datasets must have the same length to form a heat map.")

            return np.vstack(arrays), "Stacked Values"

        z_path = self._resolve_dataset_path(h5, z)
        z_name = _basename(z_path)
        z_array = np.asarray(h5[z_path][()])

        if not _is_numeric_dtype(z_array.dtype):
            raise PlotDataError("z must be numeric.")

        return z_array, z_name

    def _read_map_axis(self, h5: h5py.File, value, default, default_name: str, valid_lengths, axis_name: str):
        if value is None:
            return default, default_name

        if isinstance(value, str):
            path = self._resolve_dataset_path(h5, value)
            array = np.asarray(h5[path][()])
            name = _basename(path)
        else:
            array = np.asarray(value)
            name = default_name

        if array.ndim != 1:
            raise PlotDataError(f"{axis_name} must be 1D.")

        if not _is_numeric_dtype(array.dtype):
            raise PlotDataError(f"{axis_name} must be numeric.")

        if len(array) not in valid_lengths:
            valid_text = " or ".join(str(length) for length in valid_lengths)
            raise PlotDataError(
                f"{axis_name} has length {len(array)}, but expected length {valid_text}."
            )

        return array, name


def open(filename: str | Path, root: str = "/") -> H5File:
    return H5File(filename=filename, root=root)


def tree(filename: str | Path, root: str = "/", **kwargs) -> str:
    return open(filename, root=root).tree(**kwargs)


def list_h5(filename: str | Path, root: str = "/", **kwargs) -> str:
    return open(filename, root=root).list(**kwargs)


def read(filename: str | Path, name: str, root: str = "/"):
    return open(filename, root=root).read(name)


def values(filename: str | Path, root: str = "/", group: str | None = None, **kwargs):
    return open(filename, root=root).values(group=group, **kwargs)


def trace(filename: str | Path, y, x=None, root: str = "/", **kwargs) -> Trace:
    return open(filename, root=root).trace(y=y, x=x, **kwargs)


def _looks_like_trace_collection(value) -> bool:
    if isinstance(value, Trace):
        return True

    if isinstance(value, (builtins.list, tuple)) and value:
        return all(isinstance(item, Trace) for item in value)

    return False


def plot(filename_or_traces=None, y=None, x=None, root: str = "/", **kwargs):
    """Plot either an HDF5 dataset selection or prepared Trace objects."""

    if _looks_like_trace_collection(filename_or_traces) and y is None:
        return H5File(filename="", root="/").plot(y=filename_or_traces, x=x, **kwargs)

    if filename_or_traces is None:
        raise TypeError("plot() requires either a filename or Trace object(s).")

    return open(filename_or_traces, root=root).plot(y=y, x=x, **kwargs)


def map(filename: str | Path, z, root: str = "/", **kwargs):
    return open(filename, root=root).map(z=z, **kwargs)


def write_traces(filename: str | Path, traces, group: str = "traces", overwrite: bool = True) -> str:
    """Write one or more Trace objects to a simple HDF5 trace group."""

    traces = _as_list(traces)

    if not traces:
        raise ValueError("write_traces() requires at least one Trace.")

    for item in traces:
        if not isinstance(item, Trace):
            raise TypeError("write_traces() only accepts Trace objects.")

    output = hdf5_filename(filename)

    with h5py.File(output, "a") as h5:
        root_group = h5.require_group(safe_group_name(group))

        for item in traces:
            name = safe_group_name(item.name)

            if name in root_group:
                if overwrite:
                    del root_group[name]
                else:
                    raise ValueError(f"Trace group {group}/{name} already exists.")

            trace_group = root_group.create_group(name)
            trace_group.create_dataset("x", data=item.x)
            trace_group.create_dataset("y", data=item.y)
            trace_group.attrs["name"] = item.name
            trace_group.attrs["role"] = item.role

            for key, value in item.attrs.items():
                try:
                    trace_group.attrs[str(key)] = value
                except TypeError:
                    trace_group.attrs[str(key)] = str(value)

    return output


def show():
    """Show all currently open matplotlib figures."""

    plt.show()


list = list_h5



__all__ = [
    "FullPlotError",
    "DatasetNotFoundError",
    "AmbiguousDatasetError",
    "PlotDataError",
    "Trace",
    "H5File",
    "open",
    "tree",
    "list",
    "read",
    "values",
    "trace",
    "plot",
    "map",
    "write_traces",
    "show",
]
