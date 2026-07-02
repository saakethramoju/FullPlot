"""
FullPlot Axis example.

A map axis is one independent input that gets swept while the HDF5 map is
built. The axis name matters because it becomes the keyword passed into the
map function.

This example demonstrates the three Axis constructors:

    Axis.linear()
        Even spacing between start and stop. Good for temperature, mixture
        ratio, valve position, area ratio, or other smoothly varying inputs.

    Axis.log()
        Logarithmic spacing between positive start and stop values. Good for
        pressure or any positive input that spans several orders of magnitude.
        The stored values are still physical values, not log(value).

    Axis.values()
        Explicit breakpoints. Good for measured data, hand-picked points, pump
        speed lines, tabulated map curves, or nonuniform grids.
"""

from pathlib import Path

import fullplot as fplt


example_dir = Path(__file__).resolve().parent
filename = example_dir / "axis_demo_map.h5"


def gas_properties(pressure, temperature, mixture_ratio, gas_constant, specific_heat):
    density = pressure / (gas_constant * temperature)
    enthalpy = specific_heat * temperature

    return {
        "density": density,
        "enthalpy": enthalpy,
        "fuel_fraction": 1.0 / (1.0 + mixture_ratio),
        "oxidizer_fraction": mixture_ratio / (1.0 + mixture_ratio),
    }


pressure_axis = fplt.Axis.log(
    "pressure",
    start=1.0e5,
    stop=1.0e6,
    count=7,
    units="Pa",
)

temperature_axis = fplt.Axis.linear(
    "temperature",
    start=250.0,
    stop=600.0,
    count=8,
    units="K",
)

mixture_ratio_axis = fplt.Axis.values(
    "mixture_ratio",
    values=[1.5, 2.0, 2.3, 2.6, 3.0],
)

fplt.generate_map(
    filename,
    group="axis_demo",
    axes=[
        pressure_axis,
        temperature_axis,
        mixture_ratio_axis,
    ],
    constants={
        "gas_constant": 287.0,
        "specific_heat": 1005.0,
    },
    evaluate=gas_properties,
    overwrite=True,
    raise_errors=True,
)

print(f"Wrote {filename}")

run = fplt.open(filename)
run.tree()

# Axis datasets can be read like normal HDF5 datasets.
print("Pressure axis:", run.read("axis_demo/axes/pressure"))
print("Temperature axis:", run.read("axis_demo/axes/temperature"))
print("Mixture-ratio axis:", run.read("axis_demo/axes/mixture_ratio"))
