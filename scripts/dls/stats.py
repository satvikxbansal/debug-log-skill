"""
stats.py — `dls stats` subcommand.

The log is a knowledge graph, and the single most useful view of it is:
"what classes of bug does this project keep shipping?" This is that view.

Output sections:
  * Header — total / active / obsolete counts.
  * Root Cause Category distribution (active entries only).
  * Track tag distribution.
  * Top 10 semantic tags.
  * Severity distribution.
  * Iterations histogram + the entries with Iterations >= 5 (the
    "hallucination-loop" set).
  * Rule-promotion candidates — categories, tags, or files with >= N
    active entries. These are the clusters worth promoting to
    PREVENTION_RULES.md or a linter.

Exit 0 always (stats is read-only).
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from debug_log_parser import Entry, parse_entries_from_path
from debug_log_schema import ROOT_CAUSE_CATEGORIES, strip_markdown

from dls._format import aligned, count_bar, heading, hrule
from dls._paths import resolve_log_path


DESCRIPTION = (
    "Print frequency counts, distributions, and rule-promotion candidates. "
    "Read-only."
)

_DEFAULT_PROMOTE_THRESHOLD = 3


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--promote-threshold",
        type=int,
        default=_DEFAULT_PROMOTE_THRESHOLD,
        metavar="N",
        help=(
            f"Minimum active-entry count for a category / tag / file to "
            f"appear in the rule-promotion section (default "
            f"{_DEFAULT_PROMOTE_THRESHOLD})."
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="Max rows shown per distribution (default 10).",
    )


def _iterations_value(entry: Entry) -> int | None:
    """Parse Iterations as an int, tolerating `3 (actor race)` etc."""
    raw = strip_markdown(entry.get("Iterations"))
    m = re.match(r"^(\d+)", raw)
    return int(m.group(1)) if m else None


def _render_distribution(
    title: str,
    counter: Counter[str],
    *,
    top: int,
) -> list[str]:
    if not counter:
        return [heading(title), "  (no entries)", ""]
    max_count = max(counter.values())
    rows = counter.most_common(top)
    lines = [heading(title)]
    label_w = max(len(label) for label, _ in rows)
    for label, count in rows:
        bar = count_bar(count, max_count)
        lines.append(f"  {label:<{label_w}}  {count:>3}  {bar}")
    if len(counter) > top:
        lines.append(
            f"  … and {len(counter) - top} more (raise --top to show)."
        )
    lines.append("")
    return lines


def _rule_promotion_candidates(
    active: list[Entry], threshold: int, top: int
) -> list[str]:
    lines: list[str] = [
        heading(
            f"Rule-promotion candidates (≥ {threshold} active entries)"
        )
    ]

    def group_by(label: str, key_fn) -> list[tuple[str, int, list[str]]]:
        bucket: dict[str, list[Entry]] = {}
        for e in active:
            for k in key_fn(e):
                bucket.setdefault(k, []).append(e)
        hits = [
            (k, len(v), [entry.dl_id for entry in v])
            for k, v in bucket.items()
            if len(v) >= threshold
        ]
        hits.sort(key=lambda row: (-row[1], row[0]))
        return hits[:top]

    def cat_key(e: Entry) -> list[str]:
        raw = strip_markdown(e.get("Root Cause Category"))
        return [raw] if raw else []

    def tag_key(e: Entry) -> list[str]:
        return [t for t in e.semantic_tags]

    def file_key(e: Entry) -> list[str]:
        return e.files()

    any_hit = False
    for label, key_fn in (
        ("By Root Cause Category", cat_key),
        ("By semantic tag", tag_key),
        ("By File(s)", file_key),
    ):
        hits = group_by(label, key_fn)
        if not hits:
            continue
        any_hit = True
        lines.append(f"  {label}:")
        for k, n, ids in hits:
            ids_str = ", ".join(ids)
            lines.append(f"    {k:<30} ×{n}  ({ids_str})")
        lines.append("")

    if not any_hit:
        lines.append(
            f"  No cluster reached the {threshold}-entry threshold yet. "
            f"Keep writing."
        )
        lines.append("")

    return lines


def run(args: argparse.Namespace) -> int:
    path = resolve_log_path(args.log)
    entries = parse_entries_from_path(path)

    total = len(entries)
    active = [e for e in entries if e.active()]
    obsolete = [e for e in entries if e.is_obsolete]

    print(heading(f"DEBUG_LOG — {path}"))
    for line in aligned(
        [
            ("Total entries", total),
            ("Active", len(active)),
            ("Obsolete", len(obsolete)),
        ]
    ):
        print("  " + line)
    print()

    if not active:
        print(
            "No active entries yet. Run `dls stub` once you have your "
            "first bug to record."
        )
        return 0

    # Category distribution — enumerate all 14 categories so zeros show
    # up. Counting zeros is signal: "we have 0 Race Condition entries"
    # is itself a data point when you start logging one.
    cat_counter: Counter[str] = Counter()
    for cat in ROOT_CAUSE_CATEGORIES:
        cat_counter[cat] = 0
    for e in active:
        cat_counter[strip_markdown(e.get("Root Cause Category"))] += 1
    # Drop zero-rows from the display unless --top is very large.
    nonzero = Counter({k: v for k, v in cat_counter.items() if v > 0})
    for line in _render_distribution(
        "Root Cause Category (active)", nonzero, top=args.top
    ):
        print(line)

    track_counter: Counter[str] = Counter()
    for e in active:
        for t in e.track_tags:
            track_counter[t.lower()] += 1
    for line in _render_distribution(
        "Track tag (active)", track_counter, top=args.top
    ):
        print(line)

    sem_counter: Counter[str] = Counter()
    for e in active:
        for t in e.semantic_tags:
            sem_counter[t] += 1
    for line in _render_distribution(
        "Semantic tag (active, top)", sem_counter, top=args.top
    ):
        print(line)

    sev_counter: Counter[str] = Counter()
    for e in active:
        sev_counter[e.get("Severity") or "(missing)"] += 1
    for line in _render_distribution(
        "Severity (active)", sev_counter, top=args.top
    ):
        print(line)

    # Iteration histogram + loop-list.
    iter_counter: Counter[str] = Counter()
    loop_entries: list[Entry] = []
    for e in active:
        v = _iterations_value(e)
        if v is None:
            bucket = "?"
        elif v == 0:
            bucket = "0"
        elif v < 5:
            bucket = str(v)
        else:
            bucket = "5+"
            loop_entries.append(e)
        iter_counter[bucket] += 1

    # Order buckets naturally.
    ordered_buckets = Counter()
    for k in ("0", "1", "2", "3", "4", "5+", "?"):
        if iter_counter.get(k):
            ordered_buckets[k] = iter_counter[k]
    for line in _render_distribution(
        "Iterations (active)", ordered_buckets, top=10
    ):
        print(line)

    if loop_entries:
        print(heading("Hallucination-loop entries (Iterations ≥ 5)"))
        for e in loop_entries:
            print(f"  {e.dl_id} — {e.title}")
        print()

    for line in _rule_promotion_candidates(
        active, args.promote_threshold, args.top
    ):
        print(line)

    print(hrule())
    return 0
