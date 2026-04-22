"""
stub.py — `dls stub` subcommand.

Emits a skeleton DL entry with explicit `TODO:` markers so a human can
fill it in. Default output is stdout; `--write` appends to the resolved
log file.

Philosophy: this is deliberately NOT a wizard. A wizard would prompt the
agent or human through each field and happily produce a valid entry
without understanding the bug. The skill's premise is that entry-writing
is the thinking. The CLI's job is to make the scaffolding cheap — file
layout, next-number resolution, timestamp, tag formatting — so the human
spends their attention on Symptom / Root Cause Context / Fix / Prevention
Rule.

Implementation notes:
  * Next DL number is computed from the existing log, not passed in.
  * Tags may be given with or without leading `#` (we normalise).
  * `--title` is required. Everything else is optional; omitted fields
    become TODO lines.
  * `--write` appends with a leading blank line and trailing newline so
    repeated invocations keep the file well-formed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from debug_log_parser import next_entry_number, parse_entries_from_path

from dls._paths import resolve_log_path
from dls._templates import build_entry_skeleton


DESCRIPTION = (
    "Append a skeleton DL entry with explicit TODO markers. Humans fill "
    "the TODOs. Default is dry-run to stdout; --write commits."
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--title",
        required=True,
        metavar="TEXT",
        help="One-line entry title (used as the `### DL-NNN — TEXT` header).",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="#Tag",
        help=(
            "Tag to include (repeatable; leading `#` optional). Supply at "
            "least one track tag and one semantic tag to pass `lint`."
        ),
    )
    parser.add_argument(
        "--severity",
        default=None,
        help=(
            "Severity value (e.g. 'Runtime Crash'). Omit to get a TODO "
            "placeholder."
        ),
    )
    parser.add_argument(
        "--environment",
        default=None,
        help="Environment line (SDK / framework / OS versions).",
    )
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "File touched by the bug (repeatable). Rendered as "
            "backticked path(s) in the File(s) field."
        ),
    )
    parser.add_argument(
        "--category",
        default=None,
        metavar="CATEGORY",
        help=(
            "Root Cause Category. Omit to default to 'Other', which is "
            "valid but should be replaced before commit."
        ),
    )
    parser.add_argument(
        "--number",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Force a specific DL number. Rarely used; we normally "
            "auto-detect the next free number."
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Append to the DEBUG_LOG.md (default: print to stdout).",
    )


def _normalise_tag(t: str) -> str:
    t = t.strip()
    return t if t.startswith("#") else f"#{t}"


def run(args: argparse.Namespace) -> int:
    path = resolve_log_path(args.log)
    entries = parse_entries_from_path(path)

    num = args.number if args.number is not None else next_entry_number(entries)
    if args.number is not None:
        existing = {e.num for e in entries}
        if num in existing:
            print(
                f"error: DL-{num:03d} already exists. Pick a different "
                f"--number or drop the flag to auto-detect.",
                file=sys.stderr,
            )
            return 2

    tags = [_normalise_tag(t) for t in args.tag] or None
    files = [f.strip() for f in args.file if f.strip()] or None

    skeleton = build_entry_skeleton(
        num=num,
        title=args.title,
        tags=tags,
        severity=args.severity,
        environment=args.environment,
        files=files,
        category=args.category,
    )

    block = "\n".join(skeleton) + "\n"

    if args.write:
        _append_to_log(path, block)
        print(f"appended DL-{num:03d} to {path}")
        print(
            "Next: fill the TODO markers, then run `dls lint` to verify."
        )
    else:
        sys.stdout.write(block)
        print(
            f"\n(dry-run — pass --write to append to {path})",
            file=sys.stderr,
        )
    return 0


def _append_to_log(path: Path, block: str) -> None:
    """Append `block` ensuring exactly one blank line separates it."""
    existing = path.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing = existing + "\n"
    if not existing.endswith("\n\n"):
        existing = existing + "\n"
    path.write_text(existing + block.lstrip("\n"), encoding="utf-8")
