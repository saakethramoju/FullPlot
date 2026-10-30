"""Create a small FullFlow-style HDF5 file for the linearization reading examples.

The matrices below are illustrative. No FullFlow installation is required.
"""

from pathlib import Path

import h5py
import numpy as np


filename = Path(__file__).resolve().parent / "linearization_demo.h5"


def write_result(group, time, gain):
    group.attrs["solver_type"] = "transient"
    group.create_dataset("A", data=[[-0.25 * gain]])
    group.create_dataset("B", data=[[0.5 * gain]])
    group.create_dataset("C", data=[[1.0]])
    group.create_dataset("D", data=[[0.0]])
    group.create_dataset("x0", data=[10.0 - time])
    group.create_dataset("xdot0", data=[-0.2 * gain])
    group.create_dataset("u0", data=[0.5])
    group.create_dataset("y0", data=[10.0 - time])
    labels = h5py.string_dtype("utf-8")
    group.create_dataset("states", data=["Tank:mass"], dtype=labels)
    group.create_dataset("inputs", data=["Valve.area"], dtype=labels)
    group.create_dataset("outputs", data=["Tank.pressure"], dtype=labels)
    group.create_dataset("time", data=time)
    group.create_group("model_options")
    diagnostics = group.create_group("diagnostics")
    diagnostics.attrs["sensitivity_condition_number"] = 1.0


with h5py.File(filename, "w") as h5:
    run = h5.require_group("Tank/linearization/transient/runs/base")
    write_result(run, 1.0, 1.0)
    points = run.create_group("points")
    write_result(points.create_group("0"), 0.1, 0.8)
    write_result(points.create_group("1"), 0.3, 0.9)

    steady = h5.require_group("Tank/linearization/steady_state/runs/base")
    write_result(steady, 1.0, 1.0)
    steady.attrs["solver_type"] = "steady_state"

print("Created", filename)
