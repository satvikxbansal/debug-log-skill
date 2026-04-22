"""
_templates.py — shared entry-skeleton builder.

`stub` and `supersede` both append a skeleton DL entry to the log. The
skeleton has explicit `TODO:` markers in every field the caller did not
provide. This is deliberate: we never want an agent to produce a
syntactically valid but semantically empty entry — the TODO prefix
ensures a human has to actually fill in the Fix / Root Cause Context /
Prevention Rule before the validator will pass.

Conventions:
  * `TODO:` is the marker. Grep-friendly, and the validator's
    Prevention-Rule length check will still flag bare TODOs because
    they're shorter than MIN_RULE_LEN.
  * Every skeleton is timestamped with today's date.
  * Track + semantic tags the caller supplies are rendered literally.
  * Category defaults to `Other` — a valid value that nudges the author
    to pick something more specific before committing.

This module emits a list[str] of markdown lines, NOT a string; callers
concatenate. That keeps the "final newline" discipline in one place (the
append logic).
"""
from __future__ import annotations

from datetime import date

from debug_log_schema import OBSOLETE_PREFIX


_TODO = "TODO:"


def _field(label: str, value: str) -> str:
    return f"| **{label}** | {value} |"


def build_entry_skeleton(
    *,
    num: int,
    title: str,
    tags: list[str] | None = None,
    severity: str | None = None,
    environment: str | None = None,
    files: list[str] | None = None,
    category: str | None = None,
    supersedes: int | None = None,
    today: date | None = None,
) -> list[str]:
    """Return a markdown block for a new DL entry.

    None/empty values become `TODO: <what to write>`. The heading already
    uses the caller's title verbatim — no TODO injection — because an
    entry without a title is degenerate.
    """
    today = today or date.today()
    tag_str = " ".join(tags) if tags else f"{_TODO} #track #Semantic"
    sev_str = severity or f"{_TODO} e.g. Runtime Crash"
    env_str = environment or f"{_TODO} SDK / framework / OS versions in play"
    if files:
        file_str = ", ".join(f"`{f}`" for f in files)
    else:
        file_str = f"{_TODO} `path/to/file.ext`"
    cat_str = category or "Other"

    heading = f"### DL-{num:03d} — {title}"
    lines = [
        "",
        heading,
        "",
        "| Field | Value |",
        "|-------|-------|",
        _field("Date", today.isoformat()),
        _field("Tags", f"`{tag_str}`"),
        _field("Severity", sev_str),
        _field("Environment", env_str),
        _field("File(s)", file_str),
        _field("Symptom", f"{_TODO} observable failure in one sentence."),
        _field("Root Cause Category", cat_str),
        _field(
            "Root Cause Context",
            f"{_TODO} what was believed that turned out false.",
        ),
        _field("Fix", f"{_TODO} what changed; include commit hash when merged."),
        _field("Iterations", "0"),
        _field(
            "Prevention Rule",
            f"{_TODO} specific, checkable rule. **Why:** {_TODO} scar tissue sentence (DL-"
            f"{num:03d}).",
        ),
    ]

    if supersedes is not None:
        lines.append("")
        lines.append(f"> Supersedes DL-{supersedes:03d}.")

    return lines


def tombstone_title(old_title: str) -> str:
    """Prepend `[OBSOLETE]` to `old_title` if not already present."""
    stripped = old_title.lstrip()
    if stripped.upper().startswith(OBSOLETE_PREFIX.upper()):
        return old_title
    return f"{OBSOLETE_PREFIX} {old_title}".strip()
