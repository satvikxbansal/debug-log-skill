"""
query.py — `dls query` subcommand.

The pre-flight grep is the v2.0 invariant. This command is the
grep — but typed. Instead of `grep '#Compose' DEBUG_LOG.md` (which misses
entries where #Compose sits in the middle of a tag list) we parse entries
first, then filter.

Design choices:
  * AND semantics between filters (--tag A --category B = both must hold).
  * OR semantics within a repeated flag (--tag A --tag B = either).
  * Default output is one entry per line. `--full` prints entry bodies.
  * Obsolete entries are filtered out by default. `--include-obsolete`
    surfaces them too — rare, but useful when you want to know WHY a rule
    was retired.

Exit code 0 always (query is read-only). Empty result sets print a
one-liner so agents piping to grep don't mistake an empty stdout for an
error.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable

from debug_log_parser import Entry, parse_entries_from_path
from debug_log_schema import strip_markdown

from dls._format import heading, hrule
from dls._paths import resolve_log_path


DESCRIPTION = (
    "Filter entries by tag / category / severity / file / id. AND "
    "semantics between flags, OR within a repeated flag."
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="#Tag",
        help=(
            "Match entries whose Tags contain this tag (repeatable; OR "
            "between repeats). Matched case-insensitively, with or without "
            "the leading `#`."
        ),
    )
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        metavar="CATEGORY",
        help=(
            "Match entries whose Root Cause Category equals this (repeatable; "
            "OR between repeats)."
        ),
    )
    parser.add_argument(
        "--severity",
        action="append",
        default=[],
        metavar="SEVERITY",
        help="Match by Severity (repeatable; OR between repeats).",
    )
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Match entries where any File(s) entry contains this substring "
            "(repeatable; OR between repeats). Substring match, not glob."
        ),
    )
    parser.add_argument(
        "--id",
        action="append",
        default=[],
        metavar="DL-NNN",
        help="Match by DL id (repeatable).",
    )
    parser.add_argument(
        "--text",
        action="append",
        default=[],
        metavar="SUBSTRING",
        help=(
            "Full-text match: substring appears anywhere in the entry body "
            "(case-insensitive)."
        ),
    )
    parser.add_argument(
        "--include-obsolete",
        action="store_true",
        help=(
            "Include [OBSOLETE] entries in the result. Off by default — "
            "active pre-flight grep doesn't want tombstones."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print each matching entry's full body, not just a one-liner.",
    )


def _norm_tag(t: str) -> str:
    t = t.strip().lower()
    return t if t.startswith("#") else f"#{t}"


def _build_filter(args: argparse.Namespace) -> Callable[[Entry], bool]:
    tag_targets = {_norm_tag(t) for t in args.tag}
    category_targets = {t.strip() for t in args.category}
    severity_targets = {t.strip() for t in args.severity}
    file_targets = [t.strip() for t in args.file]
    id_targets = {t.strip().upper() for t in args.id}
    text_targets = [t.lower() for t in args.text]

    def matches(entry: Entry) -> bool:
        if not args.include_obsolete and entry.is_obsolete:
            return False
        if tag_targets:
            entry_tags = {t.lower() for t in entry.raw_tags}
            if tag_targets.isdisjoint(entry_tags):
                return False
        if category_targets:
            cat = strip_markdown(entry.get("Root Cause Category"))
            if cat not in category_targets:
                return False
        if severity_targets:
            sev = entry.get("Severity")
            # Severity may be a comma/slash list — match any token.
            sev_tokens = {t.strip() for t in sev.replace("/", ",").split(",")}
            if not (severity_targets & sev_tokens):
                return False
        if file_targets:
            files = entry.files()
            hit = any(
                any(target in f for f in files) for target in file_targets
            )
            if not hit:
                return False
        if id_targets:
            if entry.dl_id.upper() not in id_targets:
                return False
        if text_targets:
            body_joined = "\n".join(entry.body).lower()
            hit = any(t in body_joined for t in text_targets)
            if not hit:
                return False
        return True

    return matches


def _render_one_liner(entry: Entry) -> str:
    cat = strip_markdown(entry.get("Root Cause Category"))
    tags = " ".join(entry.raw_tags)
    obs = " [OBSOLETE]" if entry.is_obsolete else ""
    return f"{entry.dl_id}{obs}  {cat:<22}  {tags}  — {entry.title}"


def _render_full(entry: Entry) -> list[str]:
    lines = [heading(f"{entry.dl_id} — {entry.title}"), ""]
    lines.extend(entry.body)
    lines.append("")
    return lines


def run(args: argparse.Namespace) -> int:
    path = resolve_log_path(args.log)
    entries = parse_entries_from_path(path)
    matches = _build_filter(args)
    hits = [e for e in entries if matches(e)]

    if not hits:
        print(
            "(no matching entries — either your filters are too narrow or "
            "this class of bug hasn't been logged yet)"
        )
        return 0

    if args.full:
        for i, entry in enumerate(hits):
            if i > 0:
                print(hrule())
            for line in _render_full(entry):
                print(line)
    else:
        for entry in hits:
            print(_render_one_liner(entry))

    return 0
