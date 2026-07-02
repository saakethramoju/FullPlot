"""
Quick HDF5 plotting with sensor traces.

This is the simplest FullPlot workflow: open an HDF5 file and plot one or more
1D datasets against the time dataset. The file could be simulation output or
converted test data; FullPlot treats both the same way.
"""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()

file = fplt.open(filename)

file.plot(
    x="time",
    y=["PCMC_1", "PCMC_2", "PCMC_3"],
    xlabel="Time [s]",
    ylabel="Chamber Pressure [psia]",
    title="Multiple Chamber Pressure Sensors",
    save=example_dir / "1_quick_hdf5_trace_plot.png",
    show=False,
)
