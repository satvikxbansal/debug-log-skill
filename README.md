# debug-log-skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Works with Claude Code](https://img.shields.io/badge/Claude%20Code-ready-blueviolet)](editor-integrations/CLAUDE.md)
[![Works with Cursor](https://img.shields.io/badge/Cursor-rule-5865F2)](editor-integrations/cursor/rules/debug-log.mdc)
[![Works with Aider / Codex](https://img.shields.io/badge/AGENTS.md-supported-2ea44f)](editor-integrations/AGENTS.md)
[![CI: validate DEBUG_LOG](https://img.shields.io/badge/CI-validate%20DEBUG__LOG-lightgrey)](github-actions/validate-debug-log.yml)

A Claude / Cursor / Claude-Code skill that makes any LLM a more disciplined debugger. It enforces a structured `DEBUG_LOG.md` discipline, applies a "think before coding" pre-flight, and ships a battle-tested pre-mortem catalog of common traps across web, iOS, Android, and macOS codebases.

> **Status:** v1.1 — stable, opinionated, ready to fork.

## Install in one command

From inside any project where you want the discipline:

```bash
curl -sSfL https://raw.githubusercontent.com/<you>/debug-log-skill/main/scripts/init.sh | bash -s -- .
```

This drops `DEBUG_LOG.md`, `PREVENTION_RULES.md`, and a stub `CLAUDE.md` into your project root (none are overwritten if they already exist). Then commit them.

If you prefer not to pipe curl to bash — fork the repo, clone it, and run `./scripts/init.sh /path/to/your/project` from inside the clone.

## What this gives you

Two things that compound:

1. **A debugging discipline.** Every bug fix appends a numbered entry to `DEBUG_LOG.md` at your project root. Entries are structured, searchable, and append-only. Over time, the log becomes the single most valuable onboarding document in your repo — the invisible rules of your codebase, made visible.

2. **A pre-mortem error catalog.** Before writing new code, the skill consults reference files keyed by your stack — `web.md`, `ios.md`, `android.md`, `macos.md`, plus language-level Kotlin and Swift references and a cross-cutting catalog of universal bugs. Each entry documents a real, recurring trap with its symptom, root cause, fix pattern, and a prevention rule.

The premise: the most valuable debugging is the debugging you never had to do, because you'd seen the pattern before. This skill is how you bank that pattern recognition across sessions, across people, and across platforms.

## Tracks supported

| Track | Covers |
|---|---|
| web | React, Next.js (Pages + App router), Vite, TypeScript, Node, browser runtime, CSS/layout |
| ios | Swift, SwiftUI, UIKit, AVFoundation, URLSession, CoreData, navigation, lifecycle |
| android | Kotlin, Jetpack Compose, lifecycle, Room, Hilt, services, accessibility, WorkManager, overlays |
| macos | AppKit, SwiftUI, entitlements, sandbox, hardened runtime, menu-bar apps, global permissions |
| kotlin | Cross-platform Kotlin: coroutines, Flow, serialization, KMP, interop, data classes |
| swift | Cross-platform Swift: async/await, `@MainActor`, Sendable, generics, Codable, Previews |
| cross-cutting | Timezones, encoding, floats, HTTP retries, flaky tests, race conditions, caching, secrets |

A project can be in more than one track — a Kotlin Multiplatform app is `android + ios + kotlin + swift + cross-cutting`. The skill reads only the references that apply.

## Quickstart

### For Claude Code / Claude Desktop / Cowork

```bash
# User-scope (available in every project)
mkdir -p ~/.claude/skills
cp -r debug-log-skill ~/.claude/skills/debug-log

# OR project-scope (only in this project)
mkdir -p .claude/skills
cp -r debug-log-skill .claude/skills/debug-log
```

Then start a session and mention debugging, a crash, or a new feature in one of the supported tracks. The skill triggers automatically via its description.

### For Cursor

Copy the skill body into `.cursor/rules/debug-log.mdc` with the following frontmatter:

```markdown
---
description: DEBUG_LOG protocol + pre-mortem catalog for bug fixes and new features
globs: ["**/*"]
alwaysApply: true
---
```

Reference files in `references/` can be pointed at from the main rule (Cursor supports cross-file rule composition).

### For any other LLM harness

The skill is pure Markdown. Drop the folder wherever your harness loads skill files, or paste `SKILL.md` into your system prompt and keep the reference files available for the agent to read on demand.

## Using it

In a new project:

```
1. Drop templates/DEBUG_LOG.template.md at your project root as DEBUG_LOG.md.
2. Identify your track(s). Edit the top of DEBUG_LOG.md to list them.
3. Work normally. The first time you fix a bug, append DL-001.
4. From then on, follow the four rules: sequence / never skip / read before coding / append-only.
```

In an existing project that already has the discipline:

```
1. Ensure DEBUG_LOG.md exists at project root.
2. Before starting work, ask Claude to "check the debug log for relevant prevention rules."
3. The skill handles the rest.
```

## Why `DEBUG_LOG.md`?

Because it's boring, portable, and LLM-friendly:

- **Boring** — just Markdown at the repo root. No servers, no databases, no SaaS.
- **Portable** — moves with the repo. Works on every OS and IDE.
- **LLM-friendly** — structured fields, easy to grep, easy to cite.
- **Human-friendly** — code reviewers and new hires read it as part of onboarding.
- **Versioned with the code** — history is in `git log`; cross-references work.

Other patterns (issue tracker comments, Slack threads, tribal knowledge) all lose the invariant that matters: *the log travels with the code and is read by everyone who touches it.*

## Customising

The skill is designed to be forked. Teams should:

1. **Add their own reference files** to `references/` for internal systems (e.g., `references/our-auth-service.md`). Point at them from `SKILL.md`.
2. **Extend the checklist** in `references/preempt-checklist.md` with questions your team has learned to ask.
3. **Trim what they don't use** — a pure web team can delete the iOS/Android/macOS references.
4. **Promote rules** — when a prevention rule appears in DL three times, move it to `.cursor/rules/`, `CLAUDE.md`, `AGENTS.md`, or wherever your ambient guidance lives.

## Project structure

```
debug-log-skill/
├── SKILL.md                              # Main entry point (loaded into LLM context)
├── README.md                             # This file
├── LICENSE                               # MIT
├── CHANGELOG.md                          # Version history
├── CONTRIBUTING.md                       # Contribution guide + entry format
├── templates/
│   ├── DEBUG_LOG.template.md             # Drop at project root
│   ├── PREVENTION_RULES.template.md      # Generic PREVENTION_RULES starter
│   ├── PREVENTION_RULES.web.template.md
│   ├── PREVENTION_RULES.ios.template.md
│   ├── PREVENTION_RULES.android.template.md
│   ├── PREVENTION_RULES.macos.template.md
│   ├── PREVENTION_RULES.kotlin.template.md
│   └── PREVENTION_RULES.swift.template.md
├── references/
│   ├── web.md                            # Web-stack error catalog
│   ├── ios.md                            # iOS catalog
│   ├── android.md                        # Android catalog
│   ├── macos.md                          # macOS catalog
│   ├── kotlin.md                         # Language-level Kotlin
│   ├── swift.md                          # Language-level Swift
│   ├── cross-cutting.md                  # Universal bugs
│   ├── preempt-checklist.md              # Per-track pre-mortem questions
│   └── pre-mortem-workflow.md            # The four-phase workflow for new features
├── examples/
│   ├── example-DEBUG_LOG.md              # Filled-in example log
│   └── example-session.md                # Walkthrough of a debugging session
├── editor-integrations/
│   ├── README.md                         # Which file to grab for which editor
│   ├── CLAUDE.md                         # Sample project-level rules for Claude Code / Cowork
│   ├── AGENTS.md                         # For Aider / Codex / OpenAI Agents
│   └── cursor/rules/debug-log.mdc        # Cursor rule file
├── github-actions/
│   ├── README.md
│   ├── validate-debug-log.yml            # CI workflow
│   └── validate_debug_log.py             # Validator script
└── scripts/
    └── init.sh                           # One-shot project initialiser
```

## Prior art and inspiration

- **Andrej Karpathy's skills collection** — the "Think Before Coding" / "Simplicity First" / "Surgical Changes" / "Goal-Driven Execution" rules influenced the pre-flight pattern in this skill. The debugging discipline adds a persistence layer to those habits.
- **The `DEBUG_LOG.md` protocol** from the Handy macOS / Android project — the original seven-field template that this skill generalises.
- **Post-mortem culture** from Google SRE, Jason Fried's "Getting Real", and the broader software-engineering tradition — log the class of failure, not just the instance.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full entry format, review criteria, and how to add a new track. Roughly in order of value:

1. **New prevention-rule entries** in the catalog. Must be real bugs you've actually shipped and fixed — not theory.
2. **New tracks** — e.g., Rust, Go, Flutter, React Native. Follow the shape of existing reference files.
3. **Tightening of existing entries** — better prevention rules, better root-cause phrasing.
4. **Examples** — annotated DEBUG_LOG.md files from real projects (sanitised) are very welcome.

Every contribution must preserve the format so the skill stays LLM-readable.

## License

MIT. See `LICENSE`. Fork freely.

## Not a replacement for

This skill is not:

- An issue tracker (log the bug *class*, not the instance; use Linear/Jira/GitHub Issues for individual tickets).
- A monitoring system (log fixed bugs; use Sentry/Datadog for live errors).
- A runbook (document *classes* of bugs; use runbooks for operator responses).
- A linter (prevention rules are human-checked; use ESLint/ktlint/detekt/SwiftLint for automated checks — and promote rules to those tools when it makes sense).

The DEBUG_LOG is the long-memory layer that sits above these tools and connects them.
