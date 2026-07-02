import numpy as np

import fullplot as fplt


def test_trace_constant():
    x = np.linspace(0.0, 1.0, 11)
    trace = fplt.Trace.constant("CHPT Redline", x=x, y=400.0, role="redline")

    assert trace.name == "CHPT Redline"
    assert trace.role == "redline"
    assert np.allclose(trace.x, x)
    assert np.allclose(trace.y, 400.0)


def test_trace_window_and_filter():
    x = np.linspace(0.0, 10.0, 101)
    y = np.sin(x)
    trace = fplt.Trace.from_arrays("signal", x=x, y=y)

    windowed = trace.window(2.0, 4.0)
    assert windowed.x.min() >= 2.0
    assert windowed.x.max() <= 4.0

    filtered = trace.filter("moving_average", window=0.2)
    assert filtered.role == "filtered"
    assert filtered.x.shape == trace.x.shape
    assert filtered.y.shape == trace.y.shape


def test_trace_math_resamples_other_trace():
    x1 = np.linspace(0.0, 1.0, 11)
    x2 = np.linspace(0.0, 1.0, 21)
    a = fplt.Trace.from_arrays("a", x=x1, y=x1)
    b = fplt.Trace.from_arrays("b", x=x2, y=2.0 * x2)

    error = b - a
    assert error.role == "derived"
    assert np.allclose(error.y, b.y - b.x)
