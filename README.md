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

```python
import fullplot as fplt

run = fplt.open("hotfire.h5")

pcmc = run.trace("pcmc", x="time")
pcmc_filtered = pcmc.filter("moving_average", window=0.05)
redline = fplt.Trace.constant("pcmc Redline", x=pcmc.x, y=400.0, role="redline")

fplt.plot([pcmc, pcmc_filtered, redline])
```

## Generated traces

```python
import numpy as np
import fullplot as fplt

time = np.linspace(0.0, 10.0, 1001)

command = fplt.Trace.from_points(
    "Main Ox Valve Command",
    points=[(0.0, 0.0), (1.0, 0.0), (1.1, 1.0), (8.0, 1.0), (8.1, 0.0)],
    x=time,
    mode="previous",
    role="command",
)

fplt.plot(command)
```

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
