# debug-log-skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Works with Claude Code](https://img.shields.io/badge/Claude%20Code-ready-blueviolet)](editor-integrations/CLAUDE.md)
[![Works with Cursor](https://img.shields.io/badge/Cursor-rule-5865F2)](editor-integrations/cursor/rules/debug-log.mdc)
[![Works with Aider / Codex](https://img.shields.io/badge/AGENTS.md-supported-2ea44f)](editor-integrations/AGENTS.md)
[![CI: validate DEBUG_LOG](https://img.shields.io/badge/CI-validate%20DEBUG__LOG-lightgrey)](github-actions/validate-debug-log.yml)

> **Status:** v2.0 — the active knowledge graph upgrade.

**A skill that turns every bug you fix into a rule the next person (or the next LLM session) won't have to rediscover.**

LLM coding assistants are fast, but they're forgetful. They'll ship the same subtle bug a second time, six weeks later, because the context from the first fix evaporated. This skill fixes that. Every bug you fix gets a short, structured entry in a file called `DEBUG_LOG.md` at your project root. Before writing new code, the agent greps that file to find rules that apply. Over a few weeks, the log becomes the highest-signal document in your repo — a living memory that humans and LLMs share.

## The one-minute pitch

Three things compound when you use this:

1. **You stop re-shipping the same bug.** Every fix writes down what went wrong, what you believed that turned out to be false, and the rule that would have caught it. Next time anyone — you, a teammate, Claude, Cursor, Aider — touches that code, they find the rule before they re-break it.
2. **Your agent stops hallucinating the same wrong API.** `LLM Hallucination or Assumption` is a first-class bug category in this skill. When the agent invents a function that doesn't exist, you log it. The prevention rule ("this Compose modifier doesn't exist, use X") lives in the same place as every other lesson.
3. **Your project builds a library of its own weird corners.** Timezone bugs, hydration quirks, race conditions in that one screen — they stop being tribal knowledge and start being searchable.

## What's new in v2.0

v1 asked the agent to skim the whole log before every task. That breaks the moment the log has more than twenty entries — there's too much to skim, and the rule you need gets buried. v2.0 upgrades the log from a ledger into an **active knowledge graph**:

- **Active pre-flight grep.** Before touching a file, the agent runs three kinds of search against `DEBUG_LOG.md`: by filename, by tag (like `#Compose` or `#Hydration`), and by root-cause category (like `Race Condition` or `LLM Hallucination`). It reads only the handful of entries that match. No more whole-file scans.
- **Tags.** Every entry carries at least one track tag (which platform) and one semantic tag (which concept). Tags come from a short, canonical vocabulary in `references/tag-taxonomy.md`, so searches are predictable.
- **Environment stamps.** Every entry records the SDK / library / OS versions in play when the bug happened. A rule written for Compose 1.5 should not silently fire on Compose 1.7 — the environment field makes that check possible.
- **Iteration counter.** Every entry records how many tries it took to land the fix. `0` = first shot. `5+` = the agent was stuck in a hallucination loop, which triggers a short written reflection on which assumption kept failing. Over time, counting iterations tells you where your agent keeps slipping.
- **`[OBSOLETE]` rule lifecycle.** When a rule stops applying (you upgraded Next.js, you replaced the old auth middleware), you don't delete the old entry. You tombstone it — prepend `[OBSOLETE]` to the title — and write a new entry that says "supersedes DL-031 because we migrated to X." Nothing is lost; the log stays honest.
- **14 canonical root-cause categories.** A closed list: `API Change`, `Race Condition`, `Scope Leak`, `Hydration Mismatch`, `LLM Hallucination or Assumption`, and so on. Over time, counting categories tells you where to invest: "42% of our DL entries are Race Conditions" is a loud signal.

The full reasoning behind each of these is in `CHANGELOG.md` under `[2.0.0]`.

## Install it as a Claude skill

```bash
git clone https://github.com/<you>/debug-log-skill.git
cd debug-log-skill
./scripts/package-skill.sh            # writes ./dist/debug-log-skill.skill
```

Then upload `dist/debug-log-skill.skill` wherever Claude Skills are managed (claude.ai → Skills → Upload, or the Cowork / Claude Code skills folder).

The packager does the annoying parts for you: it excludes `.git/`, `.DS_Store`, editor caches, and scratch folders; it stages the contents into a directory whose name matches the `name` field in `SKILL.md` (which is what Anthropic's skill upload pipeline checks); and it produces a single clean `.skill` zip ready to drop in.

If you'd rather install manually:

```bash
# User-scope (available in every project Claude sees)
mkdir -p ~/.claude/skills
cp -r . ~/.claude/skills/debug-log-skill

# Or project-scope (this project only)
mkdir -p .claude/skills
cp -r . .claude/skills/debug-log-skill
```

## Add it to a project

Once the skill is installed, run the init script from inside the project you want to protect:

```bash
./scripts/init.sh /path/to/your/project
```

This drops three files at the project root, without overwriting anything that already exists:

- `DEBUG_LOG.md` — the log. Seeded with a `DL-000` entry explaining the rules.
- `PREVENTION_RULES.md` — an optional summary file for rules that have been promoted.
- `CLAUDE.md` — a short stub that points your LLM at the skill and lists the four non-negotiable rules.

Commit all three. The next time the agent starts work, it reads the stub, reads the log, and follows the protocol.

Not using Claude? There are drop-in samples for other harnesses in `editor-integrations/`:

| Your tool | Use the file |
|---|---|
| Claude Code / Claude Desktop / Cowork | `editor-integrations/CLAUDE.md` |
| Cursor | `editor-integrations/cursor/rules/debug-log.mdc` |
| Aider / Codex / OpenAI Agents / any `AGENTS.md`-aware harness | `editor-integrations/AGENTS.md` |

## The four rules

Only four, and they're all there to keep the log trustworthy:

1. **Sequence.** Entries are numbered `DL-001`, `DL-002`, `DL-003`, and so on. Never skip a number. Never reuse one.
2. **Never skip a bug.** Every fix — build error, runtime crash, flaky test, logic bug, perf regression, incident — gets a `DL-NNN` entry. Even the five-minute typo fix. Logging is cheap; rediscovering a subtle bug six months later is not.
3. **Active pre-flight, not passive skim.** Before editing, `grep` the log for the filename, tag, or category you're about to touch. Read only what matches. Do not read the whole log end-to-end.
4. **Append-only.** Never delete or edit an existing entry. When a rule is retired, prepend `[OBSOLETE]` to its title (the only permitted mutation) and supersede it with a new entry.

## What an entry looks like

```markdown
### DL-023 — Foreground service crash on Android 14 startup

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Tags** | `#android #ForegroundService #Permissions` |
| **Severity** | Runtime Crash |
| **Environment** | Android API 34, compileSdk 34, AGP 8.3 |
| **File(s)** | `app/src/main/java/com/example/MyService.kt` |
| **Symptom** | `ForegroundServiceStartNotAllowedException` on cold start after app update. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | Android 14 requires declaring a `foregroundServiceType` matching the service's real purpose. We had only `dataSync` declared but were doing media playback, so the system rejected the start. |
| **Fix** | Added `android:foregroundServiceType="mediaPlayback"` in manifest; requested `FOREGROUND_SERVICE_MEDIA_PLAYBACK` at runtime. Commit `b3d0f2a`. |
| **Iterations** | 2 |
| **Prevention Rule** | When starting a foreground service on Android 14+, declare every `foregroundServiceType` you actually use in the manifest **and** hold its runtime permission. **Why:** the OS rejects mismatched or missing types on cold start (DL-023). |
```

Everything you need to understand the bug class later, in a tabular shape an LLM can parse. See `examples/example-DEBUG_LOG.md` for nine worked entries across tracks, including a `[OBSOLETE]` tombstone and an `LLM Hallucination or Assumption` example.

## Tracks supported out of the box

| Track | Covers |
|---|---|
| `web` | React, Next.js (Pages + App router), Vite, TypeScript, Node, browser runtime, CSS/layout |
| `ios` | Swift, SwiftUI, UIKit, AVFoundation, URLSession, CoreData, navigation, lifecycle |
| `android` | Kotlin, Jetpack Compose, lifecycle, Room, Hilt, services, accessibility, WorkManager, overlays |
| `macos` | AppKit, SwiftUI, entitlements, sandbox, hardened runtime, menu-bar apps, global permissions |
| `kotlin` | Cross-platform Kotlin: coroutines, Flow, serialization, KMP, interop, data classes |
| `swift` | Cross-platform Swift: async/await, `@MainActor`, Sendable, generics, Codable, Previews |
| `cross-cutting` | Timezones, encoding, floats, HTTP retries, flaky tests, race conditions, caching, secrets |

A project can be in more than one track — a Kotlin Multiplatform app is `android + ios + kotlin + swift + cross-cutting`. The skill reads only the track files that apply. Adding a new track (Rust, Go, Flutter, React Native, Unity) takes five files and is spelled out in `CONTRIBUTING.md`.

## What makes this stand out

Most LLM-coding guidance today falls into two camps: generic "think step by step" rules, or very tool-specific linter configs. This skill sits in the middle and does three things neither camp does:

- **It persists lessons across sessions.** The log is a file in the repo, not state in a chat. The next session — yours, a teammate's, a fresh Claude conversation — starts with the full memory.
- **It treats the LLM's own failure modes as first-class.** `LLM Hallucination or Assumption` is a category. `Iterations ≥ 5` triggers a reflection. When the agent is stuck in a loop, the protocol makes the loop visible instead of hiding it under a successful-looking commit.
- **It scales with the log.** Most "write things down" systems break when the doc gets long. The active pre-flight grep means a log with 500 entries is as usable as a log with 5, because you only ever load the 3–4 entries the search surfaces.

## CI

`github-actions/validate_debug_log.py` validates every PR that touches `DEBUG_LOG.md`. It checks the sequence, the 11 required fields, the track-plus-semantic tag rule, the 14-category root-cause vocabulary, the `Iterations` integer, the `[OBSOLETE]` / supersede handshake, and the `**Why:**` marker on every prevention rule. On success it prints a one-line summary (`N entries (X active, Y obsolete), all valid.`) so you get a pulse on the log's shape in every PR. Details in `github-actions/README.md`.

## Why `DEBUG_LOG.md` and not a SaaS tool?

Because it's boring and that's the point:

- **Markdown at the repo root** — no servers, no databases, no vendor lock-in.
- **Travels with the repo** — moves on every clone, every fork. Works on every OS.
- **LLM-friendly** — structured enough to grep, plain enough to read aloud.
- **Human-friendly** — a new hire reads the log as onboarding. Code reviewers cite it in PRs.
- **Versioned with the code** — `git blame` tells you when a rule appeared, `git log` tells you why.

The log travels with the code and is read by everyone who touches it. That's the invariant that matters. Issue trackers, Slack threads, and tribal knowledge all lose it.

## Project layout

```
debug-log-skill/
├── SKILL.md                          # Main entry point (loaded into the LLM's context)
├── README.md                         # This file
├── LICENSE                           # MIT
├── CHANGELOG.md                      # Version history, incl. v2.0 migration guide
├── CONTRIBUTING.md                   # Entry format, rubric, new-track instructions
├── templates/
│   ├── DEBUG_LOG.template.md         # Drop at project root (seeded with DL-000)
│   ├── PREVENTION_RULES.template.md  # Generic promoted-rules starter
│   └── PREVENTION_RULES.<track>.template.md   # Per-language variants
├── references/
│   ├── tag-taxonomy.md               # The canonical tags + 14 root-cause categories
│   ├── web.md / ios.md / android.md / macos.md / kotlin.md / swift.md
│   ├── cross-cutting.md              # Universal traps (read every session)
│   ├── preempt-checklist.md          # Per-track pre-mortem questions
│   └── pre-mortem-workflow.md        # Four-phase workflow for new features
├── examples/
│   ├── example-DEBUG_LOG.md          # Nine worked v2.0 entries across tracks
│   └── example-session.md            # Full walkthrough of an LLM using the skill
├── editor-integrations/
│   ├── README.md                     # Which file goes with which editor
│   ├── CLAUDE.md / AGENTS.md / cursor/rules/debug-log.mdc
├── github-actions/
│   ├── README.md
│   ├── validate-debug-log.yml        # CI workflow
│   └── validate_debug_log.py         # Validator for the v2.0 schema
└── scripts/
    ├── init.sh                       # One-shot project initialiser
    └── package-skill.sh              # Builds a clean .skill for Claude upload
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full entry format, the prevention-rule rubric, and how to add a new track. The highest-value contributions are:

1. **New reference entries** — real bugs you've shipped and fixed, in the four-field shape (Symptom / Root cause / Fix / Prevention rule).
2. **New tracks** — Rust, Go, Flutter, React Native, Unity. Follow the shape of existing `references/*.md` files; `CONTRIBUTING.md` lists the seven places you'll need to touch.
3. **Tighter prevention rules** on existing entries — the rule is the output that matters, and sharpening one benefits every future adopter.
4. **New worked examples** — annotated `DEBUG_LOG.md` excerpts from real projects (sanitised).

Every contribution must preserve the format so the skill stays machine-readable.

## Prior art

- **Andrej Karpathy's skills collection** — "Think Before Coding", "Simplicity First", "Surgical Changes" influenced the pre-flight pattern here. This skill adds the persistence layer those habits were missing.
- **The `DEBUG_LOG.md` protocol** from the Handy macOS / Android project — the original seven-field template that v1 generalised.
- **Google SRE post-mortem culture** — log the class of failure, not just the instance.

## Not a replacement for

- An issue tracker — log the bug *class*, not the individual ticket. Use Linear / Jira / GitHub Issues for instances.
- A monitoring system — log bugs you've *already fixed*. Use Sentry / Datadog for live errors.
- A runbook — document *classes* of bugs. Use runbooks for operator responses.
- A linter — prevention rules are human-checked. Use ESLint / ktlint / detekt / SwiftLint for the automated checks, and promote rules to those tools when it makes sense.

The DEBUG_LOG is the long-memory layer that sits above these tools and connects them.

## License

MIT. See `LICENSE`. Fork freely.
