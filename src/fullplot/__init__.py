"""FullPlot: lightweight HDF5 trace plotting, filtering, and map generation."""

from importlib.metadata import PackageNotFoundError, version

from fullplot.cli import main
from fullplot.fullplot import (
    AmbiguousDatasetError,
    DatasetNotFoundError,
    FullPlotError,
    H5File,
    PlotDataError,
    TimeAxis,
    Trace,
    list,
    map,
    open,
    plot,
    read,
    show,
    time,
    trace,
    tree,
    values,
    write_traces,
)
from fullplot.maps import (
    Axis,
    FullPlotMapError,
    MapGenerationError,
    MapOutputError,
    generate_map,
)

try:
    __version__ = version("fullplot")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "FullPlotError",
    "DatasetNotFoundError",
    "AmbiguousDatasetError",
    "PlotDataError",
    "TimeAxis",
    "Trace",
    "H5File",
    "open",
    "tree",
    "list",
    "read",
    "values",
    "time",
    "trace",
    "plot",
    "map",
    "write_traces",
    "show",
    "Axis",
    "FullPlotMapError",
    "MapGenerationError",
    "MapOutputError",
    "generate_map",
    "main",
]
