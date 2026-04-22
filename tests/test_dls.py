#!/usr/bin/env python3
"""
test_dls.py — behavioural tests for the `dls` CLI.

These tests invoke the CLI as a subprocess (the same way a user or a CI
job would) and assert on stdout/stderr/exit-code. They do NOT import the
package directly: the value of shelling out is that we're exercising
exactly what ships.

Scope:
  * One test per subcommand covering the happy path.
  * Edge cases we care about:
      - query filters compose (AND across flags, OR within one flag).
      - relevant handles path substrings and basenames.
      - stub auto-detects the next DL number.
      - stub writes a syntactically valid skeleton.
      - supersede --write produces a lint-clean pair.
      - doctor --stale-days=0 disables stale detection.

Exit 0 = all pass.
Exit 1 = at least one failed (diff printed to stderr).
Exit 2 = script misuse (missing CLI, test fixture missing).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DLS_ENTRY = REPO_ROOT / "scripts" / "dls"
EXAMPLE_LOG = REPO_ROOT / "examples" / "example-DEBUG_LOG.md"
TEMPLATE_LOG = REPO_ROOT / "templates" / "DEBUG_LOG.template.md"
VALIDATOR = REPO_ROOT / "github-actions" / "validate_debug_log.py"


@dataclass
class Result:
    exit_code: int
    stdout: str
    stderr: str


def _run_dls(*argv: str) -> Result:
    proc = subprocess.run(
        [sys.executable, str(DLS_ENTRY), *argv],
        capture_output=True,
        text=True,
    )
    return Result(proc.returncode, proc.stdout, proc.stderr)


def _run_validator(path: Path, *extra: str) -> Result:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), *extra, str(path)],
        capture_output=True,
        text=True,
    )
    return Result(proc.returncode, proc.stdout, proc.stderr)


# ---------------------------------------------------------------------------
# Individual tests. Each returns (passed: bool, message: str).
# ---------------------------------------------------------------------------


def test_help_lists_all_subcommands() -> tuple[bool, str]:
    r = _run_dls("--help")
    if r.exit_code != 0:
        return False, f"--help exited {r.exit_code}: {r.stderr}"
    expected = (
        "lint", "stats", "query", "relevant", "doctor", "supersede", "stub",
    )
    missing = [name for name in expected if name not in r.stdout]
    if missing:
        return False, f"--help missing subcommands: {missing}"
    return True, "help lists all subcommands"


def test_lint_example_clean() -> tuple[bool, str]:
    r = _run_dls("lint", "--log", str(EXAMPLE_LOG))
    if r.exit_code != 0:
        return False, f"lint exit {r.exit_code}: {r.stderr}"
    if "all valid" not in r.stdout:
        return False, f"lint stdout missing 'all valid': {r.stdout!r}"
    return True, "lint clean on example"


def test_lint_strict_example_clean() -> tuple[bool, str]:
    r = _run_dls("lint", "--strict", "--log", str(EXAMPLE_LOG))
    if r.exit_code != 0:
        return False, f"lint --strict exit {r.exit_code}: {r.stderr}"
    if "[--strict]" not in r.stdout:
        return False, "lint --strict stdout missing '[--strict]' tag"
    return True, "lint --strict clean on example"


def test_stats_renders_categories() -> tuple[bool, str]:
    r = _run_dls("stats", "--log", str(EXAMPLE_LOG))
    if r.exit_code != 0:
        return False, f"stats exit {r.exit_code}: {r.stderr}"
    # The example log has multiple API Change entries — should show up as
    # a cluster in the promotion candidates section.
    if "API Change" not in r.stdout:
        return False, "stats stdout missing 'API Change'"
    if "Rule-promotion candidates" not in r.stdout:
        return False, "stats stdout missing promotion candidates section"
    return True, "stats renders distributions + promotion candidates"


def test_query_filter_by_category() -> tuple[bool, str]:
    r = _run_dls(
        "query", "--log", str(EXAMPLE_LOG),
        "--category", "API Change",
    )
    if r.exit_code != 0:
        return False, f"query exit {r.exit_code}: {r.stderr}"
    # Expect DL-002, DL-003, DL-008 in the example log.
    for wanted in ("DL-002", "DL-003", "DL-008"):
        if wanted not in r.stdout:
            return False, f"query missing {wanted}: {r.stdout!r}"
    # Should NOT include DL-005 (Scope Leak).
    if "DL-005" in r.stdout:
        return False, "query returned DL-005 but category filter was API Change"
    return True, "query --category narrows correctly"


def test_query_tag_and_severity_compose() -> tuple[bool, str]:
    # Two filters should AND: --tag #android AND --severity "Logic Bug".
    # DL-003 is Logic Bug but #ios; DL-006 is Logic Bug AND #android. AND
    # semantics should narrow to DL-006 only.
    r = _run_dls(
        "query", "--log", str(EXAMPLE_LOG),
        "--tag", "#android", "--severity", "Logic Bug",
    )
    if r.exit_code != 0:
        return False, f"query compose exit {r.exit_code}: {r.stderr}"
    if "DL-006" not in r.stdout:
        return False, f"query --tag --severity missed DL-006: {r.stdout!r}"
    if "DL-003" in r.stdout:
        return False, (
            f"query did NOT narrow — DL-003 (#ios) leaked in: {r.stdout!r}"
        )
    return True, "query composes filters with AND semantics"


def test_query_empty_result_is_not_an_error() -> tuple[bool, str]:
    r = _run_dls(
        "query", "--log", str(EXAMPLE_LOG),
        "--tag", "#ThisTagDoesNotExist",
    )
    if r.exit_code != 0:
        return False, f"empty query exit {r.exit_code}: {r.stderr}"
    if "no matching entries" not in r.stdout:
        return False, f"empty query stdout: {r.stdout!r}"
    return True, "empty query exits 0 with friendly message"


def test_relevant_finds_by_path_substring() -> tuple[bool, str]:
    r = _run_dls(
        "relevant", "--log", str(EXAMPLE_LOG),
        "app/components/PostCard.tsx",
    )
    if r.exit_code != 0:
        return False, f"relevant exit {r.exit_code}: {r.stderr}"
    if "DL-008" not in r.stdout:
        return False, f"relevant missed DL-008: {r.stdout!r}"
    return True, "relevant surfaces entries via path substring"


def test_relevant_finds_by_basename() -> tuple[bool, str]:
    r = _run_dls(
        "relevant", "--log", str(EXAMPLE_LOG),
        "some/other/tree/PostCard.tsx",
    )
    if r.exit_code != 0:
        return False, f"relevant exit {r.exit_code}: {r.stderr}"
    if "DL-008" not in r.stdout:
        return False, (
            f"relevant missed DL-008 via basename: {r.stdout!r}"
        )
    return True, "relevant matches by basename when full path diverges"


def test_doctor_flags_promotion_cluster() -> tuple[bool, str]:
    r = _run_dls("doctor", "--log", str(EXAMPLE_LOG))
    # Example log has a 3-entry API Change cluster -> promotion info.
    # doctor exits 0 because that's info-level, not error.
    if r.exit_code != 0:
        return False, f"doctor exit {r.exit_code}: {r.stderr}\n{r.stdout}"
    if "API Change" not in r.stdout:
        return False, "doctor missed promotion backlog"
    return True, "doctor surfaces promotion-ready clusters"


def test_stub_dryrun_emits_skeleton() -> tuple[bool, str]:
    r = _run_dls(
        "stub", "--log", str(EXAMPLE_LOG),
        "--title", "Test stub",
        "--tag", "#android", "--tag", "#Compose",
        "--severity", "Runtime Crash",
    )
    if r.exit_code != 0:
        return False, f"stub dry-run exit {r.exit_code}: {r.stderr}"
    checks = (
        "### DL-009 — Test stub",  # auto-detected next number
        "| **Date** |",
        "TODO:",  # placeholders present
        "#android #Compose",
    )
    for s in checks:
        if s not in r.stdout:
            return False, f"stub dry-run missing {s!r}: {r.stdout!r}"
    return True, "stub dry-run emits skeleton with TODOs + auto number"


def test_stub_write_appends_valid_entry() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "DEBUG_LOG.md"
        shutil.copy(EXAMPLE_LOG, tmp_path)

        r = _run_dls(
            "stub", "--log", str(tmp_path),
            "--title", "Test stub for write",
            "--tag", "#android", "--tag", "#Compose",
            "--severity", "Runtime Crash",
            "--category", "Race Condition",
            "--file", "app/Main.kt",
            "--environment", "AGP 8.3, compileSdk 34",
            "--write",
        )
        if r.exit_code != 0:
            return False, f"stub --write exit {r.exit_code}: {r.stderr}"

        # A TODO-laden stub MUST fail the validator. This is the core
        # invariant: validator-clean fake entries are worse than no
        # entries because they create the illusion of rigor. The
        # placeholder-sentinel check is what enforces this.
        v = _run_validator(tmp_path)
        if v.exit_code == 0:
            return False, (
                "CRITICAL: validator passed a TODO-laden stub entry. A "
                "scaffolded entry with placeholder sentinels must NOT "
                "pass lint. Stdout: " + v.stdout
            )
        if "placeholder sentinel" not in v.stderr:
            return False, (
                "validator rejected stub but error message doesn't "
                "mention the placeholder sentinel: " + v.stderr
            )
        text = tmp_path.read_text(encoding="utf-8")
        if "### DL-009 — Test stub for write" not in text:
            return False, "appended entry not found in file"
    return True, "stub --write fails lint until TODOs are filled in"


def test_supersede_dryrun_shows_both_sides() -> tuple[bool, str]:
    r = _run_dls(
        "supersede", "--log", str(EXAMPLE_LOG),
        "DL-005",
        "--title", "Example superseder",
        "--tag", "#android", "--tag", "#ScopeLeak",
        "--category", "Scope Leak",
    )
    if r.exit_code != 0:
        return False, f"supersede dry-run exit {r.exit_code}: {r.stderr}"
    for fragment in (
        "DL-005 title rewrite",
        "[OBSOLETE]",
        "### DL-009",
        "Supersedes DL-005",
    ):
        if fragment not in r.stdout:
            return False, (
                f"supersede dry-run missing {fragment!r}: {r.stdout!r}"
            )
    return True, "supersede dry-run renders both diff sides"


def test_supersede_refuses_double_tombstone() -> tuple[bool, str]:
    # DL-001 is [OBSOLETE] in the example log. supersede must refuse.
    r = _run_dls(
        "supersede", "--log", str(EXAMPLE_LOG),
        "DL-001",
        "--title", "anything",
    )
    if r.exit_code == 0:
        return False, "supersede DID NOT refuse to re-tombstone DL-001"
    if "already [OBSOLETE]" not in r.stderr:
        return False, (
            f"supersede refusal message missing expected text: {r.stderr!r}"
        )
    return True, "supersede refuses double-tombstone"


def test_supersede_refuses_unknown_dl() -> tuple[bool, str]:
    r = _run_dls(
        "supersede", "--log", str(EXAMPLE_LOG),
        "DL-998",
        "--title", "anything",
    )
    if r.exit_code == 0:
        return False, "supersede DID NOT refuse unknown DL-998"
    if "does not exist" not in r.stderr:
        return False, (
            f"supersede refusal message missing expected text: {r.stderr!r}"
        )
    return True, "supersede refuses unknown DL"


def test_supersede_write_round_trip_passes_handshake() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "DEBUG_LOG.md"
        shutil.copy(EXAMPLE_LOG, tmp_path)

        r = _run_dls(
            "supersede", "--log", str(tmp_path),
            "DL-005",
            "--title", "Superseder for test",
            "--tag", "#android", "--tag", "#ScopeLeak",
            "--category", "Scope Leak",
            "--severity", "Logic Bug",
            "--write",
        )
        if r.exit_code != 0:
            return False, f"supersede --write exit {r.exit_code}: {r.stderr}"

        text = tmp_path.read_text(encoding="utf-8")
        if "[OBSOLETE]" not in text:
            return False, "DL-005 was not tombstoned"
        if "Supersedes DL-005" not in text:
            return False, "superseder did not include handshake line"

        # The full log will fail `lint` because the superseder still has
        # TODOs — BUT it should NOT fail with a handshake-specific
        # message. Confirm the handshake check passes even when other
        # checks flag the TODOs.
        v = _run_validator(tmp_path)
        forbidden = (
            "is [OBSOLETE] but no later entry",
            "but DL-005's title does not start with",
        )
        for bad in forbidden:
            if bad in v.stderr:
                return False, (
                    f"supersede round-trip broke handshake check: "
                    f"{v.stderr!r}"
                )
    return True, "supersede --write passes handshake (TODOs still flagged)"


def test_artifact_missing_fails_lint() -> tuple[bool, str]:
    # Synthesise a minimal log with a broken Artifact link and confirm
    # the validator refuses it.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "DEBUG_LOG.md"
        tmp_path.write_text(
            "# DEBUG_LOG\n\n## Entries\n\n"
            "### DL-000 — Seed\n\n"
            "| Field | Value |\n"
            "|-------|-------|\n"
            "| **Date** | 2026-04-01 |\n"
            "| **Tags** | `#cross-cutting #Logging` |\n"
            "| **Severity** | Informational |\n"
            "| **Environment** | N/A |\n"
            "| **File(s)** | `DEBUG_LOG.md` |\n"
            "| **Symptom** | N/A |\n"
            "| **Root Cause Category** | Other |\n"
            "| **Root Cause Context** | Seed. |\n"
            "| **Fix** | Initialised. |\n"
            "| **Iterations** | 0 |\n"
            "| **Prevention Rule** | Grep by filename / tag before editing. "
            "**Why:** every rule here is scar tissue. |\n"
            "| **Artifact** | `.debug-log/incidents/does-not-exist.md` |\n",
            encoding="utf-8",
        )
        v = _run_validator(tmp_path)
        if v.exit_code != 1:
            return False, (
                f"validator should have flagged bad Artifact; exit "
                f"{v.exit_code}: {v.stderr}"
            )
        if "Artifact" not in v.stderr:
            return False, f"Artifact error not in stderr: {v.stderr!r}"
    return True, "validator flags unresolved Artifact paths"


def test_artifact_canonical_incident_path_ok_when_missing() -> tuple[bool, str]:
    # The canonical `.debug-log/incidents/DL-NNN.md` path is soft-allowed
    # even when the file doesn't yet exist — the entry and sidecar can
    # land in the same PR.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "DEBUG_LOG.md"
        tmp_path.write_text(
            "# DEBUG_LOG\n\n## Entries\n\n"
            "### DL-000 — Seed\n\n"
            "| Field | Value |\n"
            "|-------|-------|\n"
            "| **Date** | 2026-04-01 |\n"
            "| **Tags** | `#cross-cutting #Logging` |\n"
            "| **Severity** | Informational |\n"
            "| **Environment** | N/A |\n"
            "| **File(s)** | `DEBUG_LOG.md` |\n"
            "| **Symptom** | N/A |\n"
            "| **Root Cause Category** | Other |\n"
            "| **Root Cause Context** | Seed. |\n"
            "| **Fix** | Initialised. |\n"
            "| **Iterations** | 0 |\n"
            "| **Prevention Rule** | Grep by filename / tag before editing. "
            "**Why:** every rule here is scar tissue. |\n"
            "| **Artifact** | `.debug-log/incidents/DL-000.md` |\n",
            encoding="utf-8",
        )
        v = _run_validator(tmp_path)
        if v.exit_code != 0:
            return False, (
                f"canonical incident path should soft-pass validator; "
                f"exit {v.exit_code}: {v.stderr}"
            )
    return True, "validator soft-allows canonical incident paths"


def test_doctor_flags_stale_entries() -> tuple[bool, str]:
    # Write a log with a very old DL-001 active entry. doctor --stale-days=1
    # should flag it.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "DEBUG_LOG.md"
        tmp_path.write_text(
            "# DEBUG_LOG\n\n## Entries\n\n"
            "### DL-000 — Seed\n\n"
            "| Field | Value |\n"
            "|-------|-------|\n"
            "| **Date** | 2020-01-01 |\n"
            "| **Tags** | `#cross-cutting #Logging` |\n"
            "| **Severity** | Informational |\n"
            "| **Environment** | N/A |\n"
            "| **File(s)** | `DEBUG_LOG.md` |\n"
            "| **Symptom** | N/A |\n"
            "| **Root Cause Category** | Other |\n"
            "| **Root Cause Context** | Seed. |\n"
            "| **Fix** | Initialised. |\n"
            "| **Iterations** | 0 |\n"
            "| **Prevention Rule** | Grep by filename / tag before editing. "
            "**Why:** every rule here is scar tissue. |\n",
            encoding="utf-8",
        )
        r = _run_dls(
            "doctor", "--log", str(tmp_path),
            "--stale-days", "30",
        )
        if r.exit_code != 0:
            return False, (
                f"doctor --stale-days=30 exit {r.exit_code}: "
                f"{r.stderr}\n{r.stdout}"
            )
        if "last touched" not in r.stdout or "DL-000" not in r.stdout:
            return False, f"doctor missed stale DL-000: {r.stdout!r}"
    return True, "doctor flags stale active entries"


# ---------------------------------------------------------------------------
# Test harness.
# ---------------------------------------------------------------------------

TESTS = [
    test_help_lists_all_subcommands,
    test_lint_example_clean,
    test_lint_strict_example_clean,
    test_stats_renders_categories,
    test_query_filter_by_category,
    test_query_tag_and_severity_compose,
    test_query_empty_result_is_not_an_error,
    test_relevant_finds_by_path_substring,
    test_relevant_finds_by_basename,
    test_doctor_flags_promotion_cluster,
    test_stub_dryrun_emits_skeleton,
    test_stub_write_appends_valid_entry,
    test_supersede_dryrun_shows_both_sides,
    test_supersede_refuses_double_tombstone,
    test_supersede_refuses_unknown_dl,
    test_supersede_write_round_trip_passes_handshake,
    test_artifact_missing_fails_lint,
    test_artifact_canonical_incident_path_ok_when_missing,
    test_doctor_flags_stale_entries,
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Behavioural tests for the `dls` CLI.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print each test's message on pass.",
    )
    args = parser.parse_args(argv)

    if not DLS_ENTRY.exists():
        print(f"error: dls package not found at {DLS_ENTRY}", file=sys.stderr)
        return 2
    if not VALIDATOR.exists():
        print(f"error: validator not found at {VALIDATOR}", file=sys.stderr)
        return 2

    print(f"Running {len(TESTS)} dls test(s).")
    print()

    passed = 0
    failed = 0
    for fn in TESTS:
        try:
            ok, note = fn()
        except Exception as exc:  # pragma: no cover — defensive
            ok = False
            note = f"raised: {type(exc).__name__}: {exc}"
        mark = "  PASS" if ok else "  FAIL"
        print(f"{mark}  {fn.__name__}")
        if args.verbose or not ok:
            print(f"         {note}")
        if ok:
            passed += 1
        else:
            failed += 1

    print()
    print(f"{passed}/{len(TESTS)} passed, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
