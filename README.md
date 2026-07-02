# FullPlot

FullPlot is a lightweight HDF5 plotting, trace filtering, and map-generation package for engineering simulation and test data.


## Installation

```bash
pip install fullplot
```

For local development with `uv`:

```bash
uv sync --dev
uv run pytest
```

## Quick plotting

```python
import fullplot as fplt

run = fplt.open("engine_sim.h5")
run.tree()
run.list()

run.plot(
    x="time",
    y="node_pressure",
    xlabel="Time [s]",
    ylabel="Pressure [Pa]",
)
```

## Traces

A `Trace` is a generic one-dimensional line of data. It can represent simulation data, test data, a filtered trace, a redline, a blueline, a command trace, or a derived trace.

FullPlot does not have a special test-data object. If your HDF5 file contains normal datasets such as `time`, `PCMC_1`, `PBTC_1`, and `SHAFT_RPM_1`, you can plot them directly:

```python
import fullplot as fplt

run = fplt.open("hotfire.h5")
run.plot(x="time", y=["PCMC_1", "PCMC_2", "PCMC_3"])
```

Use `trace()` when you want to extract a reusable line, filter it, create redlines/bluelines, combine data from multiple files, or do trace math:

```python
import fullplot as fplt

run = fplt.open("hotfire.h5")
time = run.time("time")

pcmc = run.trace(y="PCMC_1", x=time)
pcmc_filtered = pcmc.filter("moving_average", window=0.05)
redline = fplt.Trace.constant("PCMC Redline", x=time, y=400.0, role="redline")

# Shift the shared time axis so original test time 95.0 becomes model time 0.
time.zero_at(95.0)

fplt.plot([pcmc, pcmc_filtered, redline])
```

`TimeAxis` objects are useful when several traces should share one shifted time basis. `file.time("time")` reads a 1D HDF5 time dataset as a shared time object. Every trace built with `x=time` uses the current shifted values from that same object. Use `time.zero_at(test_time)` or `time.align(data_time=test_time, model_time=model_time)` to change where `t = 0` is located.

`Trace.window(start, stop)` keeps the full time axis and replaces values outside the selected interval with `NaN`. This makes partial test-data windows easy to plot and easy for downstream solvers to treat as missing data outside the active interval. Non-finite y-values such as `NaN` are preserved in traces and show up as plot gaps; use `omit_missing()` when you explicitly want a compact finite trace.

## Generated traces and roles

Trace roles are only plotting hints. They do not implement abort logic or limit checking. The special role colors are intentionally slightly different from the normal line-color cycle in light and dark themes so redlines, bluelines, warning lines, and ordinary data traces are not confused.

```python
import fullplot as fplt

redline = fplt.Trace.constant("Abort Limit", x=pcmc.x, y=400.0, role="redline")
yellowline = fplt.Trace.constant("Warning Limit", x=pcmc.x, y=350.0, role="yellowline")
blueline = fplt.Trace.constant("Low Reference", x=pcmc.x, y=100.0, role="blueline")

command = fplt.Trace.from_points(
    "Main Ox Valve Command",
    points=[(0.0, 0.0), (1.0, 0.0), (1.1, 1.0), (8.0, 1.0), (8.1, 0.0)],
    x=pcmc.x,
    mode="previous",
    role="command",
)

fplt.plot([pcmc, redline, yellowline, blueline, command])
```

See `examples/traces/` for detailed examples covering generated sensor data, filtering, redlines/bluelines, commands, trace math, resampling, derivatives, saving processed traces, and missing-value handling.

## Map generation

FullPlot can generate simple rectangular-grid HDF5 maps. The layout is intentionally generic: a map group contains one `/axes` group, one `/outputs` group, and optional metadata. FullFlow can read this layout with `Map.from_hdf5(...)`, but the file is just HDF5 and does not require FullFlow.

```python
import fullplot as fplt

fplt.generate_map(
    "demo_map.h5",
    group="properties",
    axes=[
        fplt.Axis.linear("pressure", 1.0e5, 5.0e5, 5, units="Pa"),
        fplt.Axis.linear("temperature", 250.0, 500.0, 6, units="K"),
    ],
    constants={"gas_constant": 287.0},
    evaluate=lambda pressure, temperature, gas_constant: {
        "density": pressure / (gas_constant * temperature),
    },
    overwrite=True,
)
```

`Axis` defines the independent variables that are swept while the map is generated:

```python
fplt.Axis.linear("temperature", start=250.0, stop=600.0, count=8)
fplt.Axis.log("pressure", start=1.0e5, stop=1.0e7, count=9)
fplt.Axis.values("mixture_ratio", values=[1.5, 2.0, 2.5, 3.0])
```

Use `constants={...}` for inputs that should be passed to every map evaluation but should not become interpolation axes. The `evaluate` function must return a flat dictionary of scalar numeric outputs. Each key becomes one dataset in `/outputs`.

See `examples/maps/` for detailed map-generation examples.
