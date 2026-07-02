"""
NaN and missing values are preserved in traces.

PCMC_DROPOUT contains NaN samples during startup. FullPlot keeps those NaNs
inside the Trace so plots show real gaps instead of connecting through missing
test data. Use omit_missing() when you explicitly want a compact finite trace.
"""

from pathlib import Path

import numpy as np

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

raw_dataset = file.read("PCMC_DROPOUT")
dropout_trace = file.trace(y="PCMC_DROPOUT", x="time", name="PCMC Dropout")
finite_trace = dropout_trace.omit_missing(name="PCMC Dropout Finite Samples")

print(f"Raw dataset samples: {len(raw_dataset)}")
print(f"Trace samples with NaNs preserved: {len(dropout_trace.y)}")
print(f"Missing samples: {np.isnan(dropout_trace.y).sum()}")
print(f"Finite compact samples: {len(finite_trace.y)}")

fplt.plot(
    dropout_trace,
    xlabel="Time [s]",
    ylabel="Pressure [psia]",
    title="NaN Samples Preserved as Plot Gaps",
    save=example_dir / "8_missing_nan_values_create_gaps.png",
    show=False,
)
