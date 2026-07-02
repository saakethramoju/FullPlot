"""
Basic FullPlot map-generation example.

This script creates a small ideal-gas property map. The map has two swept
inputs, pressure and temperature, and two scalar outputs, density and enthalpy.

The generated HDF5 file is intentionally simple and generic:

    /ideal_gas/axes/pressure
    /ideal_gas/axes/temperature
    /ideal_gas/outputs/density
    /ideal_gas/outputs/enthalpy

FullFlow can read this layout with Map.from_hdf5(...), but FullPlot itself does
not import or depend on FullFlow.
"""

from pathlib import Path

import fullplot as fplt


example_dir = Path(__file__).resolve().parent
filename = example_dir / "ideal_gas_map.h5"


def ideal_gas_properties(pressure, temperature, gas_constant, specific_heat):
    density = pressure / (gas_constant * temperature)
    enthalpy = specific_heat * temperature

    return {
        "density": density,
        "enthalpy": enthalpy,
    }


fplt.generate_map(
    filename,
    group="ideal_gas",
    axes=[
        fplt.Axis.linear("pressure", start=1.0e5, stop=5.0e5, count=5, units="Pa"),
        fplt.Axis.linear("temperature", start=250.0, stop=500.0, count=6, units="K"),
    ],
    constants={
        "gas_constant": 287.0,
        "specific_heat": 1005.0,
    },
    evaluate=ideal_gas_properties,
    overwrite=True,
    raise_errors=True,
)

print(f"Wrote {filename}")

# FullPlot can inspect the generated file like any other HDF5 file.
run = fplt.open(filename)
run.tree()
