import fullplot as fplt


def test_public_api_imports():
    assert fplt.Trace is not None
    assert fplt.H5File is not None
    assert fplt.Axis is not None
    assert fplt.generate_map is not None
    assert isinstance(fplt.__version__, str)
