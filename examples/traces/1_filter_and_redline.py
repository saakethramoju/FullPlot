"""
FullPlot trace filtering and redline example.

This example creates a noisy pressure trace, filters it, creates a generic
redline trace, and overlays all three traces on one plot.
"""

from pathlib import Path

import h5py
import numpy as np

import fullplot as fplt


example_dir = Path(__file__).resolve().parent
filename = example_dir / "trace_example.h5"


time = np.linspace(0.0, 5.0, 1001)
pressure = 300.0 + 40.0 * np.sin(2.0 * np.pi * time) + 5.0 * np.random.default_rng(2).normal(size=len(time))

with h5py.File(filename, "w") as h5:
    h5["time"] = time
    h5["CHPT"] = pressure

run = fplt.open(filename)

chpt = run.trace("CHPT", x="time")
chpt_filtered = chpt.filter("moving_average", window=0.05)
redline = fplt.Trace.constant("CHPT Redline", x=chpt.x, y=350.0, role="redline")

fplt.plot(
    [chpt, chpt_filtered, redline],
    xlabel="Time [s]",
    ylabel="Pressure",
    title="Filtered Trace with Redline",
    save=example_dir / "trace_example.png",
    show=False,
)
