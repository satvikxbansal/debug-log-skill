"""
_format.py — tiny output helpers for the dls CLI.

Keep this file minimal. We deliberately avoid colour libraries and any
TTY-detection dance — outputs pipe cleanly into `grep`, `less`, and
GitHub Actions log streams. The helpers here are for layout only.
"""
from __future__ import annotations

from typing import Iterable


def bullet(line: str) -> str:
    """`  - {line}` — the standard `dls` finding format."""
    return f"  - {line}"


def heading(text: str, *, char: str = "=") -> str:
    """`=== {text} ===` — subcommand section header."""
    return f"=== {text} ==="


def hrule(width: int = 60, char: str = "-") -> str:
    """A horizontal rule of `char`s, default 60 cols."""
    return char * width


def aligned(pairs: Iterable[tuple[str, object]], *, gap: int = 2) -> list[str]:
    """Render (label, value) pairs as `label   value` with labels padded.

    Used by stats and query --full for a human-friendly column layout that
    still round-trips through a plain-text pipe.
    """
    pairs = list(pairs)
    if not pairs:
        return []
    width = max(len(str(label)) for label, _ in pairs)
    return [f"{str(label):<{width}}{' ' * gap}{value}" for label, value in pairs]


def count_bar(count: int, max_count: int, *, width: int = 24) -> str:
    """Render a textual bar for a distribution row.

    `count_bar(3, 12)` -> `######....................` (approximately).
    The bar uses `#` for filled cells and `.` for empty — grepable and
    diff-friendly. Degenerate inputs (max == 0) yield an empty bar.
    """
    if max_count <= 0:
        return "." * width
    filled = round((count / max_count) * width)
    filled = max(0, min(width, filled))
    return ("#" * filled) + ("." * (width - filled))
