# Changelog

All notable changes to `debug-log-skill` are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers follow [SemVer](https://semver.org/).

## [2.0.1] — 2026-04-22

Hardening pass over the v2.0 contract. No template changes — all updates are under the hood. Existing v2.0 users do not need to re-author entries.

### Added

- **`scripts/debug_log_schema.py`** — single source of truth for the DEBUG_LOG v2.0 vocabulary (11 required fields, 12 severities [8 core + 4 extended], 14 Root Cause Categories, 7 track tags, 124-tag semantic taxonomy, regex patterns, rule-strength constants). The validator, the fixture test suite, and the planned CLI all import from this one module; there is no longer a stringly-typed duplicate anywhere in the repo.
- **`tests/` with 13 fixtures + `tests/run_tests.py`.** 17 test cases covering: valid minimal / valid full / valid supersede handshake, orphan `[OBSOLETE]`, dangling `Supersedes DL-NNN`, `Supersedes` pointing at a non-tombstoned entry, gap in sequence, bad category, bad severity, bad iterations, too-many / missing / missing-semantic track tags, short rule, and `--strict` vs default behaviour on unknown semantic tags. Each failing case asserts the validator failed for the *right reason* by checking the stderr fragment, not just the exit code.
- **Validator: orphan-`[OBSOLETE]` detection.** A tombstoned entry without a later `Supersedes DL-NNN` pointing back now fails validation. (The docs promised this behaviour in v2.0; the validator did not enforce it until now.)
- **Validator: `Supersedes DL-NNN` backlink check.** Dangling references (target doesn't exist) and mis-targeted references (target title is not `[OBSOLETE]`) both fail. This is the exact shape of bug v2.0.0's `examples/example-DEBUG_LOG.md` accidentally shipped with — DL-008 was tagged `[OBSOLETE]` even though it was the superseding entry, not the tombstone.
- **Validator: HTML-commented entries are skipped.** The template ships with a commented DL-001 example; before this fix a freshly-initialised log reported "2 entries" on its first validator run. Fixed by `strip_html_comments()` in the schema module.
- **Validator: track-tag upper bound.** The taxonomy says "1 or 2 track tags"; the validator now enforces the upper bound. 3+ track tags on a single entry fails.
- **Validator: `--strict` flag.** Default mode keeps the semantic-tag vocabulary open (projects legitimately invent tags). `--strict` additionally requires every semantic tag to come from `references/tag-taxonomy.md`. Useful in CI once a project's taxonomy has stabilised.
- **`references/tag-taxonomy.md` — Agent & LLM section.** New semantic tags: `#LLM`, `#Agent`, `#Hallucination`, `#Grounding`, `#Prompt`, `#ToolUse`. Agent-produced bugs are a first-class category under `LLM Hallucination or Assumption`; the tags let entries carry the orthogonal signal.
- **`ROADMAP.md`** — honest evaluation and sequencing for Phases 2–8 (Python CLI; environment-aware tooling; retrieval intelligence; rule promotion; evidence capture via sidecar incidents; expanded track surface [Python backend, Postgres, Docker/K8s first]; MCP server as a separate package). Each phase lists concerns and mitigations; Phase 8's `append_debug_log_entry` tool is explicitly rejected in favour of `stub_debug_log_entry` + author fills the prose.

### Changed

- **`scripts/init.sh`** — rewritten to scaffold the full integration set in one pass: `DEBUG_LOG.md`, `PREVENTION_RULES.md` (picks the matching per-track template when exactly one track is detected; otherwise the generic one), `CLAUDE.md`, `AGENTS.md`, and `.cursor/rules/debug-log.mdc`. Auto-detects tracks from the target project's manifests (`package.json`, `*.xcodeproj`, `build.gradle.kts`, `Package.swift`, etc.) unless overridden explicitly. Idempotent — re-running it on an initialised project prints "skip" lines rather than clobbering customised files.
- **`scripts/package-skill.sh`** — rsync and non-rsync fallback branches now share one exclude list so there is no behavioural drift between machines with rsync (macOS + Linux default) and without. Added `tests/` to the exclusion list so the fixture suite is not shipped in the `.skill` archive.
- **`github-actions/validate-debug-log.yml`** — install instructions now copy both `validate_debug_log.py` and `debug_log_schema.py` into `.github/scripts/`. Header corrected (was "seven-field template" from v1.x).
- **`github-actions/README.md`** — rewritten to match the actual v2.0 validator behaviour, including the `--strict` flag and the `[OBSOLETE]` / `Supersedes DL-NNN` handshake (both directions). Drops the v1.x-compat overreach; severity list reflects the 8 core + 4 extended split documented in the schema.
- **`SKILL.md`** — severity vocabulary now documents both the 8 core labels and the 4 extended ones (`Informational`, `Runtime Warning`, `UX Regression`, `Security`) in a paragraph between the entry template and the four rules. Track-tag usage clarified to "1–2 track tags (use two only when the bug genuinely spans stacks)".
- **`references/tag-taxonomy.md`** — "Every entry needs exactly one or two of these" is now "At least one and at most two", matching what the validator actually enforces.
- **Editor integration samples** (`editor-integrations/CLAUDE.md`, `AGENTS.md`, `cursor/rules/debug-log.mdc`, `README.md`) — skill-path references corrected from `~/.claude/skills/debug-log/` to `~/.claude/skills/debug-log-skill/` to match the frontmatter `name`. Severity lines list both core and extended labels.
- **`templates/DEBUG_LOG.template.md`** — severity reference line shows both the 8 core and 4 extended severities, so the seed entry's `Informational` severity doesn't read as undocumented.

### Fixed

- **`examples/example-DEBUG_LOG.md` — DL-008 title.** DL-008 is the *superseding* entry that retires DL-001, but its v2.0.0 title was `### DL-008 — [OBSOLETE] DL-001: hydration guard no longer needed after RSC migration`. The `[OBSOLETE]` prefix is the tombstone marker for the entry it is written on, not for the entry it retires. The validator (correctly, under the new v2.0.1 checks) flagged DL-008 as an orphan tombstone. Fixed: `### DL-008 — RSC migration retires DL-001 hydration guard`. The `> Supersedes DL-001.` line in DL-008's body is the canonical way to express the retirement.

## [2.0.0] — 2026-04-21

**Breaking release.** The DEBUG_LOG protocol is promoted from a "dumb ledger" to an **active knowledge graph**. The v2.0 validator enforces the full 11-field template on every non-`[OBSOLETE]` entry — v1.x entries **do not validate** unless they are explicitly tombstoned with `[OBSOLETE]` and superseded by a v2.0 entry. Skim the migration guide below before upgrading a live project.

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
- **`github-actions/validate_debug_log.py`** — upgraded to v2.0 schema: checks the 11 required fields, the 14 canonical Root Cause Categories, 1–2 track tags plus ≥1 semantic tag, the `Iterations` integer, the `[OBSOLETE]` / `Supersedes DL-XXX` handshake (orphaned tombstones and dangling supersede references both fail), and prints summary counts (`N entries (X active, Y obsolete), all valid`). Starts-at-`DL-000` and starts-at-`DL-001` are both accepted; HTML-commented example entries inside the template are skipped. Vocabulary now imported from `scripts/debug_log_schema.py` — a single source of truth shared with the test fixtures and the forthcoming CLI. New `--strict` flag additionally requires semantic tags to come from `references/tag-taxonomy.md`.
- **`references/pre-mortem-workflow.md`** — Phase 2 now includes the three active pre-flight grep patterns alongside the catalog skim. Phase 4's "Applicable prevention rules" explicitly asks for the DL numbers the pre-flight grep surfaced.
- **`editor-integrations/*` + `scripts/init.sh`** — all four editor integration samples (CLAUDE.md, AGENTS.md, cursor/rules/debug-log.mdc, plus the init.sh-generated stub) now reference the v2.0 rules, the grep patterns, the v2.0 template, and the 14 canonical Root Cause Categories.
- **`CONTRIBUTING.md`** — "Format for a new reference entry" and "Format for a project DEBUG_LOG.md entry" updated to v2.0. New-track instructions expanded to include updating `tag-taxonomy.md` and the `VALID_TRACK_TAGS` set in the validator. Review criteria now check tag rules and Root Cause Category membership.
- **`examples/example-DEBUG_LOG.md`** — every existing entry rewritten in the v2.0 shape. Added DL-007 (LLM Hallucination) and DL-008 (supersede of DL-001). DL-001's title now starts with `[OBSOLETE]`, demonstrating the tombstone pattern.
- **`examples/example-session.md`** — the walkthrough now shows the active pre-flight grep (four targeted queries return DL-003, DL-004, DL-006, DL-008 before any code is written), and a later iteration bump to Iterations = 3 with a reflection on the actor/async assumption that kept failing.

### Migration guide (v1.x → v2.0)

The v2.0 validator enforces every field on every active entry, so v1.x logs will fail CI as soon as you turn the validator on. Pick a migration strategy before wiring the workflow into required checks:

1. **Tombstone everything, rewrite forward.** Prepend `[OBSOLETE]` to every v1.x entry's title, then author new v2.0 entries as you touch the relevant code. The validator skips Prevention-Rule strength checks on `[OBSOLETE]` entries, so a lightly-tagged tombstone passes. Good for long-lived OSS repos where bulk retrofitting is too much churn.
2. **Retrofit gradually.** When you next touch an old entry (e.g., you realise the rule is obsolete), write a v2.0 supersede entry that points back with `> Supersedes DL-XXX. Reason: migrated to v2.0 template with Tags / Environment / Root Cause Category / Iterations.` and prepend `[OBSOLETE]` to the old title. This is the cleanest option if you're already iterating on the rules.
3. **Retrofit in bulk.** One-time pass that adds the five new fields (`Tags`, `Environment`, `Root Cause Category`, `Root Cause Context`, `Iterations`) to every existing entry. Needed if you want every historical entry to count as an active rule under v2.0. Bump the log header to note the migration date so readers know which entries were back-filled versus authored under v2.0.

Recommended: option 1 for most projects — you get the CI teeth immediately and retrofit organically. Option 3 only when the historical entries are still load-bearing prevention rules.

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
