"""
debug_log_parser.py — shared parsing for DEBUG_LOG.md.

Both the validator and the `dls` CLI read entries out of a `DEBUG_LOG.md`
file. Before v2.1 the parsing logic lived inside the validator; the CLI grew
a second copy which then drifted. This module is the one place entries get
parsed, so both tools see the log the same way.

Contract:
  * Input is raw DEBUG_LOG.md text (file contents).
  * Output is a list of `Entry` dataclasses, in document order.
  * HTML-commented example entries are stripped before parsing (the shipped
    template carries a commented example so new users have a shape to copy).

This module is stdlib-only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from debug_log_schema import (
    OPTIONAL_FIELDS_SET,
    REQUIRED_FIELDS_SET,
    SUPERSEDES_RE,
    TABLE_ROW_RE,
    TAG_RE,
    VALID_TRACK_TAGS_LOWER,
    is_obsolete,
    partition_tags,
    strip_html_comments,
    strip_markdown,
)

# `### DL-NNN — Title` — line-anchored (multi-line search uses splitlines).
# Mirrors debug_log_schema.ENTRY_HEADING_RE but recompiled here so callers
# don't have to pass re.MULTILINE.
_ENTRY_HEADING_RE = re.compile(
    r"^###\s+DL-(\d{3,})\s+[\u2014\u2013\u002D-]\s+(.+?)\s*$"
)


@dataclass(frozen=True)
class Entry:
    """One DEBUG_LOG entry parsed out of markdown.

    Attributes:
      num: The numeric part of DL-NNN (e.g. 23 for DL-023).
      title: The heading text after the em-dash (including `[OBSOLETE]`
        prefix when present).
      body: The raw body lines between this heading and the next one, with
        comments already stripped.
      fields: Parsed table rows — the canonical entry contract.
      raw_tags: Tag tokens found in `Tags` (empty if that field is missing).
      track_tags: Subset of raw_tags that are canonical track tags.
      semantic_tags: Subset of raw_tags that are NOT track tags.
      is_obsolete: Title starts with `[OBSOLETE]`.
      supersedes: List of DL-NNN numbers referenced in the body via
        `Supersedes DL-NNN`.
    """

    num: int
    title: str
    body: list[str]
    fields: dict[str, str]
    raw_tags: list[str]
    track_tags: list[str]
    semantic_tags: list[str]
    is_obsolete: bool
    supersedes: list[int] = field(default_factory=list)

    @property
    def dl_id(self) -> str:
        """Canonical `DL-NNN` id (zero-padded to 3 digits)."""
        return f"DL-{self.num:03d}"

    def active(self) -> bool:
        """Convenience inverse of is_obsolete."""
        return not self.is_obsolete

    def get(self, field_name: str, default: str = "") -> str:
        """Lookup a table field by its label; returns `default` if absent."""
        return self.fields.get(field_name, default)

    def files(self) -> list[str]:
        """Parse the `File(s)` field into individual path strings.

        Accepts comma-separated or newline-separated values, with markdown
        backticks stripped. Paths that happen to contain a comma (rare) are
        untangled at the caller's risk.
        """
        raw = self.get("File(s)")
        if not raw:
            return []
        cleaned = strip_markdown(raw)
        # Break on commas first — most entries use `a.py, b.py`. Fallback
        # to newlines for rare multi-line values.
        pieces: list[str] = []
        for part in re.split(r"[,\n]", cleaned):
            p = part.strip().strip("`").strip()
            if p:
                pieces.append(p)
        return pieces


def parse_fields(body_lines: list[str]) -> dict[str, str]:
    """Parse the `| **Label** | value |` markdown table into a dict."""
    fields: dict[str, str] = {}
    for line in body_lines:
        m = TABLE_ROW_RE.match(line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields


def parse_tags(fields: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    """Return (raw, track, semantic) tag lists for an entry's fields."""
    raw_tags = TAG_RE.findall(fields.get("Tags", ""))
    track, semantic = partition_tags(raw_tags)
    return raw_tags, track, semantic


def parse_supersede_targets(body_lines: list[str]) -> list[int]:
    """Return DL numbers this entry supersedes (via `Supersedes DL-NNN`)."""
    joined = "\n".join(body_lines)
    return [int(m.group(1)) for m in SUPERSEDES_RE.finditer(joined)]


def _flush(
    num: int | None,
    title: str,
    body: list[str],
) -> Entry | None:
    if num is None:
        return None
    fields = parse_fields(body)
    raw_tags, track, semantic = parse_tags(fields)
    return Entry(
        num=num,
        title=title,
        body=list(body),
        fields=fields,
        raw_tags=raw_tags,
        track_tags=track,
        semantic_tags=semantic,
        is_obsolete=is_obsolete(title),
        supersedes=parse_supersede_targets(body),
    )


def parse_entries(text: str) -> list[Entry]:
    """Parse `DEBUG_LOG.md` text into an ordered list of `Entry`."""
    text = strip_html_comments(text)

    entries: list[Entry] = []
    current_num: int | None = None
    current_title: str = ""
    current_body: list[str] = []

    for line in text.splitlines():
        m = _ENTRY_HEADING_RE.match(line)
        if m:
            flushed = _flush(current_num, current_title, current_body)
            if flushed is not None:
                entries.append(flushed)
            current_num = int(m.group(1))
            current_title = m.group(2)
            current_body = []
        elif current_num is not None:
            # A new top-level heading closes the current entry.
            if line.startswith("## ") and not line.startswith("### "):
                flushed = _flush(current_num, current_title, current_body)
                if flushed is not None:
                    entries.append(flushed)
                current_num = None
                current_title = ""
                current_body = []
            else:
                current_body.append(line)

    flushed = _flush(current_num, current_title, current_body)
    if flushed is not None:
        entries.append(flushed)

    return entries


def parse_entries_from_path(path: str | Path) -> list[Entry]:
    """Read a file and parse its entries. Convenience wrapper."""
    return parse_entries(Path(path).read_text(encoding="utf-8"))


def next_entry_number(entries: Iterable[Entry]) -> int:
    """Return the next free DL number (max + 1, or 1 if the log is empty)."""
    nums = [e.num for e in entries]
    return (max(nums) + 1) if nums else 1


def find_debug_log(start: str | Path | None = None) -> Path | None:
    """Search upwards from `start` for a `DEBUG_LOG.md`.

    Used by CLI commands so the user can invoke `dls lint` from anywhere
    inside a project tree. Returns None when no log is found.
    """
    cursor = Path(start or Path.cwd()).resolve()
    while True:
        candidate = cursor / "DEBUG_LOG.md"
        if candidate.is_file():
            return candidate
        if cursor.parent == cursor:
            return None
        cursor = cursor.parent


def fields_are_known(field_name: str) -> bool:
    """True if `field_name` is a required OR optional field."""
    return field_name in REQUIRED_FIELDS_SET or field_name in OPTIONAL_FIELDS_SET


__all__ = [
    "Entry",
    "parse_entries",
    "parse_entries_from_path",
    "parse_fields",
    "parse_tags",
    "parse_supersede_targets",
    "next_entry_number",
    "find_debug_log",
    "fields_are_known",
    "VALID_TRACK_TAGS_LOWER",
]
