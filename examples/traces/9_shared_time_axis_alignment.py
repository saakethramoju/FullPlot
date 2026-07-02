"""
Shared TimeAxis alignment for test-data traces.

A TimeAxis is a shared x-axis object. Several traces can reference the same
TimeAxis, and changing where t = 0 is located shifts all of those traces at once.
This is useful when test-data time zero does not match simulation time zero.
"""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

# Read the HDF5 time dataset once as a shared TimeAxis.
time = file.time("time")

pcmc = file.trace(y="PCMC_1", x=time, name="PCMC")
oipt = file.trace(y="OIPT", x=time, name="OIPT")
fipt = file.trace(y="FIPT", x=time, name="FIPT")

print(f"Raw time range: {time.raw_tmin:.3f} to {time.raw_tmax:.3f} s")
print(f"Nominal dt: {time.dt:.6f} s")
print(f"Uniform time axis: {time.is_uniform}")

# Shift the shared axis so original test time t = 0.05 s becomes model t = 0.
# All traces that use this TimeAxis shift together.
time.zero_at(0.05)

print(f"Shifted model time range: {time.tmin:.3f} to {time.tmax:.3f} s")

fplt.plot(
    [pcmc, oipt, fipt],
    xlabel="Model Time [s]",
    ylabel="Pressure [psia]",
    title="Shared TimeAxis Shifted Once for Several Traces",
    save=example_dir / "9_shared_time_axis_alignment.png",
    show=False,
)
