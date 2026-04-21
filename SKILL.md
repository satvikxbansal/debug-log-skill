---
name: debug-log
description: Engineer-grade debugging discipline for any codebase. Invoke this skill before writing code on any non-trivial task AND every time you fix a bug, crash, build error, UI regression, flaky test, or unexpected behaviour. It enforces a structured `DEBUG_LOG.md` protocol, a "think before coding" pre-flight, and a pre-mortem catalog of frequently-encountered traps in web (React / Next.js / Node / TypeScript), iOS (Swift / SwiftUI / UIKit), Android (Kotlin / Compose), and macOS (Swift / AppKit / SwiftUI) codebases. Use this skill whenever the user mentions debugging, crashes, errors, "it's not working", "why is this broken", "the build is failing", "this test is flaky", "fix this bug", stack traces, exception types (NullPointerException, TypeError, SIGSEGV, fatal error), or when starting new implementation work in any of the supported tracks so prevention rules from prior bugs are read first.
---

# Debug Log Skill

This skill does two things, and they reinforce each other:

1. A **debugging discipline** — the `DEBUG_LOG.md` protocol. Every bug produces a numbered, append-only entry. Read before coding. Never skipped. The log is the project's memory across humans and LLM sessions.
2. A **pre-mortem catalog** — the bugs that actually recur in each supported stack, each with symptom / root cause / fix / prevention rule. Anticipate a class of bugs before you write the code that creates them.

Both halves share a single conviction: **the most valuable debugging work is the debugging you never had to do, because you'd seen the pattern before.** This skill is how you bank that pattern across sessions, across people, and across platforms.

---

## When this skill loads, do these things in order

### 1. Determine the track(s) this project uses

Look at the project root. Identify which apply (more than one is normal):

- **web** — `package.json`, `next.config.*`, `vite.config.*`, React/Vue/Svelte deps.
- **ios** — `*.xcodeproj`, `*.xcworkspace`, `Info.plist`, `Podfile`, `Package.swift` with iOS targets.
- **android** — `build.gradle.kts`, `AndroidManifest.xml`, `*.kt` in `app/`, `compileSdk` declarations.
- **macos** — AppKit references, `.entitlements` with hardened-runtime, `NSWindow` / `MenuBarExtra` code.
- **kotlin** — any Kotlin beyond Android (JVM, KMP, server) — coroutines, Flow, kotlinx.serialization.
- **swift** — any Swift beyond iOS/macOS — async/await, Sendable, SwiftPM packages.

Pick all that apply.

### 2. Read the matching reference(s)

For each track identified, read `references/<track>.md`. Skim titles; read in full the entries whose symptoms match the current task.

- `references/web.md`
- `references/ios.md`
- `references/android.md`
- `references/macos.md`
- `references/kotlin.md`
- `references/swift.md`
- `references/cross-cutting.md` — universal traps (timezones, encoding, floats, HTTP retries, race conditions, flaky tests). Read every time.

For **new feature work**, also read `references/pre-mortem-workflow.md` and `references/preempt-checklist.md`. They describe the discipline for preventing bugs before they happen — the pre-mortem is the most valuable 30 minutes you'll spend on any feature.

### 3. Read `DEBUG_LOG.md` if it exists

Lives at the project root. Skim titles. For anything whose prevention rule touches the area you're about to edit, read the entry in full. Name the applicable prevention rules in your plan.

If `DEBUG_LOG.md` doesn't exist, initialise it from `templates/DEBUG_LOG.template.md` with a `DL-000 — DEBUG_LOG started` seed entry. Or run `scripts/init.sh /path/to/your/project` to do this plus drop a stub `CLAUDE.md`.

### 4. State your plan before writing code (Think Before Coding)

Post a short plan in the chat first:

1. The user-visible goal of this change (one sentence).
2. The files you will touch and why.
3. The interfaces / contracts you will NOT change (blast-radius awareness).
4. The **prevention rules** from `DEBUG_LOG.md` and the catalogs that apply.
5. How you will verify the change works.

Skip only if the user explicitly says "just do it" or the change is purely cosmetic.

See `references/pre-mortem-workflow.md` for the expanded version of this workflow for new features.

---

## The DEBUG_LOG protocol

Append a numbered entry to `DEBUG_LOG.md` — **in the same commit as the fix** — for every one of:

- Build error (compile / transpile / bundle failure).
- Runtime crash, exception, or signal (NullPointerException, TypeError, SIGSEGV, Swift fatalError, panic).
- ANR / main-thread block / UI freeze.
- Logic bug (code ran; behaviour was wrong).
- Flaky test.
- Warning-as-error (e.g., a Sendable warning that surfaced a real concurrency bug).
- Performance regression.
- Production incident.

Even a five-minute typo fix gets an entry. Logging is cheap; rediscovering a subtle bug six months later is not.

### Entry template

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident |
| **Track** | web / ios / android / macos / kotlin / swift / cross-cutting |
| **File(s)** | `path/to/file.ext` |
| **Symptom** | What failed. Quote the error message. Include the relevant stack frame. |
| **Root Cause** | Why it happened. 1–3 sentences. Name the misconception — "what did I believe about this code that turned out to be wrong?" |
| **Fix** | What was changed. Commit SHA if available. |
| **Prevention Rule** | Imperative, specific, checkable. **Why:** one-liner. |
```

### The four non-negotiable rules

1. **Sequence.** Entries are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip, never reuse. Zero-pad to three digits; extend to four past `DL-999`.
2. **Never skip.** Every bug fix gets an entry, no matter how small. The "trivial typo" you don't log is the one that will come back as a recurring bug.
3. **Read before coding.** Skim `DEBUG_LOG.md` at the start of every non-trivial task. If you're about to edit a file that has entries pointing at it, read those entries in full and name their prevention rules in your plan.
4. **Append-only.** Never delete or modify an existing entry. If an entry turns out to be wrong, add a new one that cross-references: `> Supersedes DL-042. That analysis was incomplete because…`.

### Writing good prevention rules

The prevention rule is the only output of DL work that matters long-term. A rule is good when it is:

- **Specific** — names the API, pattern, or file it applies to.
- **Checkable** — a human or linter can verify whether you followed it.
- **Imperative** — it says what to do, not what to think about.
- **Carries why** — a one-line justification so future readers can judge edge cases.

| Weak rule | Strong rule |
|---|---|
| "Be careful with coroutines." | "Always call `SpeechRecognizer.startListening()` on the main thread; wrap the call in `withContext(Dispatchers.Main.immediate)` when the caller may be on IO. **Why:** the speech API silently drops the session if called from a worker thread (DL-023)." |
| "Don't break hydration." | "Never read `window`, `document`, `localStorage`, `Date.now()`, or `Math.random()` during React render in Next.js. Move them into `useEffect` or a client-only component. **Why:** SSR/CSR mismatch corrupts the hydration tree (DL-014)." |
| "Think about main thread." | "Never call `URLSession` handlers that touch `@Published` properties without hopping to `@MainActor` first; use `await MainActor.run { … }` or mark the caller `@MainActor`. **Why:** SwiftUI's publisher machinery is not thread-safe below iOS 17 (DL-031)." |

### Promoting rules

When the same prevention rule appears in **three or more** DL entries, promote it to `PREVENTION_RULES.md` — the project-level index of rules that have earned their place. Per-language starter templates live in `templates/PREVENTION_RULES.<track>.template.md`. If the rule can be encoded as a linter / CI check, do that too; ambient tooling beats ambient discipline.

---

## Examples

- `examples/example-DEBUG_LOG.md` — a filled-in DEBUG_LOG with worked entries across tracks.
- `examples/example-session.md` — a Claude session using this skill start-to-finish on a real feature.

## Templates

- `templates/DEBUG_LOG.template.md` — seed `DEBUG_LOG.md` for a new project.
- `templates/PREVENTION_RULES.template.md` — generic `PREVENTION_RULES.md` starter.
- `templates/PREVENTION_RULES.<track>.template.md` — per-language variants (web, ios, android, macos, kotlin, swift).

## Integrations

- `editor-integrations/CLAUDE.md` — sample project-level rules for Claude Code / Cowork.
- `editor-integrations/cursor/rules/debug-log.mdc` — Cursor rule file.
- `editor-integrations/AGENTS.md` — for Aider / Codex / OpenAI Agents.
- `github-actions/validate-debug-log.yml` + `validate_debug_log.py` — CI check for DEBUG_LOG format.
- `scripts/init.sh` — one-shot project initialiser.

---

## Philosophy — why this exists

Three assumptions power this skill:

**One: the best bug-fix is the one someone else already logged.** Every codebase accumulates invisible rules. New contributors rediscover them one crash at a time. A DEBUG_LOG makes the invisible rules visible, so the *second* person never hits the bug.

**Two: platforms leak.** The biggest category of bugs in modern apps is not "my code is wrong" but "the platform behaves in a way I didn't expect." Android 14's foreground service crash, SwiftUI's `@State` semantics inside `List`, React's effect cleanup timing — these are platform contracts you can learn by shipping a thousand apps, or by reading a catalog compiled from people who already did.

**Three: LLMs need ambient memory.** Claude and its peers are brilliant when given the right context at the right time. This skill gives them the context (the catalog), the discipline (the protocol), and the memory (the log). Every prevention rule you write is a bug a future session won't have to fix.

Good luck. Log your bugs.
