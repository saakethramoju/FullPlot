import h5py
import numpy as np

import fullplot as fplt


def test_hdf5_read_trace_and_write_traces(tmp_path):
    filename = tmp_path / "data.h5"

    with h5py.File(filename, "w") as h5:
        h5.create_dataset("time", data=np.linspace(0.0, 1.0, 11))
        h5.create_dataset("CHPT", data=np.linspace(100.0, 200.0, 11))

    data = fplt.open(filename)
    names = data.traces()
    assert "CHPT" in names

    chpt = data.trace("CHPT", x="time")
    assert chpt.name == "CHPT"
    assert np.allclose(chpt.y[0], 100.0)

    out = tmp_path / "processed.h5"
    redline = fplt.Trace.constant("CHPT Redline", x=chpt.x, y=250.0, role="redline")
    fplt.write_traces(out, [chpt, redline])

    processed = fplt.open(out)
    saved = processed.trace("traces/CHPT/y", x="traces/CHPT/x")
    assert np.allclose(saved.y, chpt.y)


def test_plot_trace_show_false(tmp_path):
    x = np.linspace(0.0, 1.0, 11)
    trace = fplt.Trace.from_arrays("signal", x=x, y=x**2)
    save = tmp_path / "plot.png"

    fig, ax = fplt.plot(trace, show=False, save=save)

    assert fig is not None
    assert ax is not None
    assert save.exists()
