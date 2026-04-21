# Changelog

All notable changes to `debug-log-skill` are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers follow [SemVer](https://semver.org/).

## [1.1.0] — 2026-04-21

Same-day follow-up: packaging, integrations, and scaffolding that make the skill easier to adopt.

### Added

- `CONTRIBUTING.md` — entry-format guide, strong/weak prevention rule rubric, review criteria, new-track instructions.
- `scripts/init.sh` — one-shot initialiser. Copies `DEBUG_LOG.md` and `PREVENTION_RULES.md` into a target project and drops a stub `CLAUDE.md` if absent. Never overwrites.
- `editor-integrations/` — sample rule / config files for popular LLM editors:
  - `CLAUDE.md` (Claude Code, Claude Desktop, Cowork).
  - `AGENTS.md` (Aider, Codex CLI, OpenAI Agents SDK, any AGENTS.md-aware harness).
  - `cursor/rules/debug-log.mdc` (Cursor, with proper frontmatter: `description`, `globs`, `alwaysApply`).
  - `README.md` table mapping each tool to its sample file.
- `github-actions/validate-debug-log.yml` + `validate_debug_log.py` — GitHub Actions workflow that validates DEBUG_LOG format on every PR: sequence integrity (no gaps, no duplicates), required-field completeness, date format, severity/track label correctness, and "Why:" marker on every prevention rule.
- Per-language `PREVENTION_RULES.<track>.template.md` starters for web, ios, android, macos, kotlin, swift.
- `references/pre-mortem-workflow.md` — the four-phase pre-mortem workflow extracted from SKILL.md and expanded with worked examples, LLM-specific guidance, and common-objection rebuttals.
- README badges (MIT, Claude Code, Cursor, Aider, CI) and a one-line `curl | bash` install snippet.
- `.gitignore` with OS, editor, and scratch-folder exclusions.

### Changed

- `SKILL.md` slimmed from ~176 lines to ~120. Keeps triggering description, the four rules, track selection, entry template, prevention-rule guidance, and pointers. Pre-mortem workflow details moved to `references/pre-mortem-workflow.md` to reduce context load for bug-fix tasks.
- `README.md` project-structure diagram updated to reflect new folders (`editor-integrations/`, `github-actions/`, `scripts/`) and new files.

### Notes for existing forks

- SKILL.md structure is backward-compatible: same sections, same rules, just shorter. LLM-trigger behaviour is unchanged.
- If you copied SKILL.md's pre-mortem section verbatim into your project, re-read it — the expanded version in `references/pre-mortem-workflow.md` is worth the diff.
- The CI validator is opt-in. Existing projects keep working unchanged.

## [1.0.0] — 2026-04-21

Initial release.

### Added

- `SKILL.md` — main entry point with triggering description, the DEBUG_LOG protocol, four non-negotiable rules, and the pre-mortem workflow.
- `templates/DEBUG_LOG.template.md` — drop-in file for project roots, seeded with `DL-000`.
- `templates/PREVENTION_RULES.template.md` — optional team summary index.
- `references/web.md` — error catalog for React / Next.js / Vite / Node / TypeScript / browser runtime / CSS.
- `references/ios.md` — error catalog for Swift / SwiftUI / UIKit / AVFoundation / URLSession / CoreData / lifecycle.
- `references/android.md` — error catalog for Kotlin / Jetpack Compose / Services / Accessibility / WorkManager / Hilt / overlays.
- `references/macos.md` — error catalog for AppKit / SwiftUI / entitlements / sandbox / hardened runtime / menu-bar apps / global permissions.
- `references/kotlin.md` — language-level catalog: coroutines, Flow, serialization, interop, data-class semantics.
- `references/swift.md` — language-level catalog: async/await, `@MainActor`, Sendable, generics, Codable, Previews.
- `references/cross-cutting.md` — universal traps: timezones, encoding, floats, HTTP retries, flaky tests, caching, secrets.
- `references/preempt-checklist.md` — per-track pre-mortem questions to ask before starting a new feature.
- `examples/example-DEBUG_LOG.md` — filled-in log with six worked entries across tracks.
- `examples/example-session.md` — walkthrough of an LLM-driven debugging session using this skill.
- `README.md`, `LICENSE` (MIT), `CHANGELOG.md`.
