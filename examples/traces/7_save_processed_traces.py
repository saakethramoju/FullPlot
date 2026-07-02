"""
Save generated and processed traces to a new HDF5 file.

The saved file uses a simple /traces/<trace name>/x and /traces/<trace name>/y
layout. These saved traces can be opened and inspected like any other HDF5 data.
"""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

pc = file.trace(y="PCMC_NOISY", x="time", name="PCMC_NOISY")
pc_filtered = pc.filter("moving_average", window=0.05, name="PCMC_NOISY Filtered")
redline = fplt.Trace.constant("PCMC Redline", x=pc.x, y=400.0, role="redline")

output = example_dir / "processed_traces.h5"
fplt.write_traces(output, [pc, pc_filtered, redline])

processed = fplt.open(output)
processed.tree(max_depth=2)
