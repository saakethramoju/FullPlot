# FullPlot Trace Examples

These examples focus on FullPlot's generic `Trace` workflow.

A `Trace` is just one reusable line of data:

```python
Trace(x=array, y=array, name="PCMC_1", role="data")
```

It can represent test data, simulation data, filtered data, redlines, bluelines,
commands, sequence states, derived quantities, or anything else that can be drawn
as one line.

## Example order

Run the examples from this directory or from the repository root.

1. `0_generate_trace_demo_file.py`  
   Creates `trace_demo.h5`, a synthetic hotfire-style file with many sensor traces.

2. `1_quick_hdf5_trace_plot.py`  
   Uses the simple HDF5 plotting API: `file.plot(x="time", y=[...])`.

3. `2_extract_trace_and_filter.py`  
   Extracts `Trace` objects and applies moving-average, median, and Savitzky-Golay filters.

4. `3_create_redlines_bluelines.py`  
   Creates redline, yellowline, blueline, and greenline traces using `Trace.constant()`.

5. `4_command_and_sequence_traces.py`  
   Shows command traces from HDF5 and generated command traces from time/value points.

6. `5_trace_math_resample_error.py`  
   Demonstrates trace math and automatic resampling for simulation/test comparison.

7. `6_window_scale_offset_derivative.py`  
   Demonstrates `window()`, `scale()`, `offset()`, and `derivative()`.

8. `7_save_processed_traces.py`  
   Saves raw, filtered, and generated traces to a new HDF5 file.

9. `8_missing_nan_values_are_omitted.py`  
   Shows that NaN/missing samples are automatically omitted in Trace workflows.

## Core workflow

```python
import fullplot as fplt

file = fplt.open("trace_demo.h5")
pc = file.trace(y="PCMC_1", x="time")
pc_filtered = pc.filter("moving_average", window=0.05)
redline = fplt.Trace.constant("PCMC Redline", x=pc.x, y=400.0, role="redline")

fplt.plot([pc, pc_filtered, redline])
```

FullPlot does not manage units or calibrations. It assumes the HDF5 data is
already in the form you want to analyze and plot.
