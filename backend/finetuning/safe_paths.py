"""Restricts the file paths the fine-tuning command line tools accept."""

import os
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_in_workspace(path) -> Path:
    """Resolve a path, rejecting anything outside the repository or the temporary directory."""
    resolved = os.path.realpath(path)
    for root in (str(REPO_ROOT), tempfile.gettempdir()):
        base = os.path.realpath(root)
        if resolved.startswith(base + os.sep):
            return Path(resolved)
    raise ValueError(f"Path outside the workspace: {path}")
