"""
Generic HDF5 map layout example.

This example shows the minimal HDF5 structure produced by FullPlot map
generation. A reader does not need to know anything about FullPlot if it can
read one-dimensional axis arrays and rectangular output arrays.
"""

from pathlib import Path

import fullplot as fplt


example_dir = Path(__file__).resolve().parent
filename = example_dir / "ideal_gas_map.h5"

# Run 1_generate_map.py first if this file does not exist.
if not filename.exists():
    raise FileNotFoundError("Run 1_generate_map.py before running this example.")

run = fplt.open(filename)
run.tree()

pressure = run.read("ideal_gas/axes/pressure")
temperature = run.read("ideal_gas/axes/temperature")
density = run.read("ideal_gas/outputs/density")
enthalpy = run.read("ideal_gas/outputs/enthalpy")

print("pressure shape:", pressure.shape)
print("temperature shape:", temperature.shape)
print("density shape:", density.shape)
print("enthalpy shape:", enthalpy.shape)

print("\nFor a rectangular-grid map, every output shape should match:")
print("(len(pressure), len(temperature)) =", (len(pressure), len(temperature)))
