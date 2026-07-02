"""
NaN and missing values are omitted automatically for traces.

PCMC_DROPOUT contains NaN samples during startup. FullPlot does not make the
user choose a NaN policy for ordinary Trace work; non-finite x/y pairs are just
removed when the Trace is created or plotted.
"""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

raw_dataset = file.read("PCMC_DROPOUT")
dropout_trace = file.trace(y="PCMC_DROPOUT", x="time", name="PCMC Dropout")
filtered = dropout_trace.filter("moving_average", window=0.05, name="Dropout Filtered")

print(f"Raw dataset samples: {len(raw_dataset)}")
print(f"Trace samples after omitting missing values: {len(dropout_trace.y)}")

fplt.plot(
    [dropout_trace, filtered],
    xlabel="Time [s]",
    ylabel="Pressure [psia]",
    title="NaN Samples Automatically Omitted",
    save=example_dir / "8_missing_nan_values_are_omitted.png",
    show=False,
)
