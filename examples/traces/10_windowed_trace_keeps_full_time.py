"""
Trace windowing masks values with NaN while keeping the full time axis.

This is useful for balancing a model only over part of a test. The trace still
has the full shared time axis, but values outside the selected window are NaN.
A solver can later decide whether NaN means skip, hold, stop, or error.
"""

from pathlib import Path

import numpy as np

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

time = file.time("time")
time.zero_at(0.05)

pcmc = file.trace(y="PCMC_1", x=time, name="PCMC Full Trace")
mainstage = pcmc.window(start=0.0, stop=12.0, name="PCMC Mainstage Window")

print(f"Full trace samples: {len(pcmc.y)}")
print(f"Windowed trace samples: {len(mainstage.y)}")
print(f"Windowed trace NaNs: {np.isnan(mainstage.y).sum()}")
print(f"Time range is still: {mainstage.tmin:.3f} to {mainstage.tmax:.3f} s")

fplt.plot(
    [pcmc, mainstage],
    xlabel="Model Time [s]",
    ylabel="Pressure [psia]",
    title="Windowed Trace Keeps Full Time Axis",
    save=example_dir / "10_windowed_trace_keeps_full_time.png",
    show=False,
)
