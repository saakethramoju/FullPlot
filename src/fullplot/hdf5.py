from __future__ import annotations

from pathlib import Path
from typing import Any
import re

import h5py


HDF5_EXTENSIONS = {".h5", ".hdf5"}


def hdf5_path(filename: str | Path) -> Path:
    """Return an HDF5 path, adding .h5 when the suffix is omitted."""
    path = Path(filename)

    if path.suffix == "":
        path = path.with_suffix(".h5")
    elif path.suffix.lower() not in HDF5_EXTENSIONS:
        raise ValueError("Use an HDF5 filename with no extension, .h5, or .hdf5.")

    if path.parent != Path(""):
        path.parent.mkdir(parents=True, exist_ok=True)

    return path


def hdf5_filename(filename: str | Path) -> str:
    """Return an HDF5 filename string, adding .h5 when omitted."""
    return str(hdf5_path(filename))


def safe_group_name(name: Any) -> str:
    """Return a compact HDF5-safe group/dataset name."""
    text = str(name).strip()
    text = re.sub(r"[\\/\x00]", "_", text)
    text = re.sub(r"\s+", "_", text)
    return text or "unnamed"


def dataset_names(group: h5py.Group, excluded: set[str] | None = None) -> list[str]:
    """Return direct child dataset names, excluding any requested names."""
    excluded = set() if excluded is None else set(excluded)
    return [
        name
        for name, item in group.items()
        if name not in excluded and isinstance(item, h5py.Dataset)
    ]
