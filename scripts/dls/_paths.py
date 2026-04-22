"""
_paths.py — path resolution helpers for the dls CLI.

The user can run `python3 scripts/dls <cmd>` from any directory. Every
subcommand needs to know:
  * Which `DEBUG_LOG.md` to operate on.
  * Which directory is the repo root (for artifact-link resolution and
    incident-sidecar creation).

This module is the one place that logic lives.
"""
from __future__ import annotations

import sys
from pathlib import Path

from debug_log_parser import find_debug_log


def resolve_log_path(explicit: str | Path | None) -> Path:
    """Find the DEBUG_LOG.md to operate on.

    Precedence:
      1. `--log PATH` if provided (and exists).
      2. Upward search from cwd for `DEBUG_LOG.md`.

    Fails loudly with exit-code 2 if neither yields a file. Every CLI
    subcommand uses this so the error message is consistent.
    """
    if explicit is not None:
        path = Path(explicit).resolve()
        if not path.is_file():
            print(
                f"error: --log '{path}' does not exist or is not a file.",
                file=sys.stderr,
            )
            sys.exit(2)
        return path

    found = find_debug_log()
    if found is None:
        print(
            "error: no DEBUG_LOG.md found. Either cd into a project that "
            "has one, or pass --log PATH. Run `./scripts/init.sh .` "
            "inside a project to create one.",
            file=sys.stderr,
        )
        sys.exit(2)
    return found


def repo_root_for_log(log_path: Path) -> Path:
    """Directory containing DEBUG_LOG.md — treated as the repo root."""
    return log_path.resolve().parent
