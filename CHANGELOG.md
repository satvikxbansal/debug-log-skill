# Changelog

All notable changes to `debug-log-skill` are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers follow [SemVer](https://semver.org/).

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
