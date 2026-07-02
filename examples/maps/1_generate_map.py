"""
FullPlot map-generation example.

The generated HDF5 map follows the same layout expected by FullFlow's
Map.from_hdf5(...) component, but FullPlot itself is independent from FullFlow.
"""

from pathlib import Path

import fullplot as fplt


example_dir = Path(__file__).resolve().parent
filename = example_dir / "ideal_gas_map.h5"


def ideal_gas_density(pressure, temperature):
    return {
        "density": pressure / (287.0 * temperature),
    }


fplt.generate_map(
    filename,
    group="ideal_gas",
    axes=[
        fplt.Axis.linear("pressure", start=1.0e5, stop=5.0e5, count=5),
        fplt.Axis.linear("temperature", start=250.0, stop=500.0, count=6),
    ],
    evaluate=ideal_gas_density,
    overwrite=True,
)

print(f"Wrote {filename}")
