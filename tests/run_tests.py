#!/usr/bin/env python3
"""
run_tests.py — fixture-based tests for the DEBUG_LOG v2.0 validator.

Each fixture in `fixtures/` is a complete DEBUG_LOG.md designed to exercise
exactly one check in the validator. The runner shells out to the validator
and asserts:

  1. The exit code matches `expected_exit`.
  2. For fixtures expected to fail (exit 1), stderr contains the
     `expected_fragment` — this is how we check that the validator failed
     for the *right* reason, not just that it failed.
  3. For fixtures expected to pass (exit 0), stderr is empty.

Usage:
  python3 tests/run_tests.py            # default mode
  python3 tests/run_tests.py --verbose  # print stderr for every fixture

Exit 0 = all fixtures produced the expected result.
Exit 1 = at least one mismatch (diff printed to stderr).
Exit 2 = script misuse (missing validator, missing fixtures dir).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "github-actions" / "validate_debug_log.py"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"


@dataclass(frozen=True)
class Case:
    fixture: str
    expected_exit: int
    # Substring that MUST appear in the validator's stderr when expected_exit
    # is non-zero. Leave empty for pass cases.
    expected_fragment: str = ""
    # Extra validator args (e.g., ["--strict"]).
    extra_args: tuple[str, ...] = ()


# Ordered for stable output. Each case documents *why* the expected behaviour
# is what it is — this doubles as a spec for the validator.
CASES: list[Case] = [
    # --- valid cases ------------------------------------------------------
    Case(
        fixture="valid_minimal.md",
        expected_exit=0,
        # A single DL-000 seed entry with the full 11 fields is a complete,
        # valid log. This is the shape `init.sh` writes.
    ),
    Case(
        fixture="valid_full.md",
        expected_exit=0,
        # DL-000 seed + a regular DL-001 active entry is the common shape.
    ),
    Case(
        fixture="valid_supersede.md",
        expected_exit=0,
        # The canonical lifecycle: DL-001 tombstoned, DL-002 supersedes it.
        # Both sides of the handshake are present.
    ),
    Case(
        fixture="html_commented_entry.md",
        expected_exit=0,
        # A DL-001 inside an HTML comment MUST NOT be counted. This is the
        # shape of the shipped template; the regression from before the
        # HTML-comment strip was "template DEBUG_LOG reports 2 entries".
    ),

    # --- structural failures ---------------------------------------------
    Case(
        fixture="orphan_obsolete.md",
        expected_exit=1,
        expected_fragment="is [OBSOLETE] but no later entry says `Supersedes",
        # Tombstone without a superseder must fail — docs promise this and
        # the v1 validator did not enforce it.
    ),
    Case(
        fixture="dangling_supersede.md",
        expected_exit=1,
        expected_fragment="Supersedes DL-999` but DL-999 does not exist",
        # `Supersedes DL-NNN` pointing at a nonexistent entry must fail.
    ),
    Case(
        fixture="wrong_target_supersede.md",
        expected_exit=1,
        expected_fragment="title does not start with `[OBSOLETE]`",
        # `Supersedes DL-NNN` pointing at an entry whose title is NOT
        # tombstoned must fail. This catches the "I wrote a supersede but
        # forgot to mark the old entry obsolete" mistake.
    ),
    Case(
        fixture="gap_in_sequence.md",
        expected_exit=1,
        expected_fragment="Gap in DL sequence. Missing: DL-002",
        # Contiguous sequence is rule #1. Missing DL-002 between DL-001 and
        # DL-003 must fail.
    ),

    # --- vocabulary failures ---------------------------------------------
    Case(
        fixture="bad_category.md",
        expected_exit=1,
        expected_fragment="Root Cause Category 'NotARealCategory' is not canonical",
        # 14 canonical categories. Arbitrary strings must fail.
    ),
    Case(
        fixture="bad_severity.md",
        expected_exit=1,
        expected_fragment="Severity 'Very Bad' contains invalid label(s)",
        # 12 total severities (8 core + 4 extended). Arbitrary strings must fail.
    ),
    Case(
        fixture="bad_iterations.md",
        expected_exit=1,
        expected_fragment="Iterations 'a few times' is not a non-negative integer",
        # Iterations is a count, not prose.
    ),

    # --- tag-discipline failures -----------------------------------------
    Case(
        fixture="too_many_track_tags.md",
        expected_exit=1,
        expected_fragment="track tag(s) (cap is 2)",
        # Taxonomy says 1-2. 3+ track tags must fail (regression from v1
        # where the validator had no upper bound).
    ),
    Case(
        fixture="no_track_tag.md",
        expected_exit=1,
        expected_fragment="is missing a track tag",
        # At least one track tag required.
    ),
    Case(
        fixture="no_semantic_tag.md",
        expected_exit=1,
        expected_fragment="has no semantic tag",
        # At least one semantic tag required beyond the track set.
    ),

    # --- rule-strength failures ------------------------------------------
    Case(
        fixture="short_rule.md",
        expected_exit=1,
        expected_fragment="Prevention Rule is",
        # "Be careful." is neither specific nor checkable nor carries why.
        # The validator catches both the short length and the missing Why:.
    ),
    Case(
        fixture="placeholder_sentinel.md",
        expected_exit=1,
        expected_fragment="placeholder sentinel",
        # A `dls stub --write` entry committed without being filled in is
        # the canonical "validator-clean fake entry" case. The sentinel
        # check must refuse it — a scaffolded entry masquerading as real
        # knowledge is worse than no entry at all.
    ),

    # --- strict mode -----------------------------------------------------
    Case(
        fixture="strict_unknown_tag.md",
        expected_exit=0,
        # Default mode accepts `#MadeUpTag` (open semantic vocabulary).
    ),
    Case(
        fixture="strict_unknown_tag.md",
        expected_exit=1,
        expected_fragment="not in taxonomy (#MadeUpTag)",
        extra_args=("--strict",),
        # --strict rejects tags that aren't in references/tag-taxonomy.md.
    ),
]


def run_case(case: Case, *, verbose: bool) -> tuple[bool, str]:
    """Run a single case, return (passed, diagnostic)."""
    fixture_path = FIXTURE_DIR / case.fixture
    if not fixture_path.is_file():
        return False, f"missing fixture: {fixture_path}"

    cmd = [sys.executable, str(VALIDATOR), *case.extra_args, str(fixture_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    problems: list[str] = []
    if proc.returncode != case.expected_exit:
        problems.append(
            f"expected exit {case.expected_exit}, got {proc.returncode}"
        )
    if case.expected_exit == 0 and proc.stderr.strip():
        problems.append(f"expected empty stderr, got: {proc.stderr.strip()}")
    if case.expected_exit != 0 and case.expected_fragment:
        if case.expected_fragment not in proc.stderr:
            problems.append(
                f"stderr missing expected fragment: "
                f"{case.expected_fragment!r}\n"
                f"stderr was:\n{proc.stderr.strip()}"
            )

    if problems:
        return False, "; ".join(problems)

    note = f" [args: {' '.join(case.extra_args)}]" if case.extra_args else ""
    if verbose:
        return True, f"exit {proc.returncode}{note}: {proc.stdout.strip() or proc.stderr.strip()}"
    return True, f"exit {proc.returncode}{note}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run DEBUG_LOG v2.0 validator fixture tests.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print each fixture's stdout/stderr on pass.",
    )
    args = parser.parse_args(argv)

    if not VALIDATOR.is_file():
        print(f"error: validator not found at {VALIDATOR}", file=sys.stderr)
        return 2
    if not FIXTURE_DIR.is_dir():
        print(f"error: fixtures dir not found at {FIXTURE_DIR}", file=sys.stderr)
        return 2

    passed = 0
    failed = 0
    print(f"Running {len(CASES)} fixture(s) against {VALIDATOR.name}")
    print()

    for case in CASES:
        ok, note = run_case(case, verbose=args.verbose)
        prefix = "  PASS" if ok else "  FAIL"
        arg_hint = f" [{' '.join(case.extra_args)}]" if case.extra_args else ""
        print(f"{prefix}  {case.fixture}{arg_hint}")
        if args.verbose or not ok:
            print(f"         {note}")
        if ok:
            passed += 1
        else:
            failed += 1

    print()
    print(f"{passed}/{len(CASES)} passed, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
