# FullPlot

[![PyPI version](https://img.shields.io/pypi/v/fullplot)](https://pypi.org/project/fullplot/)
[![Python](https://img.shields.io/pypi/pyversions/fullplot)](https://pypi.org/project/fullplot/)
[![License](https://img.shields.io/github/license/saakethramoju/FullPlot)](https://github.com/saakethramoju/FullPlot)

FullPlot is a Python package for reading, plotting, and processing engineering simulation and test data. It provides a consistent API for **HDF5 inspection, time-history traces, shared time axes, line and heat-map plotting, multidimensional maps, and saved state-space linearizations**.

The package is designed to work naturally with [FullFlow](https://github.com/saakethramoju/FullFlow) output, but most features work with ordinary HDF5 files and NumPy arrays. **FullFlow is not required to read previously saved linearization results.**

FullPlot does not simulate physical systems, solve differential equations, or calculate state-space Jacobians. It reads and presents data produced by other tools.

## Installation

Install FullPlot from PyPI:

```bash
pip3 install fullplot
```

To set up FullPlot for the repository examples, use:

```bash
pip3 install "fullplot[examples]"
```

## Quick start

```python
import fullplot as fplt

file = fplt.open("simulation.h5")
file.tree(max_depth=3)

run = file.at("/My_Network/transient/runs/base")
run.plot(x="time", y=["tank_pressure", "mass_flow"])
```

An HDF5 file can also contain linearizations:

```python
file = fplt.open("Linearization.h5")
file.linearizations()

linear = file.linearization(solver="steady_state")
print(linear.A, linear.B, linear.C, linear.D)
```

Both workflows start with `fplt.open(...)`. A file handle stores only a filename and a root group; data is read on demand.

## HDF5 files and inspection

### File and group selection

```python
file = fplt.open("results.h5")
file.tree()
file.list()

run = file.at("/Network/transient/runs/base")
print(run.read("time"))
```

- `fplt.open(filename, root="/")`: open a file and optionally select an initial group.
- `file.at(group)`: return another handle scoped to an HDF5 group.
- `file.tree(max_depth=...)`: print a group/dataset tree.
- `file.list()`: categorize numeric and nonnumeric datasets by dimensionality.
- `file.read(name)`: return the raw dataset as a NumPy value.
- `file.values(...)`: inspect scalar datasets.

A dataset can be selected by absolute path, relative path, or an unambiguous short name. Use `.at()` to eliminate name collisions when working with larger files.

Module-level shortcuts are also available:

```python
fplt.tree("results.h5", max_depth=3)
values = fplt.read("results.h5", "time", root="/Network/transient/runs/base")
```

## Reading FullFlow linearizations

FullPlot can read **previously calculated** FullFlow steady-state and transient linearization records. The result is a labeled `Linearization` object containing the state-space matrices and the operating point at which they were computed.

A continuous-time linear model takes the form

\[
\Delta\dot{x}=A\Delta x+B\Delta u
\]

\[
\Delta y=C\Delta x+D\Delta u
\]

where:

- `x`: physical dynamic state vector (for example stored mass or energy),
- `u`: selected input vector (for example valve area),
- `y`: selected output vector (for example chamber pressure),
- `A`: how state changes affect the state derivatives,
- `B`: how input changes affect the state derivatives,
- `C`: how state changes affect outputs,
- `D`: how input changes directly affect outputs.

`\Delta` denotes a deviation from the saved operating point. For a non-equilibrium transient point, the model also needs the saved baseline derivative:

\[
\dot{x}\approx\dot{x}_0+A(x-x_0)+B(u-u_0)
\]

\[
y\approx y_0+C(x-x_0)+D(u-u_0)
\]

FullPlot **does not create these matrices**. It reads them from FullFlow's linearization HDF5 output, without needing the original nonlinear network or property-model packages.

### Discover available results

```python
import fullplot as fplt

file = fplt.open("Linearization.h5")
info = file.linearizations()
```

`linearizations()` prints a summary of each available run and returns a list of dictionaries. Each record includes `network`, `solver`, `run`, `path`, `time`, matrix dimensions (`states`, `inputs`, `outputs`), and saved transient point times (`times`). When only transient points were saved, `time` is `None` because there is no separate base result.

For programmatic discovery without printing:

```python
info = file.linearizations(print_output=False)

for run in info:
    print(run["solver"], run["time"], run["times"])
```

### Read one linearization

```python
steady = file.linearization(solver="steady_state")

print(steady.A)
print(steady.B)
print(steady.C)
print(steady.D)
```

Read the final/base transient result with:

```python
final = file.linearization(solver="transient")
```

Omitting `time` selects the **base result**, not the latest point stored in `points/`. If only saved points are present, specify `time=` or `times=`. If the file contains both steady-state and transient records, select `solver=` explicitly. If only one record is available, it can be inferred.

### Read transient operating points

```python
point = file.linearization(solver="transient", time=0.1)

print(point.time)
print(point.A.shape)
print(point.states)
```

Read several points at once:

```python
points = file.linearization(
    solver="transient",
    times=[0.1, 0.3],
)

for requested_time, linear in points.items():
    print(requested_time, linear.A, linear.D)
```

`times=` returns an ordinary dictionary keyed by the **requested** times, even if HDF5 stores `0.3` as `0.30000000000000004`. Times are matched within a narrow floating-point tolerance. If a time does not exist, FullPlot reports the available point times. If multiple points match the same time, it rejects the ambiguous selection.

Saved points can have **different numbers of states, inputs, or outputs**. FullPlot returns each result independently; it does not attempt to concatenate incompatible matrices.

### Scope into a run

```python
run = file.at("/Water_Flow/linearization/transient/runs/base")

point = run.linearization(time=0.1)
final = run.linearization()
```

A handle scoped directly to a point group can read that point without a time argument:

```python
point = file.at(
    "/Water_Flow/linearization/transient/runs/base/points/0"
).linearization()
```

If several networks contain matching records, `.linearization()` raises an ambiguity error instead of choosing one arbitrarily. Use `.at()` to select the desired network or run. For non-base model-option runs, scope to the run group or supply its HDF5 run path (such as `run="Pump_Model/polytropic"`). A single unambiguous non-base run can also be selected automatically.

### Data available in `Linearization`

| Attribute | Description |
| --- | --- |
| `A`, `B`, `C`, `D` | NumPy state-space matrices |
| `x0`, `xdot0`, `u0`, `y0` | Nominal states, state rates, inputs, and outputs |
| `states`, `inputs`, `outputs` | Ordered Python string tuples corresponding to matrix rows and columns |
| `time` | Operating-point time |
| `diagnostics` | Saved condition numbers and other numerical diagnostics |
| `model_options` | Saved FullFlow model-option metadata |
| `network`, `solver`, `run`, `path` | Source identification and HDF5 path |

Dimensions are checked on reading:

\[
A\in\mathbb R^{n_x\times n_x},\quad B\in\mathbb R^{n_x\times n_u},\quad
C\in\mathbb R^{n_y\times n_x},\quad D\in\mathbb R^{n_y\times n_u}.
\]

FullPlot validates the baseline-vector lengths and requires compatible label counts. HDF5 byte strings are decoded to regular Python strings. Incorrect or missing datasets raise `LinearizationError`.

### Using the matrices

Matrix labels determine the meaning of each row and column:

```python
linear = file.linearization(solver="transient", time=0.1)

state_index = linear.states.index("Pipe 1.mass_flow")
input_index = linear.inputs.index("Pipe 1.cross_sectional_area")

sensitivity = linear.B[state_index, input_index]
print(sensitivity)
```

For a small deviation from the nominal operating point:

```python
import numpy as np

dx = np.zeros(len(linear.states))
du = np.zeros(len(linear.inputs))
du[0] = 1e-6

xdot = linear.xdot0 + linear.A @ dx + linear.B @ du
y = linear.y0 + linear.C @ dx + linear.D @ du
```

These are **local predictions**, not a substitute for the nonlinear model away from the operating point. FullPlot reads the saved arrays; it does not provide built-in eigenvalue analysis, controller tuning, state-space integration, linearization heat maps, or matrix-coefficient trace extraction.

### FullFlow HDF5 format

The reader supports the current FullFlow per-run and per-point layout:

```text
Network/
  linearization/
    steady_state/
      runs/
        base/
          A, B, C, D
          x0, xdot0, u0, y0
          states, inputs, outputs, time
          diagnostics/, model_options/
    transient/
      runs/
        base/
          A, B, C, D
          x0, xdot0, u0, y0
          states, inputs, outputs, time
          diagnostics/, model_options/
          points/
            0/
              A, B, C, D, ...
              time
            1/
              A, B, C, D, ...
              time
```

Reading a saved linearization is **not** the same as calculating one from a normal simulation-history file. Ordinary result traces alone cannot determine the original system equations or their derivatives. Matrix generation remains FullFlow's responsibility.

### Linearization examples

Run the small demo generator, then the two reading examples:

```bash
python examples/linearization/0generate_linearization_data.py
python examples/linearization/1inspect_linearization.py
python examples/linearization/2read_transient_points.py
```

The demo uses a tiny, self-contained HDF5 file in FullFlow's export format. Replace its filename with your own FullFlow result to inspect real networks. No FullFlow dependency is needed for these reading examples.

## Traces

A `Trace` stores a one-dimensional x/y series, its name and its plotting role. Traces can be created from HDF5 datasets or directly from arrays and reused across plotting calls.

### Read one trace

```python
run = fplt.open("simulation.h5").at("/Network/transient/runs/base")
trace = run.trace(y="tank_pressure", x="time")

print(trace.x)
print(trace.y)
```

`trace(...)` also accepts existing `Trace` objects, NumPy arrays, and a `TimeAxis` for its x-values. When a dataset has multiple dimensions, select a valid slice before converting it into a one-dimensional trace.

### Create traces from arrays

```python
import numpy as np
import fullplot as fplt

time = np.linspace(0, 10, 101)
pressure = 2e6 + 1e5 * np.sin(time)

trace = fplt.Trace(x=time, y=pressure, name="Tank Pressure", role="data")
```

Supported roles are `data`, `redline`, `blueline`, `greenline`, `yellowline`, and `command`. Roles influence how traces are styled, but do not execute commands, enforce redlines, or implement a controller.

### Shared time axes

A `TimeAxis` can be shared across related traces so all of them use the same time shift and window.

```python
axis = fplt.TimeAxis([0, 1, 2, 3, 4], name="Time")

p = fplt.Trace(x=axis, y=[1, 2, 3, 4, 5], name="Pressure")
q = fplt.Trace(x=axis, y=[5, 4, 3, 2, 1], name="Flow")

axis.window(1, 3)
print(p.y, q.y)
axis.clear_window()
```

`TimeAxis` preserves its complete raw data, even when windowing is active. `full_values`, `raw_count`, `raw_duration`, and `raw_dt_array` describe the original axis. `values`, `count`, `duration`, and `dt_array` describe the active time window. This allows a shared axis to be shifted or cropped without destroying the original samples.

### Missing values

Non-finite y-values are preserved as gaps, not replaced with zeros. The original trace data remains available through `raw_y` when using a shared time axis. Filtering, resampling, and alignment can be applied independently of the source HDF5 file.

### Filtering and math

Traces support common processing operations including moving averages, resampling, derivatives, and arithmetic. For example:

```python
filtered = trace.filter(method="moving_average", window=5)
```

Consult `examples/traces/` for the precise filter signatures, data alignment rules, and more elaborate trace math, including error traces and shared time-axis windows.

### Write processed traces

```python
fplt.write_traces("processed.h5", [trace, filtered])
```

This creates a new HDF5 trace collection. It does not modify the original simulation file unless you explicitly select that file as the output.

## Line plotting

```python
run = fplt.open("simulation.h5").at("/Network/transient/runs/base")

run.plot(
    x="time",
    y=["tank_pressure", "chamber_pressure"],
    y2="mass_flow",
    xlabel="Time [s]",
    ylabel="Pressure [Pa]",
    y2label="Mass Flow [kg/s]",
    title="Feed System",
    save="feed_system.png",
)
```

`plot()` supports custom labels, axes, limits (`xlim`, `ylim`, `y2lim`), logarithmic scales (`xscale`, `yscale`, `y2scale`), legends, grids, themes, image saving, and direct `Trace` objects. Display limits change only the visible figure and do not edit trace data.

```python
fplt.plot([trace, filtered], title="Signal Comparison")
fplt.show()
```

Use `examples/hdf5_plotting/` for dual-axis plots, logarithmic axes, custom themes, image export, and multidimensional line slices.

## Multidimensional data and heat maps

FullPlot can read arrays with more than one axis and plot selected slices. The underlying HDF5 dataset is always available through `.read()` for direct NumPy work.

For a two-dimensional field, use a heat map:

```python
maps = fplt.open("results.h5").at("/maps")

maps.map(
    z="pressure_map",
    x="time",
    y="station",
    title="Pressure Distribution",
    zlabel="Pressure [Pa]",
)
```

You can also use `plot()` with `slice=` and `axis=` to reduce multidimensional data to one-dimensional traces. See `examples/hdf5_plotting/` for how physical x/y coordinates, nearest-value selections, and slice dimensions are handled. Linearization matrices can be read as NumPy arrays, but the `Linearization` object does not provide a dedicated heat-map method.

## Generated maps and interpolation grids

FullPlot can generate rectangular interpolation maps by sweeping one or more input axes. `Axis` describes axis values and spacing; `generate_map` evaluates the supplied callable and stores its outputs in HDF5 for later interpolation or plotting.

```python
from fullplot import Axis, generate_map

pressure = Axis.linear("pressure", 1e5, 5e5, 5)
```

Other axis modes include logarithmic and explicit values. Maps support more than two dimensions even though a heat map visualizes only two at a time. See `examples/maps/` for complete generation and HDF5-layout workflows.

Maps and linearizations are different concepts: a map contains sampled function values across a grid, while a saved state-space linearization contains local derivatives and baseline quantities at one operating point.

## Command-line interface

FullPlot includes a `fullplot` command for HDF5 exploration. Use:

```bash
fullplot --help
```

For command-line inspection examples and the supported options, see `src/fullplot/cli.py`. The Python API remains the primary interface for trace processing and linearization records.

## Public API overview

| API | Purpose |
| --- | --- |
| `fplt.open(filename)` | Open an HDF5 file |
| `file.at(group)` | Scope to an HDF5 group |
| `file.tree()`, `file.list()` | Inspect file structure |
| `file.read(name)`, `file.values()` | Read dataset values |
| `file.time(name)`, `file.trace(...)` | Read engineering time series |
| `file.plot(...)`, `file.map(...)` | Plot line series and maps |
| `file.linearizations()` | Discover saved FullFlow linearizations |
| `file.linearization(...)` | Read one or several saved state-space models |
| `fplt.Trace`, `fplt.TimeAxis` | Reusable time-series objects |
| `fplt.Linearization` | Saved matrix and operating-point container |
| `fplt.Axis`, `fplt.generate_map` | Generate interpolation grids |
| `fplt.write_traces(...)` | Export processed traces to HDF5 |
| `fplt.show()` | Display pending Matplotlib figures |

## Examples

| Folder | Contents |
| --- | --- |
| `examples/hdf5_plotting/` | HDF5 inspection, line plots, heat maps, axes, slicing, themes |
| `examples/traces/` | Reusable traces, shared time axes, filtering, math, alignment, export |
| `examples/maps/` | Axis types, map generation, metadata, HDF5 layout |
| `examples/linearization/` | Discover, read, and inspect FullFlow state-space results |

Most example scripts use files within their own folders. For tracing and HDF5 plotting, run the corresponding `0...` generator script first when the data file does not exist.

## Themes and units

FullPlot offers light and dark plot themes. Labels and units are carried through the available metadata, but **FullPlot does not automatically convert units**. In particular, matrix coefficients in a linearization inherit the units of the physical FullFlow model, and different matrix entries may have different units.

## Limitations and design choices

- FullPlot reads numerical data; it does not run FullFlow solvers, infer equations, or calculate state-space matrices from ordinary traces.
- FullPlot does not implement controller logic or enforce trace redlines. Command traces represent data, not actuator commands sent by FullPlot.
- Time histories, HDF5 datasets, and linearization matrices are loaded as needed. A `Linearization` object holds its arrays in memory after reading.
- A linearization is valid only near its original operating point and operating mode. FullPlot does not verify its physical accuracy.
- Model-option metadata and diagnostic values are read when present; missing optional groups become empty dictionaries.
- Saved linearization times must already exist in the file. FullPlot does not interpolate matrices between operating points.
- Different operating points can have different state/input/output selections, so the reader never assumes compatible matrix sizes.
- The linearization reader supports FullFlow's per-run and per-point HDF5 layout. Files with incompatible layouts require conversion.
- The `Linearization` object does not provide `.plot()` or `.trace()` methods. Its NumPy arrays can be inspected, analyzed, or passed to plotting tools directly.

## License

FullPlot is licensed under GPL-3.0-only. See [LICENSE](LICENSE).
