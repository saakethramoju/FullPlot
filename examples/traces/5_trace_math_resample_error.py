"""
Trace math and automatic resampling.

When doing Trace-to-Trace math, FullPlot resamples the right-hand trace onto the
left-hand trace x-axis. This makes it easy to compare simulation and test traces
with slightly different sample rates.
"""

from pathlib import Path

import numpy as np

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

test_pc = file.trace(y="PCMC_1", x="time", name="Test PCMC_1")

# Create a lower-rate synthetic simulation trace on a different x grid.
sim_time = np.arange(test_pc.x[0], test_pc.x[-1], 0.02)
sim_pc = fplt.Trace.from_function(
    "Simulation PC",
    x=sim_time,
    function=lambda t: np.interp(t, test_pc.x, test_pc.y) * 0.985 + 3.0,
)

error = sim_pc - test_pc
error.name = "Simulation - Test"

fplt.plot(
    [test_pc, sim_pc],
    xlabel="Time [s]",
    ylabel="Pressure [psia]",
    title="Simulation/Test Overlay with Different Sample Rates",
    save=example_dir / "5_trace_math_overlay.png",
    show=False,
)

fplt.plot(
    error,
    xlabel="Time [s]",
    ylabel="Pressure Error [psia]",
    title="Simulation/Test Error Trace",
    save=example_dir / "5_trace_math_error.png",
    show=False,
)
