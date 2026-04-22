"""
supersede.py — `dls supersede OLD --title ...` subcommand.

The only permitted mutation of an existing entry is prepending
`[OBSOLETE]` to its title. This command automates that (carefully) and
appends a stub superseder entry whose body says `Supersedes DL-OLD.`

The resulting pair passes the validator's handshake check by
construction — but the human still has to fill the TODOs in the
superseder before the entry will pass full `lint`. That's intentional:
the whole point of superseding is to explain why the old rule no longer
applies, which is a thinking task.

Safety rails:
  * `--dry-run` is the default; `--write` is required to mutate files.
  * Refuses to run if the OLD entry is already obsolete (no double
    tombstones).
  * Refuses to run if the OLD number does not exist.
  * The existing entry heading line is found by regex on the exact text
    (`### DL-NNN — Title`), and we verify the match is unique before
    mutating. Two headings with the same DL number would have already
    failed `lint`, but defence in depth.

Exit codes:
  0 — successfully superseded (or dry-run preview produced).
  2 — invalid input (unknown DL, already obsolete, ambiguous heading).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from debug_log_parser import next_entry_number, parse_entries_from_path

from dls._paths import resolve_log_path
from dls._templates import build_entry_skeleton, tombstone_title


DESCRIPTION = (
    "Tombstone an existing DL-OLD entry (prepend [OBSOLETE] to its title) "
    "and append a stub superseder. Default is dry-run; --write commits."
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "old",
        metavar="DL-NNN",
        help="The entry to tombstone (e.g. DL-007 or 7).",
    )
    parser.add_argument(
        "--title",
        required=True,
        metavar="TEXT",
        help=(
            "Title for the new superseding entry. Should name what "
            "replaced the old rule."
        ),
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="#Tag",
        help="Tag for the new entry (repeatable).",
    )
    parser.add_argument(
        "--category",
        default=None,
        metavar="CATEGORY",
        help="Root Cause Category for the new entry.",
    )
    parser.add_argument(
        "--severity",
        default=None,
        help="Severity for the new entry.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply the mutation. Default is dry-run (preview only).",
    )


def _parse_dl_id(token: str) -> int | None:
    token = token.strip().upper()
    if token.startswith("DL-"):
        token = token[3:]
    try:
        return int(token)
    except ValueError:
        return None


def _normalise_tag(t: str) -> str:
    t = t.strip()
    return t if t.startswith("#") else f"#{t}"


def _heading_pattern(num: int) -> re.Pattern[str]:
    # Anchored to start of line, tolerant of em-dash / en-dash / hyphen.
    return re.compile(
        rf"^(###\s+DL-{num:03d}\s+[\u2014\u2013\u002D-]\s+)(.+?)\s*$",
        flags=re.MULTILINE,
    )


def run(args: argparse.Namespace) -> int:
    num = _parse_dl_id(args.old)
    if num is None:
        print(
            f"error: '{args.old}' is not a DL number (expected DL-NNN "
            f"or NNN).",
            file=sys.stderr,
        )
        return 2

    path = resolve_log_path(args.log)
    entries = parse_entries_from_path(path)
    by_num = {e.num: e for e in entries}

    if num not in by_num:
        print(
            f"error: DL-{num:03d} does not exist in {path}.",
            file=sys.stderr,
        )
        return 2

    old_entry = by_num[num]
    if old_entry.is_obsolete:
        print(
            f"error: DL-{num:03d} is already [OBSOLETE]. Nothing to do.",
            file=sys.stderr,
        )
        return 2

    text = path.read_text(encoding="utf-8")
    pattern = _heading_pattern(num)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        print(
            f"error: expected exactly one heading for DL-{num:03d}, "
            f"found {len(matches)}. Bailing out — fix the log manually.",
            file=sys.stderr,
        )
        return 2

    new_num = next_entry_number(entries)
    tombstoned = tombstone_title(old_entry.title)

    # Build the two diffs we'll apply on --write.
    new_heading_line = f"### DL-{num:03d} \u2014 {tombstoned}"
    patched = pattern.sub(new_heading_line, text, count=1)

    tags = [_normalise_tag(t) for t in args.tag] or None
    skeleton = build_entry_skeleton(
        num=new_num,
        title=args.title,
        tags=tags,
        severity=args.severity,
        category=args.category,
        supersedes=num,
    )
    block = "\n".join(skeleton) + "\n"

    if not patched.endswith("\n"):
        patched = patched + "\n"
    if not patched.endswith("\n\n"):
        patched = patched + "\n"
    patched = patched + block.lstrip("\n")

    if args.write:
        path.write_text(patched, encoding="utf-8")
        print(
            f"tombstoned DL-{num:03d} and appended DL-{new_num:03d} "
            f"(superseder) to {path}."
        )
        print(
            f"Next: fill the TODO markers in DL-{new_num:03d}, then run "
            f"`dls lint` to verify the handshake."
        )
        return 0

    print(f"=== dry-run — would mutate {path} ===")
    print(f"  DL-{num:03d} title rewrite:")
    print(f"    - old: {old_entry.title}")
    print(f"    + new: {tombstoned}")
    print(f"  Append DL-{new_num:03d} (superseder):")
    for line in skeleton:
        print("    " + line)
    print()
    print("(re-run with --write to apply)")
    return 0
