"""
debug_log_schema.py — single source of truth for the DEBUG_LOG v2.0 contract.

Anything that validates, generates, or mutates a DEBUG_LOG.md entry imports
from this module. Drift used to live in three places (the validator, the
SKILL.md template, the docs); this module collapses it into one.

When you change a constant here, grep the repo for stringly-typed duplicates
and update them — the fixture test suite (`tests/run_tests.py`) also
cross-checks that a handful of invariants hold.

No third-party dependencies — this file is stdlib-only so CI environments
don't need a `pip install` step.
"""
from __future__ import annotations

import re
from typing import Final

# ----------------------------------------------------------------------------
# Version marker — bumped when the entry contract (field set / vocabularies)
# changes in a way the validator needs to distinguish.
# ----------------------------------------------------------------------------
SCHEMA_VERSION: Final[str] = "2.0"

# ----------------------------------------------------------------------------
# Required fields (v2.0). Order matters for the template; the validator uses
# the set form.
# ----------------------------------------------------------------------------
REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "Date",
    "Tags",
    "Severity",
    "Environment",
    "File(s)",
    "Symptom",
    "Root Cause Category",
    "Root Cause Context",
    "Fix",
    "Iterations",
    "Prevention Rule",
)
REQUIRED_FIELDS_SET: Final[frozenset[str]] = frozenset(REQUIRED_FIELDS)

# ----------------------------------------------------------------------------
# Optional fields (v2.1).
#
# These do NOT appear in every entry but are recognised + validated when they
# do. `Artifact` is the Phase 6 hook: when an investigation produced a
# companion file (under `.debug-log/incidents/DL-NNN.md` by convention, or any
# other path), the entry can point at it. The validator and `dls doctor`
# check the path resolves.
#
# Keep this set small — the cost of a new optional field is paid by every
# reader who now has to know what it means.
# ----------------------------------------------------------------------------
OPTIONAL_FIELDS: Final[tuple[str, ...]] = (
    "Artifact",
)
OPTIONAL_FIELDS_SET: Final[frozenset[str]] = frozenset(OPTIONAL_FIELDS)

# ----------------------------------------------------------------------------
# Incident sidecar convention (Phase 6).
#
# Deep-dive investigations live in per-incident markdown files under this
# directory, named after the DL number. We keep this as a constant so the
# CLI's `dls stub` and `dls doctor` commands can agree on the path without
# users having to pass it explicitly.
# ----------------------------------------------------------------------------
INCIDENT_DIR: Final[str] = ".debug-log/incidents"


def incident_path_for(num: int) -> str:
    """Canonical sidecar-file path for DL-NNN, relative to repo root."""
    return f"{INCIDENT_DIR}/DL-{num:03d}.md"

# ----------------------------------------------------------------------------
# Severity vocabulary.
#
# The SKILL.md entry-template cheat-sheet lists the eight "core" severities
# that cover ~95% of entries. The validator additionally accepts four
# "extended" severities that come up in practice (seed rows, non-crash
# warnings, UX regressions, security-only fixes). Docs in SKILL.md and the
# editor-integration samples show the core list with a footnote pointing at
# the extended set so the cheat-sheet stays readable.
# ----------------------------------------------------------------------------
SEVERITIES_CORE: Final[tuple[str, ...]] = (
    "Build Error",
    "Runtime Crash",
    "ANR",
    "Logic Bug",
    "Flaky Test",
    "Warning-as-Error",
    "Perf Regression",
    "Incident",
)

SEVERITIES_EXTENDED: Final[tuple[str, ...]] = (
    "Informational",       # seed entries (DL-000) and non-bug annotations
    "Runtime Warning",     # warnings that surfaced a latent bug
    "UX Regression",       # visible but not a crash
    "Security",            # security-motivated fix without a crash
)

VALID_SEVERITIES: Final[frozenset[str]] = frozenset(
    SEVERITIES_CORE + SEVERITIES_EXTENDED
)

# ----------------------------------------------------------------------------
# Root Cause Categories — closed vocabulary. The free-text `Root Cause
# Context` field carries the nuance. Adding a category is a deliberate,
# log-wide change; deletion is disallowed (it breaks historical counts).
# ----------------------------------------------------------------------------
ROOT_CAUSE_CATEGORIES: Final[tuple[str, ...]] = (
    "API Change",
    "API Deprecation",
    "Race Condition",
    "Scope Leak",
    "Main Thread Block",
    "Hydration Mismatch",
    "Null or Unchecked Access",
    "Type Coercion",
    "Off-By-One",
    "Syntax Error",
    "Config or Build",
    "Test Infrastructure",
    "LLM Hallucination or Assumption",
    "Other",
)
VALID_ROOT_CAUSE_CATEGORIES: Final[frozenset[str]] = frozenset(ROOT_CAUSE_CATEGORIES)

# ----------------------------------------------------------------------------
# Tags.
#
# Track tags anchor an entry to a stack. Every entry needs between
# MIN_TRACK_TAGS and MAX_TRACK_TAGS of them — "exactly one or two".
# Semantic tags classify the subject matter; every entry needs at least
# MIN_SEMANTIC_TAGS of them.
#
# The SEMANTIC_TAGS_TAXONOMY set is the catalog from
# `references/tag-taxonomy.md`. The default validator accepts any
# syntactically-valid tag outside the track set as a semantic tag; passing
# `--strict` requires semantic tags to come from this catalog.
# ----------------------------------------------------------------------------
TRACK_TAGS: Final[tuple[str, ...]] = (
    "#web",
    "#ios",
    "#android",
    "#macos",
    "#kotlin",
    "#swift",
    "#cross-cutting",
)
VALID_TRACK_TAGS: Final[frozenset[str]] = frozenset(TRACK_TAGS)
VALID_TRACK_TAGS_LOWER: Final[frozenset[str]] = frozenset(t.lower() for t in TRACK_TAGS)

MIN_TRACK_TAGS: Final[int] = 1
MAX_TRACK_TAGS: Final[int] = 2
MIN_SEMANTIC_TAGS: Final[int] = 1

SEMANTIC_TAGS_TAXONOMY: Final[frozenset[str]] = frozenset({
    # UI & rendering
    "#UI", "#Layout", "#Rendering", "#Animation", "#A11y", "#Focus",
    "#KeyboardInput", "#Gestures", "#Theme", "#DarkMode",
    "#DynamicType", "#RTL",
    # Framework-specific
    "#Compose", "#SwiftUI", "#UIKit", "#AppKit", "#React", "#NextJS",
    "#RSC", "#Hydration", "#SSR", "#ViewModel", "#LiveData",
    "#StateFlow", "#SharedFlow", "#Observable",
    # Concurrency & lifecycle
    "#Coroutines", "#Threading", "#MainActor", "#Sendable", "#AsyncAwait",
    "#Combine", "#RxJava", "#Lifecycle", "#ScopeLeak", "#Cancellation",
    "#Reentrancy",
    # Data & storage
    "#Room", "#CoreData", "#Realm", "#Firestore", "#SQLite", "#Cache",
    "#Serialization", "#JSON", "#Codable", "#Migration", "#DataRace",
    # Network & I/O
    "#Network", "#HTTP", "#URLSession", "#Fetch", "#Retry", "#Idempotency",
    "#CORS", "#CSP", "#WebSocket", "#Offline", "#Auth", "#OAuth", "#Token",
    # Navigation
    "#Navigation", "#DeepLink", "#Routing", "#BackStack",
    # Platform & permissions
    "#Permissions", "#TCC", "#Entitlements", "#Sandbox",
    "#ForegroundService", "#Notifications", "#Background", "#Overlay",
    "#FlagSecure", "#Screenshot", "#ScreenRecording", "#Accessibility",
    "#InputMonitoring",
    # Build, tooling & packaging
    "#Build", "#Gradle", "#Xcode", "#SwiftPM", "#CocoaPods", "#Vite",
    "#Webpack", "#Bundler", "#Lint", "#TypeCheck", "#CI", "#Release",
    "#Notarisation", "#Signing", "#ProGuard", "#R8",
    # Testing
    "#Test", "#FlakyTest", "#UnitTest", "#UITest", "#SnapshotTest",
    "#E2E", "#Playwright", "#XCTest", "#Espresso",
    # Perf & profiling
    "#Perf", "#Memory", "#Leak", "#Startup", "#JankFrame", "#Battery",
    # Security
    "#Security", "#Secrets", "#CVE", "#PII",
    # Observability
    "#Logging", "#Telemetry", "#Crashlytics", "#Analytics",
    # Agent & LLM
    "#LLM", "#Agent", "#Hallucination", "#Grounding", "#Prompt", "#ToolUse",
    # Also allow #cross-cutting as a "semantic" tag — some entries use it
    # twice (once as the sole track tag, once semantically) and we don't
    # want the validator to reject that shape. Track-dedup is handled
    # elsewhere.
    "#cross-cutting",
})
SEMANTIC_TAGS_TAXONOMY_LOWER: Final[frozenset[str]] = frozenset(
    t.lower() for t in SEMANTIC_TAGS_TAXONOMY
)

# ----------------------------------------------------------------------------
# Prevention Rule constraints.
#
# The "Why:" marker is the one mechanical signal that a rule carries
# justification. Short rules (under MIN_RULE_LEN chars) are almost always
# bumper-sticker rules that fail the "specific / checkable" bar.
# ----------------------------------------------------------------------------
MIN_RULE_LEN: Final[int] = 40
WHY_MARKERS: Final[tuple[str, ...]] = ("**Why:**", "Why:", "why:")

# ----------------------------------------------------------------------------
# Regex patterns.
# ----------------------------------------------------------------------------
# `### DL-NNN — Title` (em-dash or hyphen, 3+ digits, optional [OBSOLETE]).
ENTRY_HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^###\s+DL-(\d{3,})\s+[\u2014\u2013\u002D-]\s+(.+?)\s*$"
)

# Markdown table row: `| **Field** | value |`.
TABLE_ROW_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*(.+?)\s*\|\s*$"
)

# Single `#Tag` token. Track tags use lowercase; semantic tags typically
# use PascalCase. Both shapes fit this regex.
TAG_RE: Final[re.Pattern[str]] = re.compile(r"#[A-Za-z][A-Za-z0-9_-]*")

# HTML comment — non-greedy, DOTALL so it spans newlines.
HTML_COMMENT_RE: Final[re.Pattern[str]] = re.compile(r"<!--.*?-->", re.DOTALL)

# `Supersedes DL-NNN` reference — matches at the start of a body line, and
# anywhere in prose.
SUPERSEDES_RE: Final[re.Pattern[str]] = re.compile(r"Supersedes\s+DL-(\d{3,})")

# Obsolete tombstone prefix.
OBSOLETE_PREFIX: Final[str] = "[OBSOLETE]"


# ----------------------------------------------------------------------------
# Helpers.
# ----------------------------------------------------------------------------
def strip_html_comments(text: str) -> str:
    """Remove HTML comments so example / commented entries don't parse.

    The template ships with a commented DL-001 example. Without this strip,
    the entry-heading regex inside the comment gets matched and the
    validator reports two entries in a freshly-initialised log.
    """
    return HTML_COMMENT_RE.sub("", text)


def is_obsolete(title: str) -> bool:
    """True if the entry title starts with `[OBSOLETE]` (case-insensitive)."""
    return title.strip().upper().startswith(OBSOLETE_PREFIX.upper())


def strip_markdown(value: str) -> str:
    """Remove backticks and common markdown ornamentation for comparison."""
    return value.replace("`", "").strip()


def partition_tags(tags: list[str]) -> tuple[list[str], list[str]]:
    """Split a tag list into (track_tags, semantic_tags).

    Matching is case-insensitive — the taxonomy uses lowercase for track
    tags but authors sometimes capitalise them.
    """
    track: list[str] = []
    semantic: list[str] = []
    for t in tags:
        if t.lower() in VALID_TRACK_TAGS_LOWER:
            track.append(t)
        else:
            semantic.append(t)
    return track, semantic


__all__ = [
    "SCHEMA_VERSION",
    "REQUIRED_FIELDS",
    "REQUIRED_FIELDS_SET",
    "OPTIONAL_FIELDS",
    "OPTIONAL_FIELDS_SET",
    "INCIDENT_DIR",
    "incident_path_for",
    "SEVERITIES_CORE",
    "SEVERITIES_EXTENDED",
    "VALID_SEVERITIES",
    "ROOT_CAUSE_CATEGORIES",
    "VALID_ROOT_CAUSE_CATEGORIES",
    "TRACK_TAGS",
    "VALID_TRACK_TAGS",
    "VALID_TRACK_TAGS_LOWER",
    "MIN_TRACK_TAGS",
    "MAX_TRACK_TAGS",
    "MIN_SEMANTIC_TAGS",
    "SEMANTIC_TAGS_TAXONOMY",
    "SEMANTIC_TAGS_TAXONOMY_LOWER",
    "MIN_RULE_LEN",
    "WHY_MARKERS",
    "ENTRY_HEADING_RE",
    "TABLE_ROW_RE",
    "TAG_RE",
    "HTML_COMMENT_RE",
    "SUPERSEDES_RE",
    "OBSOLETE_PREFIX",
    "strip_html_comments",
    "is_obsolete",
    "strip_markdown",
    "partition_tags",
]
