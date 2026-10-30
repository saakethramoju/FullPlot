"""Read FullFlow state-space linearizations from HDF5 files."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from .fullplot import FullPlotError, H5File as _H5File, open as _open


class LinearizationError(FullPlotError):
    """An HDF5 linearization is missing, ambiguous, or malformed."""


@dataclass
class Linearization:
    """One saved continuous-time state-space model and its operating point."""

    A: np.ndarray
    B: np.ndarray
    C: np.ndarray
    D: np.ndarray
    x0: np.ndarray
    xdot0: np.ndarray
    u0: np.ndarray
    y0: np.ndarray
    states: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    time: float
    diagnostics: dict[str, Any]
    model_options: dict[str, Any]
    solver: str
    run: str
    network: str
    path: str

    def __str__(self) -> str:
        """Return a compact summary suitable for interactive printing."""
        nx = len(self.states)
        nu = len(self.inputs)
        ny = len(self.outputs)
        identity = " / ".join(
            item for item in (self.network, self.solver, self.run) if item
        )
        title = "Linearization" if not identity else f"Linearization: {identity}"
        dimensions = ", ".join((
            f"{nx} state{'s' if nx != 1 else ''}",
            f"{nu} input{'s' if nu != 1 else ''}",
            f"{ny} output{'s' if ny != 1 else ''}",
        ))
        return "\n".join((
            title,
            f"  Time: {self.time:g} s",
            f"  Dimensions: {dimensions}",
            f"  Matrices: A{self.A.shape}, B{self.B.shape}, "
            f"C{self.C.shape}, D{self.D.shape}",
            f"  Path: {self.path}",
        ))


def _decode(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.generic):
        return _decode(value.item())
    if isinstance(value, np.ndarray):
        return [_decode(item) for item in value.tolist()]
    return value


def _labels(group: h5py.Group, name: str) -> tuple[str, ...]:
    if name not in group or not isinstance(group[name], h5py.Dataset):
        raise LinearizationError(f"Missing {name!r} labels in {group.name}.")
    values = group[name][()]
    if np.asarray(values).ndim != 1:
        raise LinearizationError(f"{group.name}/{name} must be a 1D label array.")
    decoded = tuple(_decode(value) for value in values)
    if any(not isinstance(value, str) for value in decoded):
        raise LinearizationError(f"{group.name}/{name} contains non-string labels.")
    return decoded


def _array(group: h5py.Group, name: str, shape: tuple[int, ...]) -> np.ndarray:
    if name not in group or not isinstance(group[name], h5py.Dataset):
        raise LinearizationError(f"Missing dataset {group.name}/{name}.")
    value = np.asarray(group[name][()])
    if value.shape != shape or not np.issubdtype(value.dtype, np.number):
        raise LinearizationError(
            f"{group.name}/{name} must be a numeric array with shape {shape}; "
            f"found {value.shape}."
        )
    return value.copy()


def _metadata(group: h5py.Group, name: str) -> dict[str, Any]:
    if name not in group:
        return {}
    node = group[name]
    if not isinstance(node, h5py.Group):
        raise LinearizationError(f"{group.name}/{name} must be a group.")
    result = {key: _decode(value) for key, value in node.attrs.items()}
    for key, item in node.items():
        if isinstance(item, h5py.Dataset):
            result[key] = _decode(item[()])
        elif name == "model_options" and isinstance(item, h5py.Group):
            option_name = _decode(item.attrs.get("name", key))
            selected = _decode(item.attrs.get("option", ""))
            result[option_name] = selected or None
    return result


def _identity(path: str) -> tuple[str, str, str]:
    segments = path.strip("/").split("/")
    if "linearization" not in segments:
        return "", "", ""
    i = segments.index("linearization")
    network = "/".join(segments[:i])
    solver = segments[i + 1] if i + 1 < len(segments) else ""
    run = ""
    if "runs" in segments:
        j = segments.index("runs") + 1
        end = segments.index("points") if "points" in segments else len(segments)
        run = "/".join(segments[j:end])
    return network, solver, run


def _is_result(group: h5py.Group) -> bool:
    return isinstance(group, h5py.Group) and all(name in group for name in ("A", "B", "C", "D"))


def _read_result(group: h5py.Group) -> Linearization:
    if not _is_result(group):
        raise LinearizationError(
            f"No base linearization is stored in {group.name}. "
            "Specify time= or times= to read saved transient points."
        )
    network, solver, run = _identity(group.name)
    states = _labels(group, "states")
    inputs = _labels(group, "inputs")
    outputs = _labels(group, "outputs")
    nx, nu, ny = len(states), len(inputs), len(outputs)
    if "time" not in group or not isinstance(group["time"], h5py.Dataset):
        raise LinearizationError(f"Missing operating time in {group.name}.")
    time_value = np.asarray(group["time"][()])
    if time_value.shape != () or not np.issubdtype(time_value.dtype, np.number):
        raise LinearizationError(f"{group.name}/time must be numeric and scalar.")
    return Linearization(
        A=_array(group, "A", (nx, nx)),
        B=_array(group, "B", (nx, nu)),
        C=_array(group, "C", (ny, nx)),
        D=_array(group, "D", (ny, nu)),
        x0=_array(group, "x0", (nx,)),
        xdot0=_array(group, "xdot0", (nx,)),
        u0=_array(group, "u0", (nu,)),
        y0=_array(group, "y0", (ny,)),
        states=states,
        inputs=inputs,
        outputs=outputs,
        time=float(time_value),
        diagnostics=_metadata(group, "diagnostics"),
        model_options=_metadata(group, "model_options"),
        solver=solver,
        run=run,
        network=network,
        path=group.name,
    )


def _has_points(group: h5py.Group) -> bool:
    if not isinstance(group, h5py.Group):
        return False
    points = group.get("points")
    return isinstance(points, h5py.Group) and any(
        _is_result(item) for item in points.values() if isinstance(item, h5py.Group)
    )


def _runs(root: h5py.Group) -> list[h5py.Group]:
    if (_is_result(root) or _has_points(root)) and "/points/" not in root.name:
        return [root]
    found: list[h5py.Group] = []

    def visit(name: str, item: h5py.Group | h5py.Dataset):
        if not (_is_result(item) or _has_points(item)):
            return
        path = item.name
        if "/linearization/" in path and "/runs/" in path and "/points/" not in path:
            found.append(item)

    root.visititems(visit)
    return sorted(found, key=lambda group: group.name)


def _missing_scoped_run(root: h5py.Group, solver: str | None):
    raise LinearizationError(f"Scoped linearization {root.name} does not match solver={solver!r}.")


def _select_run(root: h5py.Group, solver: str | None, run: str) -> h5py.Group:
    runs = [group for group in _runs(root) if (not solver or _identity(group.name)[1] == solver)]
    if (_is_result(root) or _has_points(root)) and "/points/" not in root.name:
        return runs[0] if runs else _missing_scoped_run(root, solver)
    matching = [group for group in runs if _identity(group.name)[2] == run]
    if not matching and run == "base" and len(runs) == 1:
        matching = runs
    runs = matching
    if not runs:
        raise LinearizationError(
            f"No linearization for solver={solver!r}, run={run!r} under {root.name}. "
            "Call linearizations() to inspect available results."
        )
    if len(runs) != 1:
        paths = ", ".join(group.name for group in runs)
        raise LinearizationError(f"Multiple linearizations match; use .at() to select one: {paths}")
    return runs[0]


def _point(run: h5py.Group, time: float) -> h5py.Group:
    points = run.get("points")
    matches: list[h5py.Group] = []
    available: list[float] = []
    if isinstance(points, h5py.Group):
        for item in points.values():
            if not isinstance(item, h5py.Group) or "time" not in item:
                continue
            value = float(item["time"][()])
            available.append(value)
            if isclose(value, time, rel_tol=1e-10, abs_tol=1e-12):
                matches.append(item)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise LinearizationError(f"Multiple saved points match t={time:g} under {run.name}.")
    formatted = ", ".join(f"{value:g}" for value in sorted(available)) or "none"
    raise LinearizationError(f"No linearization saved at t={time:g}. Available point times: {formatted}.")


class H5File(_H5File):
    """FullPlot HDF5 handle with support for FullFlow linearization records."""

    def at(self, group: str) -> H5File:
        scoped = super().at(group)
        return H5File(scoped.filename, scoped.root)

    def linearization(
        self,
        solver: str | None = None,
        run: str = "base",
        time: float | None = None,
        times: list[float] | tuple[float, ...] | None = None,
    ) -> Linearization | dict[float, Linearization]:
        """Read one model, or a time-keyed dictionary of saved transient models.

        With no time, reads the run's base result rather than the last point.
        A scoped result group can be read directly with ``.linearization()``.
        """
        if solver not in (None, "steady_state", "transient"):
            raise ValueError("solver must be 'steady_state' or 'transient'.")
        if time is not None and times is not None:
            raise ValueError("Specify time or times, not both.")
        if times is not None and not times:
            raise ValueError("times must not be empty.")
        with h5py.File(self.filename, "r") as h5:
            root = h5[self.root]
            if _is_result(root) and "/points/" in root.name:
                if time is not None or times is not None:
                    raise ValueError("Already scoped to a point; omit time and times.")
                if solver and _identity(root.name)[1] != solver:
                    raise LinearizationError("The selected point does not match solver=.")
                return _read_result(root)
            selected = _select_run(root, solver, run)
            if time is not None:
                return _read_result(_point(selected, float(time)))
            if times is not None:
                results: dict[float, Linearization] = {}
                for requested in times:
                    key = float(requested)
                    if key in results:
                        raise ValueError(f"Duplicate requested time: {key:g}.")
                    results[key] = _read_result(_point(selected, key))
                return results
            return _read_result(selected)

    def linearizations(self, print_output: bool = True) -> list[dict[str, Any]]:
        """List available linearization runs and their saved operating times."""
        with h5py.File(self.filename, "r") as h5:
            root = h5[self.root]
            found = []
            for group in _runs(root):
                network, solver, run = _identity(group.name)
                points = group.get("points")
                point_times = []
                if isinstance(points, h5py.Group):
                    for point in points.values():
                        if isinstance(point, h5py.Group) and "time" in point:
                            point_times.append(float(point["time"][()]))
                reference = group
                if not _is_result(group):
                    reference = min(
                        (item for item in points.values() if _is_result(item)),
                        key=lambda item: float(item["time"][()]),
                    )
                found.append({
                    "network": network,
                    "solver": solver,
                    "run": run,
                    "path": group.name,
                    "time": float(group["time"][()]) if _is_result(group) else None,
                    "states": len(_labels(reference, "states")),
                    "inputs": len(_labels(reference, "inputs")),
                    "outputs": len(_labels(reference, "outputs")),
                    "times": sorted(point_times),
                })
        if print_output:
            for item in found:
                print(f"{item['network']} / {item['solver']} / {item['run']}")
                base_time = f"t={item['time']:g}" if item["time"] is not None else "not saved"
                print(f"  Base: {base_time}, {item['states']} states, "
                      f"{item['inputs']} inputs, {item['outputs']} outputs")
                if item["times"]:
                    print("  Points: " + ", ".join(f"{t:g}" for t in item["times"]))
            if not found:
                print("No FullFlow linearization results found.")
        return found


def open(filename: str | Path, root: str = "/") -> H5File:
    """Open an HDF5 file with the standard FullPlot API and linearization support."""
    handle = _open(filename, root=root)
    return H5File(handle.filename, handle.root)
