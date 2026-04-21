#!/usr/bin/env python3
"""
validate_debug_log.py — sanity-checker for DEBUG_LOG.md.

Drop this into `.github/scripts/validate_debug_log.py` in your project.
The companion workflow in `validate-debug-log.yml` invokes it.

Checks performed:

  1. Every heading matching `### DL-NNN` has a short title after the em-dash.
  2. Entry numbers form a contiguous sequence starting at DL-001. No gaps,
     no duplicates, no reuse.
  3. Each entry contains all seven required fields:
       Date, Severity, Track, File(s), Symptom, Root Cause, Fix, Prevention Rule.
     (Eight keys if you count "File(s)", seven if you consider them fields.)
  4. Date values parse as YYYY-MM-DD.
  5. Severity is one of the accepted severity labels.
  6. Track is one of the accepted track labels.
  7. Prevention Rule field contains a "Why:" marker.

Exit code:
  0 — all entries valid.
  1 — one or more problems; details printed to stderr.

Usage:
  python3 validate_debug_log.py DEBUG_LOG.md
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

REQUIRED_FIELDS = {
    "Date",
    "Severity",
    "Track",
    "File(s)",
    "Symptom",
    "Root Cause",
    "Fix",
    "Prevention Rule",
}

VALID_SEVERITIES = {
    # canonical set, as documented in SKILL.md
    "Build Error",
    "Runtime Crash",
    "ANR",
    "Logic Bug",
    "Flaky Test",
    "Warning-as-Error",
    "Perf Regression",
    "Incident",
    # additional labels accepted in practice
    "Informational",   # used on DL-000 seed entries
    "Runtime Warning", # runtime warning that was not a crash
    "UX Regression",   # non-crash user-visible regression
    "Security",        # security issue / disclosure
}

VALID_TRACKS = {
    "web",
    "ios",
    "android",
    "macos",
    "kotlin",
    "swift",
    "cross-cutting",
}

ENTRY_HEADING_RE = re.compile(r"^###\s+DL-(\d{3,})\s+[—-]\s+(.+?)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*(.+?)\s*\|\s*$")


def split_entries(text: str) -> list[tuple[int, str, list[str]]]:
    """Split the log into (entry_number, title, body_lines) tuples."""
    entries: list[tuple[int, str, list[str]]] = []
    current_num: int | None = None
    current_title: str = ""
    current_body: list[str] = []

    for line in text.splitlines():
        m = ENTRY_HEADING_RE.match(line)
        if m:
            if current_num is not None:
                entries.append((current_num, current_title, current_body))
            current_num = int(m.group(1))
            current_title = m.group(2)
            current_body = []
        elif current_num is not None:
            # stop collecting once we hit the next top-level section
            if line.startswith("## ") and not line.startswith("### "):
                entries.append((current_num, current_title, current_body))
                current_num = None
                current_title = ""
                current_body = []
            else:
                current_body.append(line)

    if current_num is not None:
        entries.append((current_num, current_title, current_body))

    return entries


def parse_fields(body_lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body_lines:
        m = TABLE_ROW_RE.match(line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields


def validate_entry(num: int, title: str, fields: dict[str, str]) -> list[str]:
    problems: list[str] = []
    prefix = f"DL-{num:03d} ({title})"

    missing = REQUIRED_FIELDS - set(fields.keys())
    if missing:
        problems.append(f"{prefix}: missing field(s): {', '.join(sorted(missing))}")

    if "Date" in fields:
        date_val = fields["Date"]
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            problems.append(
                f"{prefix}: Date '{date_val}' does not parse as YYYY-MM-DD."
            )

    if "Severity" in fields:
        sev = fields["Severity"]
        # Allow comma/slash separated list but each token must be valid
        tokens = [t.strip() for t in re.split(r"[,/]", sev) if t.strip()]
        invalid = [t for t in tokens if t not in VALID_SEVERITIES]
        if invalid:
            problems.append(
                f"{prefix}: Severity '{sev}' contains invalid label(s): "
                f"{', '.join(invalid)}. Valid: {sorted(VALID_SEVERITIES)}"
            )

    if "Track" in fields:
        trk = fields["Track"]
        tokens = [t.strip() for t in re.split(r"[,/]", trk) if t.strip()]
        invalid = [t for t in tokens if t not in VALID_TRACKS]
        if invalid:
            problems.append(
                f"{prefix}: Track '{trk}' contains invalid label(s): "
                f"{', '.join(invalid)}. Valid: {sorted(VALID_TRACKS)}"
            )

    if "Prevention Rule" in fields:
        rule = fields["Prevention Rule"]
        if "Why:" not in rule:
            problems.append(
                f"{prefix}: Prevention Rule is missing a 'Why:' one-liner."
            )
        if len(rule) < 40:
            problems.append(
                f"{prefix}: Prevention Rule is suspiciously short "
                f"({len(rule)} chars). Be specific."
            )

    return problems


def validate_sequence(entries: list[tuple[int, str, list[str]]]) -> list[str]:
    problems: list[str] = []
    numbers = [num for (num, _, _) in entries]

    seen: set[int] = set()
    for num in numbers:
        if num in seen:
            problems.append(f"Duplicate entry number DL-{num:03d}.")
        seen.add(num)

    if numbers:
        expected = list(range(1, max(numbers) + 1))
        missing = sorted(set(expected) - set(numbers))
        if missing:
            problems.append(
                "Gap in DL sequence. Missing: "
                + ", ".join(f"DL-{n:03d}" for n in missing)
            )

    return problems


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_debug_log.py <path-to-DEBUG_LOG.md>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"error: {path} does not exist.", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    entries = split_entries(text)

    if not entries:
        print(
            "warning: no DL-NNN entries found in DEBUG_LOG.md. "
            "If this is a fresh project, that's fine."
        )
        return 0

    problems: list[str] = []
    problems.extend(validate_sequence(entries))
    for num, title, body in entries:
        fields = parse_fields(body)
        problems.extend(validate_entry(num, title, fields))

    if problems:
        print("DEBUG_LOG validation failed:\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            f"\n{len(problems)} problem(s) across {len(entries)} entries.",
            file=sys.stderr,
        )
        return 1

    print(f"DEBUG_LOG.md: {len(entries)} entries, all valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
