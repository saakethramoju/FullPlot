# Reading FullFlow linearizations

These examples demonstrate FullPlot 2.0.0's read-only linearization API.
They do not generate new Jacobians or require FullFlow.

From the repository root, run:

```bash
python examples/linearization/0generate_linearization_data.py
python examples/linearization/1inspect_linearization.py
python examples/linearization/2read_transient_points.py
```

`0generate_linearization_data.py` produces `linearization_demo.h5`, a small
illustrative file with a steady-state result, a base transient result, and
transient operating points at 0.1 and 0.3 seconds.

`1inspect_linearization.py` discovers available runs and reads one set of
steady-state A, B, C, D matrices, labels, and diagnostics.

`2read_transient_points.py` loads the final transient result, returns a
dictionary for multiple saved times, and demonstrates scoping to a run
using `.at()`.

To use actual FullFlow results, replace `linearization_demo.h5` with your
saved HDF5 filename. The loaded matrices retain their original units and
refer to the saved operating points; FullPlot does not recompute them.
