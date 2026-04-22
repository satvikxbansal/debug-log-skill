"""
relevant.py — `dls relevant <path> [<path> ...]` (Phase 4 prep).

Phase 4 of the roadmap is retrieval intelligence — feeding the agent the
DL entries most likely to matter *right now*. This subcommand is the
simplest useful primitive:

    dls relevant src/components/checkout/index.tsx

returns every entry whose `File(s)` field contains a matching substring
against any of the given paths. Later phases can:

  * take `--diff` and parse a unified diff to extract changed paths;
  * take `--stack-trace` and extract frame paths;
  * weight matches by recency, iterations count, and tag overlap;
  * layer embedding-based retrieval on top.

The surface is deliberately small: one positional (N paths) and one
output shape (one entry per line, same as `dls query`'s one-liner). The
point is that an agent about to edit a file can pipe its path into this
and get the lessons that apply, with zero ceremony.

File matching is **substring on the File(s) field**. That's intentional:
file paths in DL entries are often partial ("app/src/main/.../Service.kt")
and the caller usually passes a full repo-relative path. Substring lets
them meet in the middle.
"""
from __future__ import annotations

import argparse
import os

from debug_log_parser import Entry, parse_entries_from_path
from debug_log_schema import strip_markdown

from dls._paths import resolve_log_path


DESCRIPTION = (
    "Surface DL entries that touch any of the given file paths. The Phase "
    "4 retrieval primitive — run it before editing to load the relevant "
    "rules."
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "paths",
        nargs="+",
        metavar="PATH",
        help=(
            "One or more file paths (or path fragments). Substring match "
            "against the File(s) field."
        ),
    )
    parser.add_argument(
        "--include-obsolete",
        action="store_true",
        help="Include [OBSOLETE] entries in the result.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print full entry bodies instead of one-liners.",
    )


def _matches(entry: Entry, targets: list[str]) -> bool:
    files = entry.files()
    if not files:
        return False
    basenames = {os.path.basename(f) for f in files}
    for target in targets:
        target_base = os.path.basename(target)
        for f in files:
            if target in f or f in target:
                return True
        if target_base in basenames:
            return True
    return False


def run(args: argparse.Namespace) -> int:
    path = resolve_log_path(args.log)
    entries = parse_entries_from_path(path)
    targets = [t.strip() for t in args.paths if t.strip()]

    hits: list[Entry] = []
    for entry in entries:
        if entry.is_obsolete and not args.include_obsolete:
            continue
        if _matches(entry, targets):
            hits.append(entry)

    if not hits:
        print(
            "(no DL entries touch those paths — either this code path is "
            "untouched by prior bugs or the paths need to be broadened)"
        )
        return 0

    if args.full:
        from dls.query import _render_full  # reuse the formatter
        for i, entry in enumerate(hits):
            if i > 0:
                print("-" * 60)
            for line in _render_full(entry):
                print(line)
    else:
        for entry in hits:
            cat = strip_markdown(entry.get("Root Cause Category"))
            obs = " [OBSOLETE]" if entry.is_obsolete else ""
            print(
                f"{entry.dl_id}{obs}  {cat:<22}  — {entry.title}"
            )
    return 0
