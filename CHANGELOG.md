# Changelog

## 0.0.1

Initial standalone FullPlot package.

- Add HDF5 file inspection and dataset reading.
- Add generic `Trace` objects for 1D engineering data.
- Add trace plotting and overlays.
- Add trace filtering utilities.
- Add generated traces for redlines, bluelines, commands, and derived data.
- Add HDF5 trace writing.
- Add HDF5 map generation with `Axis` and `generate_map`.

## Unreleased

- Add detailed trace examples with synthetic hotfire-style HDF5 data generation.
- Add shared `TimeAxis` objects for test/simulation time alignment.
- Add `H5File.time(...)` and module-level `fullplot.time(...)`.
- Change `Trace.window(...)` to preserve the full time axis and mask values outside the window with `NaN`.
- Preserve non-finite y-values in traces so missing test-data samples remain visible as plot gaps.
- Add `Trace.omit_missing()` / `Trace.drop_missing()` for compact finite traces.
- Adjust redline/blueline/yellowline/greenline role colors to avoid confusion with normal data colors.
