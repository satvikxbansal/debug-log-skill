"""
doctor.py — `dls doctor` subcommand.

`lint` tells you whether the log is structurally valid. `doctor` tells you
whether it is *healthy*. These are different questions:

  * A perfectly valid log can still be stale — 60% of active entries
    dated >12 months ago in a fast-moving codebase is a smell.
  * A perfectly valid log can still have orphaned Artifact links — the
    sidecar file may have been renamed or deleted.
  * A perfectly valid log can still have Iterations ≥ 5 entries whose
    Root Cause Context doesn't mention the hallucination loop — the
    protocol asks for a reflection there, and doctor flags the ones
    that dodged it.
  * A perfectly valid log can still have promotion-ready clusters that
    never made it into PREVENTION_RULES.md.

doctor's output is a *list of findings*, each one-line. Exit code 1 if
there are any findings of severity "error"; exit 0 otherwise (warnings
never block CI — they're nudges).
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from debug_log_parser import Entry, parse_entries_from_path
from debug_log_schema import (
    INCIDENT_DIR,
    strip_markdown,
)

from dls._format import heading, hrule
from dls._paths import repo_root_for_log, resolve_log_path


DESCRIPTION = (
    "Health checks beyond `lint`: stale rules, Artifact-link resolution, "
    "missed reflection on high-iteration entries, rule-promotion backlog."
)

_DEFAULT_STALE_DAYS = 365  # "stale" = active & last-touched > 1 year ago
_DEFAULT_PROMOTION_THRESHOLD = 3


@dataclass(frozen=True)
class Finding:
    severity: str  # "error" | "warning" | "info"
    message: str

    def render(self) -> str:
        prefix = {
            "error": "[error]  ",
            "warning": "[warn]   ",
            "info": "[info]   ",
        }[self.severity]
        return f"{prefix}{self.message}"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--stale-days",
        type=int,
        default=_DEFAULT_STALE_DAYS,
        metavar="N",
        help=(
            f"Flag active entries older than N days (default "
            f"{_DEFAULT_STALE_DAYS}). Set 0 to disable."
        ),
    )
    parser.add_argument(
        "--promote-threshold",
        type=int,
        default=_DEFAULT_PROMOTION_THRESHOLD,
        metavar="N",
        help=(
            f"Flag clusters of ≥ N active entries sharing a category or "
            f"tag (default {_DEFAULT_PROMOTION_THRESHOLD})."
        ),
    )


def _parse_date(entry: Entry) -> date | None:
    raw = entry.get("Date").split("<!--")[0].strip()
    if not raw or raw == "YYYY-MM-DD":
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _iterations_value(entry: Entry) -> int | None:
    raw = strip_markdown(entry.get("Iterations"))
    m = re.match(r"^(\d+)", raw)
    return int(m.group(1)) if m else None


def _artifact_path(entry: Entry) -> str | None:
    raw = strip_markdown(entry.get("Artifact"))
    if not raw:
        return None
    m = re.search(r"\(([^)]+)\)", raw)  # markdown link
    return (m.group(1) if m else raw).strip() or None


def _check_artifact_links(
    entries: list[Entry], repo_root: Path
) -> list[Finding]:
    findings: list[Finding] = []
    for entry in entries:
        path = _artifact_path(entry)
        if path is None:
            continue
        resolved = (repo_root / path).resolve()
        canonical = f"{INCIDENT_DIR}/DL-{entry.num:03d}.md"
        if resolved.exists():
            continue
        if path == canonical:
            findings.append(
                Finding(
                    "warning",
                    f"{entry.dl_id}: Artifact points at canonical "
                    f"incident path `{canonical}` but that file doesn't "
                    f"exist yet. Create it, or drop the Artifact field.",
                )
            )
        else:
            findings.append(
                Finding(
                    "error",
                    f"{entry.dl_id}: Artifact '{path}' does not resolve "
                    f"(relative to {repo_root}). Fix the path or remove "
                    f"the field.",
                )
            )
    return findings


def _check_stale(
    entries: list[Entry], stale_days: int, today: date | None = None
) -> list[Finding]:
    if stale_days <= 0:
        return []
    today = today or date.today()
    findings: list[Finding] = []
    for entry in entries:
        if entry.is_obsolete:
            continue
        d = _parse_date(entry)
        if d is None:
            continue
        age = (today - d).days
        if age > stale_days:
            findings.append(
                Finding(
                    "info",
                    f"{entry.dl_id}: active, last touched {age} days ago "
                    f"(>{stale_days}). Still true? Consider superseding "
                    f"or adding an Artifact note.",
                )
            )
    return findings


_LOOP_HINT_WORDS = (
    "iteration", "iterations", "retry", "retries", "loop", "looped",
    "stuck", "hallucin", "reflection",
)


def _check_loop_reflection(entries: list[Entry]) -> list[Finding]:
    findings: list[Finding] = []
    for entry in entries:
        it = _iterations_value(entry)
        if it is None or it < 5:
            continue
        context = entry.get("Root Cause Context").lower()
        if not any(word in context for word in _LOOP_HINT_WORDS):
            findings.append(
                Finding(
                    "warning",
                    f"{entry.dl_id}: Iterations = {it} but Root Cause "
                    f"Context does not mention the loop/hallucination. The "
                    f"protocol asks for a 1-2 sentence reflection on "
                    f"which assumption kept failing.",
                )
            )
    return findings


def _check_promotion_backlog(
    entries: list[Entry], threshold: int
) -> list[Finding]:
    findings: list[Finding] = []
    active = [e for e in entries if e.active()]

    by_cat: dict[str, list[Entry]] = {}
    for e in active:
        cat = strip_markdown(e.get("Root Cause Category"))
        if cat:
            by_cat.setdefault(cat, []).append(e)

    for cat, es in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        if len(es) < threshold:
            continue
        ids = ", ".join(sorted(e.dl_id for e in es)[:5])
        if len(es) > 5:
            ids += f", … (+{len(es) - 5} more)"
        findings.append(
            Finding(
                "info",
                f"Category '{cat}' has {len(es)} active entries "
                f"({ids}). Consider promoting a cross-entry rule to "
                f"PREVENTION_RULES.md.",
            )
        )

    return findings


def run(args: argparse.Namespace) -> int:
    path = resolve_log_path(args.log)
    repo_root = repo_root_for_log(path)
    entries = parse_entries_from_path(path)

    print(heading(f"doctor — {path}"))

    if not entries:
        print("  No entries yet — the log is empty. Nothing to check.")
        return 0

    findings: list[Finding] = []
    findings.extend(_check_artifact_links(entries, repo_root))
    findings.extend(_check_stale(entries, args.stale_days))
    findings.extend(_check_loop_reflection(entries))
    findings.extend(_check_promotion_backlog(entries, args.promote_threshold))

    if not findings:
        print("  All checks passed. Log is valid and healthy.")
        return 0

    err_count = sum(1 for f in findings if f.severity == "error")
    warn_count = sum(1 for f in findings if f.severity == "warning")
    info_count = sum(1 for f in findings if f.severity == "info")

    for f in findings:
        print("  " + f.render())
    print()
    print(hrule())
    print(
        f"  {err_count} error(s), {warn_count} warning(s), {info_count} "
        f"info. doctor exits 1 iff there are errors."
    )
    return 1 if err_count else 0
