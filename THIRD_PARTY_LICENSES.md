# Third-party license notes

FullPlot is licensed under `GPL-3.0-only`. See `LICENSE` for the full license text.

FullPlot depends on several third-party Python packages. These dependencies are not vendored into this repository; they are installed by the Python package manager from their own distributions.

## Runtime dependencies

FullPlot declares these runtime dependencies in `pyproject.toml`:

| Package | Used for |
| --- | --- |
| NumPy | Numeric arrays, interpolation, masking, and basic trace operations. |
| SciPy | Signal-processing filters used by `Trace.filter(...)`. |
| h5py | Reading and writing HDF5 files. |
| Matplotlib | Line plots, dual-axis plots, and heat maps. |

## Build and development tools

FullPlot uses these tools for local development, testing, linting, and packaging:

| Package/tool | Used for |
| --- | --- |
| uv / uv_build | Building and publishing package artifacts. |
| pytest | Test execution. |
| ruff | Optional linting. |

## Notes for redistributors

If you redistribute FullPlot, review the dependency metadata from the exact package versions you distribute with it. The dependencies listed above are separate projects with their own license files, notices, authors, and release histories.

The FullPlot source distribution and wheel should include FullPlot's own GPL license file. Dependency license texts are not copied into the FullPlot wheel because the dependencies are not vendored.
