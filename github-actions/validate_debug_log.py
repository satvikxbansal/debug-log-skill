#!/usr/bin/env python3
"""
validate_debug_log.py — sanity-checker for DEBUG_LOG.md (v2.0+).

Drop this into `.github/scripts/validate_debug_log.py` in your project,
alongside `debug_log_schema.py` and `debug_log_parser.py` (the three files
live side by side). The companion workflow in `validate-debug-log.yml`
invokes this script.

Checks performed:

  1. HTML-commented `### DL-NNN` headings are skipped (the template ships
     with a commented example so users have a shape to copy).
  2. Every heading matching `### DL-NNN` has a short title after the
     em-dash. Titles may be prefixed with `[OBSOLETE]` — these entries
     keep their sequence slot but are skipped by active rule retrieval.
  3. Entry numbers form a contiguous sequence starting at DL-000 or
     DL-001. No gaps. No duplicates.
  4. Each entry contains all 11 v2.0 required fields. Optional fields
     (e.g. `Artifact`) are validated when present but never required.
  5. Date values parse as YYYY-MM-DD (or contain a YYYY-MM-DD placeholder
     for seed entries).
  6. Tags contain 1-2 track tags AND at least one semantic tag. With
     --strict, semantic tags must come from
     `references/tag-taxonomy.md`.
  7. Severity is one of the accepted severities (core + extended).
  8. Root Cause Category is one of the 14 canonical categories.
  9. Iterations is a non-negative integer.
 10. Prevention Rule contains a "Why:" marker and is at least 40 chars
     (active entries only — [OBSOLETE] tombstones are exempt).
 11. [OBSOLETE] entries have a later entry whose body says
     `Supersedes DL-NNN` pointing back. Orphaned tombstones are flagged.
 12. `Supersedes DL-NNN` references point at an existing entry whose
     title starts with `[OBSOLETE]`. Dangling references are flagged.
 13. `Artifact` values (Phase 6 sidecar hook), when present, must either
     resolve to an existing file or use the canonical incident path shape.
     Resolution is relative to the DEBUG_LOG.md's directory.

Exit code:
  0 — all entries valid.
  1 — one or more problems; details printed to stderr.
  2 — script misuse (bad args, file missing, missing schema module).

Usage:
  python3 validate_debug_log.py DEBUG_LOG.md
  python3 validate_debug_log.py --strict DEBUG_LOG.md
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Import the schema + parser modules. In the skill checkout they live at
# ../scripts/; when deployed to .github/scripts/ in a consuming project they
# sit next to this file. Search both.
_here = Path(__file__).resolve().parent
for candidate in (_here, _here.parent / "scripts", _here.parent):
    if (candidate / "debug_log_schema.py").is_file():
        sys.path.insert(0, str(candidate))
        break
else:  # pragma: no cover — only hit when install is broken
    print(
        "error: could not locate debug_log_schema.py next to the validator. "
        "Copy it (and debug_log_parser.py) alongside this script, typically "
        "into .github/scripts/.",
        file=sys.stderr,
    )
    sys.exit(2)

from debug_log_schema import (  # noqa: E402
    INCIDENT_DIR,
    MAX_TRACK_TAGS,
    MIN_RULE_LEN,
    MIN_SEMANTIC_TAGS,
    MIN_TRACK_TAGS,
    REQUIRED_FIELDS_SET,
    SCHEMA_VERSION,
    SEMANTIC_TAGS_TAXONOMY_LOWER,
    VALID_ROOT_CAUSE_CATEGORIES,
    VALID_SEVERITIES,
    VALID_TRACK_TAGS,
    WHY_MARKERS,
    strip_markdown,
)
from debug_log_parser import Entry, parse_entries  # noqa: E402


def _why_marker_present(rule: str) -> bool:
    return any(marker in rule for marker in WHY_MARKERS)


def _validate_artifact(
    entry: Entry, log_dir: Path, prefix: str
) -> list[str]:
    """Artifact paths must resolve or match the canonical incident shape.

    We accept two shapes:
      * A path that exists on disk, relative to the DEBUG_LOG.md's directory.
      * The canonical `.debug-log/incidents/DL-NNN.md` path. If this path
        *doesn't yet exist* we warn softly — the entry may be pointing at an
        artifact that will be created in the same commit, and CI shouldn't
        block on a missing sidecar. Any path that doesn't match either shape
        is an error.
    """
    raw = entry.get("Artifact")
    if not raw:
        return []
    value = strip_markdown(raw)
    # Markdown link shape: `[label](path)` — pull the path.
    m = re.search(r"\(([^)]+)\)", value)
    target = m.group(1) if m else value
    target = target.strip()
    if not target:
        return [f"{prefix}: Artifact is empty."]

    resolved = (log_dir / target).resolve()
    if resolved.exists():
        return []

    # Not on disk — is it the canonical incident shape for this entry?
    canonical = f"{INCIDENT_DIR}/DL-{entry.num:03d}.md"
    if target == canonical:
        # Soft-allow: file not yet written (common in same-PR authoring).
        return []

    return [
        f"{prefix}: Artifact '{target}' does not resolve to an existing "
        f"file (checked relative to {log_dir}). Use a real path or the "
        f"canonical incident path `{canonical}`."
    ]


def validate_entry(
    entry: Entry,
    log_dir: Path,
    *,
    strict: bool = False,
) -> list[str]:
    problems: list[str] = []
    prefix = f"{entry.dl_id} ({entry.title})"

    missing = REQUIRED_FIELDS_SET - set(entry.fields.keys())
    if missing:
        problems.append(
            f"{prefix}: missing field(s): {', '.join(sorted(missing))}"
        )

    # --- Date ---
    if "Date" in entry.fields:
        date_val = entry.fields["Date"]
        # Accept `YYYY-MM-DD` or `YYYY-MM-DD <!-- ... -->`. HTML comments
        # were stripped at parse-time, but the raw `YYYY-MM-DD` placeholder
        # from the seed template is still valid.
        date_token = date_val.split("<!--")[0].strip()
        if date_token and date_token != "YYYY-MM-DD":
            try:
                datetime.strptime(date_token, "%Y-%m-%d")
            except ValueError:
                problems.append(
                    f"{prefix}: Date '{date_val}' does not parse as "
                    f"YYYY-MM-DD."
                )

    # --- Tags ---
    if "Tags" in entry.fields:
        raw_tags = entry.fields["Tags"]
        if not entry.raw_tags:
            problems.append(
                f"{prefix}: Tags '{raw_tags}' contains no #Tag tokens. "
                f"Expected {MIN_TRACK_TAGS}-{MAX_TRACK_TAGS} track tags "
                f"+ at least {MIN_SEMANTIC_TAGS} semantic tag."
            )
        else:
            track_unique = {t.lower() for t in entry.track_tags}
            if len(track_unique) < MIN_TRACK_TAGS:
                problems.append(
                    f"{prefix}: Tags '{raw_tags}' is missing a track tag. "
                    f"Expected at least {MIN_TRACK_TAGS} of: "
                    f"{sorted(VALID_TRACK_TAGS)}."
                )
            if len(track_unique) > MAX_TRACK_TAGS:
                problems.append(
                    f"{prefix}: Tags '{raw_tags}' has {len(track_unique)} "
                    f"track tag(s) (cap is {MAX_TRACK_TAGS}). Pick the "
                    f"primary stack; add more only when the bug truly "
                    f"spans stacks."
                )
            if len(entry.semantic_tags) < MIN_SEMANTIC_TAGS:
                problems.append(
                    f"{prefix}: Tags '{raw_tags}' has no semantic tag. "
                    f"Add at least {MIN_SEMANTIC_TAGS} tag from "
                    f"references/tag-taxonomy.md (e.g. #Compose, "
                    f"#StateFlow, #Hydration)."
                )

            if strict and entry.semantic_tags:
                unknown = [
                    t for t in entry.semantic_tags
                    if t.lower() not in SEMANTIC_TAGS_TAXONOMY_LOWER
                ]
                if unknown:
                    problems.append(
                        f"{prefix}: semantic tag(s) not in taxonomy "
                        f"({', '.join(unknown)}). Either pick a tag from "
                        f"references/tag-taxonomy.md or add yours there "
                        f"in the same commit. [--strict]"
                    )

    # --- Severity ---
    if "Severity" in entry.fields:
        sev = entry.fields["Severity"]
        tokens = [t.strip() for t in re.split(r"[,/]", sev) if t.strip()]
        invalid = [t for t in tokens if t not in VALID_SEVERITIES]
        if invalid:
            problems.append(
                f"{prefix}: Severity '{sev}' contains invalid label(s): "
                f"{', '.join(invalid)}. Valid: {sorted(VALID_SEVERITIES)}"
            )

    # --- Root Cause Category ---
    if "Root Cause Category" in entry.fields:
        cat = strip_markdown(entry.fields["Root Cause Category"])
        if cat not in VALID_ROOT_CAUSE_CATEGORIES:
            problems.append(
                f"{prefix}: Root Cause Category '{cat}' is not canonical. "
                f"Valid: {sorted(VALID_ROOT_CAUSE_CATEGORIES)}. If none "
                f"fits, use 'Other' and describe the category in Root "
                f"Cause Context."
            )

    # --- Iterations ---
    if "Iterations" in entry.fields:
        it_raw = strip_markdown(entry.fields["Iterations"])
        # Accept `3`, `3 (actor race)`, `3 — retries`.
        m_iter = re.match(r"^(\d+)", it_raw)
        if not m_iter:
            problems.append(
                f"{prefix}: Iterations '{it_raw}' is not a non-negative "
                f"integer."
            )

    # --- Prevention Rule ---
    if "Prevention Rule" in entry.fields:
        rule = entry.fields["Prevention Rule"]
        if not entry.is_obsolete:
            if not _why_marker_present(rule):
                problems.append(
                    f"{prefix}: Prevention Rule is missing a 'Why:' "
                    f"one-liner."
                )
            if len(rule) < MIN_RULE_LEN:
                problems.append(
                    f"{prefix}: Prevention Rule is suspiciously short "
                    f"({len(rule)} chars, need >= {MIN_RULE_LEN}). Be "
                    f"specific."
                )

    # --- Artifact (Phase 6, optional) ---
    problems.extend(_validate_artifact(entry, log_dir, prefix))

    return problems


def validate_sequence(entries: list[Entry]) -> list[str]:
    problems: list[str] = []
    numbers = [e.num for e in entries]

    seen: set[int] = set()
    for num in numbers:
        if num in seen:
            problems.append(f"Duplicate entry number DL-{num:03d}.")
        seen.add(num)

    if numbers:
        start = 0 if 0 in numbers else 1
        expected = list(range(start, max(numbers) + 1))
        missing = sorted(set(expected) - set(numbers))
        if missing:
            problems.append(
                "Gap in DL sequence. Missing: "
                + ", ".join(f"DL-{n:03d}" for n in missing)
            )

    return problems


def validate_supersede_handshake(entries: list[Entry]) -> list[str]:
    """Enforce the [OBSOLETE] <-> Supersedes DL-NNN handshake.

    Rules:
      - If an entry is marked [OBSOLETE], at least one *later* entry must
        contain `Supersedes DL-NNN` pointing back at it.
      - If any entry body contains `Supersedes DL-NNN`, the referenced
        entry must exist and its title must start with `[OBSOLETE]`.
    """
    problems: list[str] = []

    by_num: dict[int, Entry] = {e.num: e for e in entries}
    obsolete_nums = [e.num for e in entries if e.is_obsolete]

    supersede_targets: dict[int, list[int]] = {}
    for entry in entries:
        for target in entry.supersedes:
            supersede_targets.setdefault(target, []).append(entry.num)

    # 1. Every [OBSOLETE] has at least one later superseder.
    for obs_num in obsolete_nums:
        refs = supersede_targets.get(obs_num, [])
        later = [r for r in refs if r > obs_num]
        if not later:
            problems.append(
                f"DL-{obs_num:03d} is [OBSOLETE] but no later entry says "
                f"`Supersedes DL-{obs_num:03d}`. Either add a superseding "
                f"entry that explains what replaced the old rule, or "
                f"remove the [OBSOLETE] marker if the rule is still "
                f"active."
            )

    # 2. Every `Supersedes DL-NNN` targets an existing [OBSOLETE] entry.
    for target, sources in supersede_targets.items():
        entry = by_num.get(target)
        if entry is None:
            for src in sources:
                problems.append(
                    f"DL-{src:03d} says `Supersedes DL-{target:03d}` but "
                    f"DL-{target:03d} does not exist."
                )
            continue
        if not entry.is_obsolete:
            for src in sources:
                problems.append(
                    f"DL-{src:03d} says `Supersedes DL-{target:03d}` but "
                    f"DL-{target:03d}'s title does not start with "
                    f"`[OBSOLETE]`. Prepend [OBSOLETE] to the superseded "
                    f"entry's title (the only permitted mutation)."
                )

    return problems


def summary_counts(entries: list[Entry]) -> dict[str, int]:
    total = len(entries)
    obsolete = sum(1 for e in entries if e.is_obsolete)
    return {"total": total, "active": total - obsolete, "obsolete": obsolete}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_debug_log.py",
        description=(
            f"DEBUG_LOG v{SCHEMA_VERSION} validator. Checks structure, "
            f"vocabulary, sequence, and the [OBSOLETE]/Supersedes "
            f"handshake."
        ),
    )
    parser.add_argument(
        "path",
        help="Path to DEBUG_LOG.md",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Also require semantic tags to come from "
            "references/tag-taxonomy.md. Off by default because projects "
            "legitimately add project-specific tags; turn it on once your "
            "taxonomy has stabilised."
        ),
    )
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.is_file():
        print(f"error: {path} does not exist.", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    entries = parse_entries(text)
    log_dir = path.resolve().parent

    if not entries:
        print(
            "warning: no DL-NNN entries found in DEBUG_LOG.md. "
            "If this is a fresh project, that's fine."
        )
        return 0

    problems: list[str] = []
    problems.extend(validate_sequence(entries))
    problems.extend(validate_supersede_handshake(entries))
    for entry in entries:
        problems.extend(
            validate_entry(entry, log_dir, strict=args.strict)
        )

    counts = summary_counts(entries)

    if problems:
        print("DEBUG_LOG validation failed:\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            f"\n{len(problems)} problem(s) across {counts['total']} "
            f"entries ({counts['active']} active, "
            f"{counts['obsolete']} obsolete).",
            file=sys.stderr,
        )
        return 1

    strict_note = " [--strict]" if args.strict else ""
    print(
        f"DEBUG_LOG.md (v{SCHEMA_VERSION}): {counts['total']} entries "
        f"({counts['active']} active, {counts['obsolete']} obsolete), "
        f"all valid.{strict_note}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
