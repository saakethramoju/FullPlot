"""
FullPlot map metadata and output-selection example.

A generated map is mostly just arrays, but FullPlot also stores useful metadata:
axis order, output names, constants, user metadata, and per-point success
information. This is helpful for inspecting expensive property or performance
maps after they have been generated.
"""

from pathlib import Path
import json

import h5py
import fullplot as fplt


example_dir = Path(__file__).resolve().parent
filename = example_dir / "pump_demo_map.h5"


def pump_like_map(flow_coefficient, speed_parameter, reference_head):
    head_coefficient = reference_head * speed_parameter**2 * (1.0 - 0.35 * flow_coefficient**2)
    torque_coefficient = 0.20 + 0.08 * speed_parameter + 0.15 * flow_coefficient
    efficiency = 0.78 - 0.20 * (flow_coefficient - 0.6)**2

    return {
        "head_coefficient": head_coefficient,
        "torque_coefficient": torque_coefficient,
        "efficiency": efficiency,
    }


fplt.generate_map(
    filename,
    group="pump_demo",
    axes=[
        fplt.Axis.values("flow_coefficient", values=[0.0, 0.25, 0.50, 0.75, 1.0]),
        fplt.Axis.linear("speed_parameter", start=0.75, stop=1.25, count=6),
    ],
    constants={
        "reference_head": 1.0,
    },
    metadata={
        "description": "Small pump-like map for demonstrating FullPlot metadata.",
        "valid_for": "demonstration only",
    },
    outputs=[
        "head_coefficient",
        "torque_coefficient",
        "efficiency",
    ],
    evaluate=pump_like_map,
    overwrite=True,
    raise_errors=True,
)

print(f"Wrote {filename}")

with h5py.File(filename, "r") as file:
    map_group = file["pump_demo"]

    axis_order = json.loads(map_group.attrs["axis_order"])
    output_names = json.loads(map_group.attrs["output_names"])
    constants = json.loads(map_group.attrs["constants"])
    metadata = json.loads(map_group.attrs["metadata"])

    print("Map group:", map_group.name)
    print("Axis order:", axis_order)
    print("Output names:", output_names)
    print("Constants:", constants)
    print("Metadata:", metadata)

    print("\nAxes:")
    for axis_name in axis_order:
        axis_dataset = map_group["axes"][axis_name]
        print(axis_name)
        print("  spacing:", axis_dataset.attrs.get("spacing", "values"))
        print("  values:", axis_dataset[()])

    print("\nOutput shapes:")
    for output_name in output_names:
        print(output_name, map_group["outputs"][output_name].shape)

    successful_points = map_group["status"]["success"][()]
    print("\nSuccessful map points:", successful_points.sum(), "out of", successful_points.size)
