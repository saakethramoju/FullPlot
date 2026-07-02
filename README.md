# FullPlot

FullPlot is a lightweight HDF5 plotting, trace filtering, and map-generation package for engineering simulation and test data.

FullPlot is intentionally independent from FullFlow. FullPlot does not import FullFlow, and FullFlow does not import FullPlot. HDF5 files are the interface between the two packages.

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

chpt = run.trace("CHPT", x="time")
chpt_filtered = chpt.filter("moving_average", window=0.05)
redline = fplt.Trace.constant("CHPT Redline", x=chpt.x, y=400.0, role="redline")

fplt.plot([chpt, chpt_filtered, redline])
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

FullPlot can generate rectangular HDF5 maps that another package, including FullFlow, can consume later.

```python
import fullplot as fplt

fplt.generate_map(
    "demo_map.h5",
    group="properties",
    axes=[
        fplt.Axis.linear("pressure", 1.0e5, 5.0e5, 5),
        fplt.Axis.linear("temperature", 250.0, 500.0, 6),
    ],
    evaluate=lambda pressure, temperature: {
        "density": pressure / (287.0 * temperature),
    },
)
```