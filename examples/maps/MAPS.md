# Map generation examples

FullPlot can generate rectangular-grid HDF5 maps. A generated map group has this basic layout:

```text
/<map_group>
    attrs:
        axis_order = '["axis_1", "axis_2", ...]'

    /axes
        /axis_1
        /axis_2

    /outputs
        /output_1
        /output_2

    /status
        /success
        /message
```

Only `/axes/<axis_name>` and `/outputs/<output_name>` are required for a basic reader. Metadata, constants, status arrays, units strings, and spacing attributes are helpful but optional for generic HDF5 use.

`Axis` controls how each independent variable is swept:

- `Axis.linear(...)` uses evenly spaced values from `np.linspace`.
- `Axis.log(...)` uses logarithmically spaced physical values from `np.geomspace` and stores `spacing="log"`.
- `Axis.values(...)` uses explicit user-provided breakpoints.

The map generator calls `evaluate(**inputs)` at every grid point. Axis names become keyword arguments, and entries in `constants={...}` are also passed as keyword arguments but are not swept.
