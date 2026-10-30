"""FullPlot public package interface."""

from fullplot.cli import main
from fullplot.fullplot import (
    AmbiguousDatasetError,
    DatasetNotFoundError,
    FullPlotError,
    PlotDataError,
    TimeAxis,
    Trace,
    VALID_TRACE_ROLES,
    list,
    map,
    plot,
    read,
    show,
    time,
    trace,
    tree,
    values,
    write_traces,
)
from fullplot.linearization import H5File, Linearization, LinearizationError, open
from fullplot.maps import (
    Axis,
    FullPlotMapError,
    MapGenerationError,
    MapOutputError,
    generate_map,
)

__version__ = "2.0.0"

__all__ = [
    "__version__",
    "FullPlotError",
    "DatasetNotFoundError",
    "AmbiguousDatasetError",
    "PlotDataError",
    "LinearizationError",
    "Linearization",
    "TimeAxis",
    "Trace",
    "VALID_TRACE_ROLES",
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
