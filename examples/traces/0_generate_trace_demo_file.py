"""
Generate a synthetic HDF5 file with many realistic sensor traces.

Run this first if you want to inspect the generated file by hand. The other
trace examples call ensure_trace_demo_file(), so they can also generate the file
automatically if it is missing.
"""

import fullplot as fplt
from _trace_demo_data import TRACE_FILE, create_trace_demo_file


filename = create_trace_demo_file(TRACE_FILE, overwrite=True)

print(f"Wrote: {filename}")

file = fplt.open(filename)
file.tree(max_depth=1)
