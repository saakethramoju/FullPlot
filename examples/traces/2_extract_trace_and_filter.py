"""
Extract Trace objects and filter noisy data.

Trace.filter() returns a new Trace, leaving the original raw trace unchanged.
Time-based windows use the x-axis units. Since x is time in seconds here,
window=0.05 means a 0.05 second moving-average window.
"""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

raw = file.trace(y="PCMC_NOISY", x="time", name="Raw PCMC")
mean_filtered = raw.filter("moving_average", window=0.05, name="Moving Average")
median_filtered = raw.filter("median", window=0.05, name="Median Filter")
savgol_filtered = raw.filter("savgol", window=0.05, order=2, name="Savitzky-Golay")

fplt.plot(
    [raw, mean_filtered, median_filtered, savgol_filtered],
    xlabel="Time [s]",
    ylabel="Pressure [psia]",
    title="Noisy Chamber Pressure Filtering",
    save=example_dir / "2_extract_trace_and_filter.png",
    show=False,
)
