# Changelog

## 0.1.1

### Added

* Added shared `TimeAxis.window(...)`, `clear_window()`, and `windowed(...)` support so every trace using the same time axis follows one common data window.
* Added `TimeAxis.full_values`, `raw_count`, `raw_duration`, `raw_dt_array`, `window_range`, and `has_window` for working with the original and active time ranges.
* Added `Trace.raw_y` so the original y-data remains available when a shared `TimeAxis` is windowed.
* Added `xlim`, `ylim`, and `y2lim` plotting arguments for display-only axis limits.

### Changed

* Shared `TimeAxis` windowing now propagates automatically through attached traces, HDF5 trace extraction, and direct HDF5 plotting.
* `TimeAxis.count`, `duration`, `dt_array`, and related active-axis properties now describe the current window, while the new `raw_*` properties describe the complete source axis.
* Trace constructors that use a `TimeAxis` preserve the complete source-length data so windows can be changed or cleared later.

## 0.1.0

### Added

* Added detailed public API docstrings across user-facing classes, methods, properties, helper functions, theme helpers, CLI helpers, and exceptions.
* Expanded `README.md` into the primary user guide while no separate documentation site exists.
* Added `PUBLISHING.md` with release validation, smoke-test, artifact-inspection, and upload commands.
* Added `THIRD_PARTY_LICENSES.md` with dependency and licensing notes.
* Added package metadata for changelog and documentation URLs.
* Added source-distribution inclusion rules for repository documentation, examples, and tests.
* Added regression tests for HDF5 inspection, trace creation, shared time-axis behavior, filtering, plotting, map generation, and the CLI.

### Changed

* Bumped the package version to `0.1.0` for the first publish-ready public release.
* Updated the package description and PyPI classifiers to reflect a documented beta release rather than an internal alpha package.
* Made `fullplot.__version__` explicit in the package source instead of returning `0.0.0` when imported from a source checkout.
* Expanded HDF5 inspection, plotting, trace, and map-generation documentation in the README and examples-facing package docs.

### Fixed

* Fixed `TimeAxis.dt_array`, which had accidentally been decorated with `@property` twice and could fail when accessed.
* Fixed `H5File.trace(..., x=array_like)` so array-like x-values and `Trace` objects can be used consistently with plotting.
* Removed generated cache artifacts and operating-system metadata from the publish-ready source tree.

### Packaging

* Added `license-files = ["LICENSE"]` so built wheels include the GPL license text.
* Added `[tool.uv.build-backend]` settings for module naming and source distribution inclusion.
* Verified that build artifacts do not include `.git`, `__pycache__`, `.DS_Store`, or generated local files.

### Notes

* Trace roles remain plotting hints only. They do not implement abort logic, controller logic, command execution, or unit conversion.
* FullPlot still has no separate formal documentation site, so the README and docstrings are intentionally detailed.

## 0.0.1

Initial standalone FullPlot package.

* Added HDF5 file inspection and dataset reading.
* Added generic `Trace` objects for 1D engineering data.
* Added trace plotting and overlays.
* Added trace filtering utilities.
* Added generated traces for redlines, bluelines, commands, and derived data.
* Added HDF5 trace writing.
* Added HDF5 map generation with `Axis` and `generate_map`.

## Unreleased

No unreleased changes yet.
