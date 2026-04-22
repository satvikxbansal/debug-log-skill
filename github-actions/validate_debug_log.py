#!/usr/bin/env python3
"""
validate_debug_log.py — sanity-checker for DEBUG_LOG.md (v2.0).

Drop this into `.github/scripts/validate_debug_log.py` in your project.
The companion workflow in `validate-debug-log.yml` invokes it.

Checks performed:

  1. Every heading matching `### DL-NNN` has a short title after the em-dash.
     Titles may be prefixed with `[OBSOLETE]` — these entries are kept in the
     sequence but their prevention rule is marked as retired.
  2. Entry numbers form a contiguous sequence starting at DL-000 or DL-001.
     No gaps, no duplicates, no reuse.
  3. Each entry contains all required v2.0 fields:
       Date, Tags, Severity, Environment, File(s),
       Symptom, Root Cause Category, Root Cause Context,
       Fix, Iterations, Prevention Rule.
  4. Date values parse as YYYY-MM-DD (or contain a YYYY-MM-DD placeholder
     comment for seed entries).
  5. Tags field contains at least one recognised track tag and at least
     one additional semantic tag (any leading `#`-word accepted for the
     semantic tag — the tag taxonomy file is the authoritative list).
  6. Severity is one of the accepted severity labels.
  7. Root Cause Category is one of the 14 canonical categories.
  8. Iterations is a non-negative integer.
  9. Prevention Rule field contains a "Why:" marker and is >= 40 chars.
 10. `[OBSOLETE]` entries are allowed to skip the Prevention Rule strength
     check (they are tombstones), but must still have all structural fields.

Exit code:
  0 — all entries valid.
  1 — one or more problems; details printed to stderr.
  2 — script misuse (bad args, file missing).

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
    "Tags",
    "Severity",
    "Environment",
    "File(s)",
    "Symptom",
    "Root Cause Category",
    "Root Cause Context",
    "Fix",
    "Iterations",
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
    "Informational",
    "Runtime Warning",
    "UX Regression",
    "Security",
}

# Closed vocabulary — see references/tag-taxonomy.md.
VALID_ROOT_CAUSE_CATEGORIES = {
    "API Change",
    "API Deprecation",
    "Race Condition",
    "Scope Leak",
    "Main Thread Block",
    "Hydration Mismatch",
    "Null or Unchecked Access",
    "Type Coercion",
    "Off-By-One",
    "Syntax Error",
    "Config or Build",
    "Test Infrastructure",
    "LLM Hallucination or Assumption",
    "Other",
}

VALID_TRACK_TAGS = {
    "#web",
    "#ios",
    "#android",
    "#macos",
    "#kotlin",
    "#swift",
    "#cross-cutting",
}

ENTRY_HEADING_RE = re.compile(r"^###\s+DL-(\d{3,})\s+[—-]\s+(.+?)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*(.+?)\s*\|\s*$")
TAG_RE = re.compile(r"#[A-Za-z][A-Za-z0-9_-]*")


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


def is_obsolete(title: str) -> bool:
    return title.strip().upper().startswith("[OBSOLETE]")


def strip_markdown(value: str) -> str:
    """Remove backticks and common markdown ornamentation for comparison."""
    return value.replace("`", "").strip()


def validate_entry(num: int, title: str, fields: dict[str, str]) -> list[str]:
    problems: list[str] = []
    prefix = f"DL-{num:03d} ({title})"
    obsolete = is_obsolete(title)

    missing = REQUIRED_FIELDS - set(fields.keys())
    if missing:
        problems.append(f"{prefix}: missing field(s): {', '.join(sorted(missing))}")

    # --- Date ---
    if "Date" in fields:
        date_val = fields["Date"]
        # Accept "YYYY-MM-DD" or "YYYY-MM-DD <!-- ... -->" or
        # "YYYY-MM-DD <!-- fill in when you initialise -->"
        date_token = date_val.split("<!--")[0].strip()
        if date_token and date_token != "YYYY-MM-DD":
            try:
                datetime.strptime(date_token, "%Y-%m-%d")
            except ValueError:
                problems.append(
                    f"{prefix}: Date '{date_val}' does not parse as YYYY-MM-DD."
                )

    # --- Tags ---
    if "Tags" in fields:
        raw_tags = fields["Tags"]
        tags = TAG_RE.findall(raw_tags)
        if not tags:
            problems.append(
                f"{prefix}: Tags '{raw_tags}' contains no #Tag tokens. "
                f"Expected at least one track tag + one semantic tag."
            )
        else:
            # Case-insensitive match for track tags (taxonomy uses lowercase)
            lower = {t.lower() for t in tags}
            if not (lower & {t.lower() for t in VALID_TRACK_TAGS}):
                problems.append(
                    f"{prefix}: Tags '{raw_tags}' is missing a track tag. "
                    f"Expected one of: {sorted(VALID_TRACK_TAGS)}."
                )
            if len(tags) < 2:
                problems.append(
                    f"{prefix}: Tags '{raw_tags}' has only {len(tags)} tag(s). "
                    f"Need at least one track tag + one semantic tag."
                )

    # --- Severity ---
    if "Severity" in fields:
        sev = fields["Severity"]
        tokens = [t.strip() for t in re.split(r"[,/]", sev) if t.strip()]
        invalid = [t for t in tokens if t not in VALID_SEVERITIES]
        if invalid:
            problems.append(
                f"{prefix}: Severity '{sev}' contains invalid label(s): "
                f"{', '.join(invalid)}. Valid: {sorted(VALID_SEVERITIES)}"
            )

    # --- Root Cause Category ---
    if "Root Cause Category" in fields:
        cat = strip_markdown(fields["Root Cause Category"])
        if cat not in VALID_ROOT_CAUSE_CATEGORIES:
            problems.append(
                f"{prefix}: Root Cause Category '{cat}' is not canonical. "
                f"Valid: {sorted(VALID_ROOT_CAUSE_CATEGORIES)}. "
                f"If none fits, use 'Other' and describe the category in "
                f"Root Cause Context."
            )

    # --- Iterations ---
    if "Iterations" in fields:
        it_raw = strip_markdown(fields["Iterations"])
        # Accept a leading integer followed by anything (e.g. "3 (actor race)")
        m_iter = re.match(r"^(\d+)", it_raw)
        if not m_iter:
            problems.append(
                f"{prefix}: Iterations '{it_raw}' is not a non-negative integer."
            )

    # --- Prevention Rule ---
    if "Prevention Rule" in fields:
        rule = fields["Prevention Rule"]
        if not obsolete:
            if "Why:" not in rule and "why:" not in rule:
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
        # Tolerate either DL-000 or DL-001 as the starting entry.
        start = 0 if 0 in numbers else 1
        expected = list(range(start, max(numbers) + 1))
        missing = sorted(set(expected) - set(numbers))
        if missing:
            problems.append(
                "Gap in DL sequence. Missing: "
                + ", ".join(f"DL-{n:03d}" for n in missing)
            )

    return problems


def summary_counts(entries: list[tuple[int, str, list[str]]]) -> dict[str, int]:
    total = len(entries)
    obsolete = sum(1 for (_, t, _) in entries if is_obsolete(t))
    return {"total": total, "active": total - obsolete, "obsolete": obsolete}


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

    counts = summary_counts(entries)

    if problems:
        print("DEBUG_LOG validation failed:\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            f"\n{len(problems)} problem(s) across {counts['total']} entries "
            f"({counts['active']} active, {counts['obsolete']} obsolete).",
            file=sys.stderr,
        )
        return 1

    print(
        f"DEBUG_LOG.md: {counts['total']} entries "
        f"({counts['active']} active, {counts['obsolete']} obsolete), all valid."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
