# Changelog

All notable changes to `debug-log-skill` are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers follow [SemVer](https://semver.org/).

## [2.0.0] — 2026-04-21

**Breaking release.** The DEBUG_LOG protocol is promoted from a "dumb ledger" to an **active knowledge graph**. Existing v1.x entries continue to validate (the checker is tolerant of the old shape when `[OBSOLETE]`-tombstoned), but any new entry must use the v2.0 template. Skim the migration guide below before upgrading a live project.

### Why (the four flaws v2.0 addresses)

1. **Context-window bloat.** Skimming a 100-entry `DEBUG_LOG.md` on every turn does not scale. v2.0 replaces whole-file reads with **active pre-flight grep** on filenames, tags, and Root Cause Categories.
2. **Passive retrieval.** Even when the relevant rule lives in the log, a skim can miss it. v2.0 adds a closed semantic-tag vocabulary so searches are deterministic.
3. **Missing environment context.** A prevention rule written for Compose 1.5 can silently misfire on Compose 1.7. v2.0 makes `Environment` (SDK / library / OS versions) a required field.
4. **No iteration signal.** Hallucination loops are invisible in v1.x. v2.0 adds an `Iterations` counter and treats `5+` as a mandatory reflection trigger.

### Added

- **Active pre-flight grep protocol** (SKILL.md step 3). Three canonical grep patterns — by file path, by tag, by Root Cause Category — become the mandatory pre-edit move. The LLM reads only the entries grep surfaces plus their cross-references (`Supersedes DL-XXX` / `See DL-XXX`).
- **`references/tag-taxonomy.md`** — the canonical vocabulary:
  - 7 track tags (`#web #ios #android #macos #kotlin #swift #cross-cutting`).
  - Open semantic-tag list organised by UI/rendering, framework-specific, concurrency, data, network, navigation, platform/permissions, build/tooling, testing, perf, security, observability.
  - 14 Root Cause Categories with definitions and real examples.
  - Grep recipes for the most common queries.
- **`LLM Hallucination or Assumption`** promoted to a first-class Root Cause Category, with a worked example (DL-007 in `examples/example-DEBUG_LOG.md`: an agent invented a non-existent `.onHoverEnter` Compose modifier, Iterations = 4).
- **`[OBSOLETE]` rule lifecycle.** Retired rules get `[OBSOLETE]` prepended to their title (the only permitted mutation on an existing entry) and are superseded by a new entry that leads with `> Supersedes DL-XXX. Reason: …`. Worked example at DL-008 — Next.js 15 RSC migration retiring DL-001's hydration rule.
- **`scripts/package-skill.sh`** — clean packaging into `<skill-name>.skill` for upload to Claude / Cowork Skills. Excludes `.git/`, `.DS_Store`, `.gitignore`, `.gitattributes`, editor caches, and `dist/`. Stages into a folder whose name matches the frontmatter `name`, which is what Anthropic's upload pipeline expects.

### Changed

- **SKILL.md entry template — breaking.** The v2.0 template has 11 fields: `Date`, `Tags`, `Severity`, `Environment`, `File(s)`, `Symptom`, `Root Cause Category`, `Root Cause Context`, `Fix`, `Iterations`, `Prevention Rule`. v1.x's `Track` field is subsumed by the mandatory track tag; `Root Cause` is split into the closed-vocabulary `Root Cause Category` plus the free-text `Root Cause Context`.
- **SKILL.md `name`** changed from `debug-log` to `debug-log-skill` to match the repo / folder name. This is what makes `.skill` uploads succeed: Anthropic's validator expects the archive's top-level directory to match the frontmatter `name` exactly.
- **Rule 3 rewritten.** Was "Read before coding (skim DEBUG_LOG.md)". Now "Active pre-flight, not passive skim (grep the log)."
- **`github-actions/validate_debug_log.py`** — upgraded to v2.0 schema: checks the 11 required fields, the 14 canonical Root Cause Categories, the track + semantic tag rule, the `Iterations` integer, the `[OBSOLETE]` / `Supersedes DL-XXX` handshake, and prints summary counts (`N entries (X active, Y obsolete), all valid`). Tolerates both v2.0 start-at-`DL-000` templates and v1.x start-at-`DL-001` projects.
- **`references/pre-mortem-workflow.md`** — Phase 2 now includes the three active pre-flight grep patterns alongside the catalog skim. Phase 4's "Applicable prevention rules" explicitly asks for the DL numbers the pre-flight grep surfaced.
- **`editor-integrations/*` + `scripts/init.sh`** — all four editor integration samples (CLAUDE.md, AGENTS.md, cursor/rules/debug-log.mdc, plus the init.sh-generated stub) now reference the v2.0 rules, the grep patterns, the v2.0 template, and the 14 canonical Root Cause Categories.
- **`CONTRIBUTING.md`** — "Format for a new reference entry" and "Format for a project DEBUG_LOG.md entry" updated to v2.0. New-track instructions expanded to include updating `tag-taxonomy.md` and the `VALID_TRACK_TAGS` set in the validator. Review criteria now check tag rules and Root Cause Category membership.
- **`examples/example-DEBUG_LOG.md`** — every existing entry rewritten in the v2.0 shape. Added DL-007 (LLM Hallucination) and DL-008 (supersede of DL-001). DL-001's title now starts with `[OBSOLETE]`, demonstrating the tombstone pattern.
- **`examples/example-session.md`** — the walkthrough now shows the active pre-flight grep (four targeted queries return DL-003, DL-004, DL-006, DL-008 before any code is written), and a later iteration bump to Iterations = 3 with a reflection on the actor/async assumption that kept failing.

### Migration guide (v1.x → v2.0)

Running project with a populated `DEBUG_LOG.md`? You have three options:

1. **Do nothing.** The validator accepts v1.x entries as-is. Just write new entries in the v2.0 shape. The two shapes coexist in the same log.
2. **Retrofit gradually.** When you next touch an old entry (e.g., you realise the rule is now obsolete), write a v2.0 supersede entry that points back with `> Supersedes DL-XXX. Reason: migrated to v2.0 template with Tags / Environment / Root Cause Category / Iterations.` and prepend `[OBSOLETE]` to the old title. The old fields remain readable; the new one is the current rule.
3. **Retrofit in bulk.** Run a one-time pass that adds the five new fields (`Tags`, `Environment`, `Root Cause Category`, `Root Cause Context`, `Iterations`) to every existing entry. If you go this route, bump the log header to note the migration date so readers know which entries were back-filled versus authored in v2.0.

Recommended: option 1 for first-party projects, option 2 for long-lived OSS repos, option 3 only if you have CI teeth that would otherwise fail on missing fields.

### Notes for existing forks

- The editor-integration samples changed in place. Merge the new `DEBUG_LOG discipline (v2.0)` section into your project's existing CLAUDE.md / AGENTS.md / cursor rules — don't copy wholesale if you've customised.
- `scripts/init.sh` only writes stubs when the target file is absent. It will not overwrite a v1.x CLAUDE.md — for that, either delete the old file first or merge by hand.

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
