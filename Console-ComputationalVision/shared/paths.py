"""Filesystem helpers shared across layers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def resolve_project_root(reference: Path) -> Path:
    """Return the repository root given a module ``reference`` file."""

    return reference.resolve().parents[2]


def list_files_with_extensions(root: Path, extensions: Iterable[str]) -> list[Path]:
    """List files under ``root`` matching any extension in ``extensions``."""

    results: list[Path] = []
    if not root.exists():
        return results
    normalised = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in normalised:
            results.append(path)
    return results


def ensure_path_first(paths: list[str], candidate: str | None) -> list[str]:
    """Ensure ``candidate`` is present at the front of ``paths`` if provided."""

    if candidate and candidate not in paths:
        return [candidate] + paths
    return paths
