import h5py
import numpy as np

import fullplot as fplt


def test_generate_map(tmp_path):
    filename = tmp_path / "map.h5"

    def evaluate(pressure, temperature):
        return {"density": pressure / (287.0 * temperature)}

    result = fplt.generate_map(
        filename,
        group="properties",
        axes=[
            fplt.Axis.linear("pressure", 1.0e5, 2.0e5, 3),
            fplt.Axis.linear("temperature", 250.0, 500.0, 4),
        ],
        evaluate=evaluate,
        overwrite=True,
    )

    assert result.endswith(".h5")

    with h5py.File(filename, "r") as h5:
        density = h5["properties/outputs/density"][()]
        success = h5["properties/status/success"][()]

    assert density.shape == (3, 4)
    assert np.all(success)
