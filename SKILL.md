---
name: debug-log
description: Engineer-grade debugging discipline for any codebase. Invoke this skill before writing code on any non-trivial task AND every time you fix a bug, crash, build error, UI regression, flaky test, or unexpected behaviour. It enforces a structured `DEBUG_LOG.md` protocol, a "think before coding" pre-flight, and a pre-mortem catalog of frequently-encountered traps in web (React / Next.js / Node / TypeScript), iOS (Swift / SwiftUI / UIKit), Android (Kotlin / Compose), and macOS (Swift / AppKit / SwiftUI) codebases. Use this skill whenever the user mentions debugging, crashes, errors, "it's not working", "why is this broken", "the build is failing", "this test is flaky", "fix this bug", stack traces, exception types (NullPointerException, TypeError, SIGSEGV, fatal error), or when starting new implementation work in any of the supported tracks so prevention rules from prior bugs are read first.
---

# Debug Log Skill

This skill does two things, and they reinforce each other:

1. It enforces a **debugging discipline** — a `DEBUG_LOG.md` file at the root of the project that captures every bug with a structured, searchable, appendable entry. Numbered sequentially. Read before coding. Never skipped. The log exists so that tomorrow's engineer (including tomorrow's Claude) doesn't rediscover yesterday's mistake.

2. It provides a **pre-mortem error catalog** — the real, frequently-encountered traps in each supported tech stack, with symptom / root cause / fix / prevention-rule for each. The catalog lets you anticipate a class of bugs before they happen, not just react after.

Both halves share a single conviction: **the most valuable debugging work is the debugging you never had to do, because you'd seen the pattern before.** This skill is how you bank that pattern recognition across sessions, across people, and across platforms.

---

## When this skill loads, do these things in order

### 1. Determine the track(s) this project uses

Look at the project root. Identify which of the following apply (more than one is normal — e.g. a Kotlin Multiplatform project is Android + iOS + Kotlin + Swift):

- **web** — presence of `package.json`, `next.config.*`, `vite.config.*`, `tsconfig.json`, React/Vue/Svelte dependencies.
- **ios** — presence of `*.xcodeproj`, `*.xcworkspace`, `Info.plist`, `Podfile`, `Package.swift` with iOS targets, `*.swift` files.
- **android** — presence of `build.gradle.kts`, `settings.gradle.kts`, `AndroidManifest.xml`, `*.kt` files in `app/`, `compileSdk` declarations.
- **macos** — similar to iOS but with AppKit references, `.entitlements` with hardened-runtime, menu-bar / `NSWindow` / `MenuBarExtra` code.
- **kotlin** — any Kotlin beyond Android (JVM, KMP, server) — coroutines, Flow, kotlinx.serialization.
- **swift** — any Swift beyond iOS/macOS — async/await, Sendable, SwiftPM packages.

You may pick more than one. Pick all that apply.

### 2. Read the matching reference(s)

For each track identified above, read the corresponding `references/<track>.md` before you write code. These files catalog the bugs that actually recur in that stack — the ones that senior engineers learn to smell. Skim the titles; read the entries whose symptoms match the current task.

The reference files are keyed by track:

- `references/web.md`
- `references/ios.md`
- `references/android.md`
- `references/macos.md`
- `references/kotlin.md`
- `references/swift.md`
- `references/cross-cutting.md` — universal traps (timezones, encoding, floats, HTTP retries, race conditions, flaky tests). Read this every time, regardless of track.

For a new feature (not a bug fix), also read `references/preempt-checklist.md` — a per-track pre-mortem list of ~10-12 questions to ask before starting.

### 3. Read `DEBUG_LOG.md` if it exists

The file lives at the project root. Skim the titles. For anything whose prevention rule touches the area you're about to edit, read the full entry. Call out in your plan which prevention rules apply.

If `DEBUG_LOG.md` doesn't exist, create it by copying `templates/DEBUG_LOG.template.md` into the project root and initialise with `DL-000 — DEBUG_LOG started`.

### 4. State your plan before writing code (Think Before Coding)

Before you edit any file, post a short plan in the chat containing:

1. The user-visible goal of this change (one sentence).
2. The files you will touch and why (bullet list).
3. The interfaces / contracts you will NOT change (to prove you understand the blast radius).
4. The **prevention rules** from `DEBUG_LOG.md` and the reference catalogs that apply.
5. How you will verify the change works (tests, manual checks, logs).

This five-item plan is the discipline. Skipping it is where most preventable bugs come from — rushing to code produces tangled diffs, hidden coupling, and regressions that show up two commits later. Ten seconds of planning prevents an hour of debugging.

Skip only if the user explicitly says "just do it" or the change is purely cosmetic (fixing a typo in a comment).

---

## The DEBUG_LOG protocol — the part you will use most often

Every time you fix **any** of the following, you append a numbered entry to `DEBUG_LOG.md` at the project root **in the same commit as the fix**:

- Build error (the project wouldn't compile, transpile, or bundle).
- Runtime crash, exception, or signal (NullPointerException, TypeError, SIGSEGV, Swift fatalError, panic).
- ANR / main-thread block / UI freeze.
- Logic bug (code compiled and ran, but the behaviour was wrong).
- Flaky test (sometimes passed, sometimes failed, same code).
- Warning you had to treat as an error (e.g., a Sendable warning that surfaced a real concurrency bug).
- Performance regression (something got slower in a measurable way).
- Production incident (alert fired, user-visible issue).

Even a one-character typo that cost you five minutes gets an entry. The cost of logging is tiny; the cost of rediscovering a subtle bug six months later is huge.

### Entry template

Copy this exactly. The column widths don't matter; the field names do.

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident |
| **Track** | web / ios / android / macos / kotlin / swift / cross-cutting |
| **File(s)** | `path/to/file.ext` (relative to project root) |
| **Symptom** | What the user saw or what failed. Quote the error message. Include the stack frame that fired if you have it. |
| **Root Cause** | Why it happened. 1–3 sentences. Name the misconception, not just the line. A good root cause answers "what did I believe about this code that turned out to be wrong?" |
| **Fix** | What was changed. Reference the commit SHA if available. |
| **Prevention Rule** | An imperative, checkable rule that would have prevented this. Specific, not generic. (See "Writing good prevention rules" below.) |
```

### The four non-negotiable rules

1. **Sequence.** Entries are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip a number. Never reuse a number. Zero-pad to at least three digits for sort order; extend to four when you pass `DL-999`.
2. **Never skip.** Every bug fix gets an entry, no matter how small. The "trivial typo" you don't log is the one that will come back as a recurring bug.
3. **Read before coding.** At the start of every non-trivial coding task, skim `DEBUG_LOG.md` and name the prevention rules that apply in your plan. If you're about to edit a file that has entries pointing at it, read those entries in full.
4. **Append-only.** Never delete or modify an existing entry. If an entry turns out to be wrong or superseded, add a new one that cross-references the old: `> Supersedes DL-042. That analysis was incomplete because…`.

### Writing good prevention rules

A prevention rule is the only output of DL work that matters long-term. The symptom and fix describe a bug; the prevention rule prevents a class of bugs. Spend the most effort on this field.

A good rule is:

- **Specific** — it names the API, pattern, or file it applies to.
- **Checkable** — a human or linter can verify whether you followed it.
- **Imperative** — it says what to do, not what to think about.
- **Carries "why"** — a one-line justification so future readers can judge edge cases instead of blindly following.

| Weak rule | Strong rule |
|---|---|
| "Be careful with coroutines." | "Always call `SpeechRecognizer.startListening()` on the main thread; wrap the call in `withContext(Dispatchers.Main.immediate)` when the caller may be on IO. Why: the speech API silently drops the session if called from a worker thread (DL-023)." |
| "Don't break hydration." | "Never read `window`, `document`, `localStorage`, `Date.now()`, or `Math.random()` during React render in Next.js. Move them into `useEffect` or a client-only component. Why: SSR/CSR mismatch corrupts the hydration tree and produces invisible state bugs (DL-014)." |
| "Think about main thread." | "Never call `URLSession` handlers that touch `@Published` properties without hopping to `@MainActor` first; use `await MainActor.run { … }` or mark the caller `@MainActor`. Why: SwiftUI's publisher machinery is not thread-safe below iOS 17 (DL-031)." |

### When a prevention rule appears three or more times across DL entries

Promote it. Move the rule out of `DEBUG_LOG.md` and into a project-level rule file (`.cursor/rules/`, `CLAUDE.md`, `AGENTS.md`, or whatever your team uses). A rule that keeps getting violated is a signal the pattern is implicit in the codebase and needs to become ambient guidance.

---

## Pre-mortem workflow — before a new feature

For **new work** (not bug fixes), the skill's job is to prevent bugs, not react to them. The workflow is:

1. Identify the track(s) (step 1 above).
2. Open `references/<track>.md` for each and scan the section titles. Read the entries whose names touch the feature area (e.g., starting Compose work? Read the "State hoisting" and "Recomposition loop" entries).
3. Open `references/preempt-checklist.md` and work through the relevant track's 10–12 pre-mortem questions. For each question, answer it in the design before you start coding. Flag any "I'm not sure" answers — those are the most likely future bugs.
4. If the feature lands near a `DEBUG_LOG.md` prevention rule, name it in your plan.
5. Start coding.

The pre-mortem catalog is not theory. It is the distilled scar tissue from real shipping codebases. Treat it with the seriousness you'd give a senior colleague's code review.

---

## Examples

- `examples/example-DEBUG_LOG.md` — a filled-in DEBUG_LOG with 6 worked entries across tracks, showing the shape of a good entry.
- `examples/example-session.md` — a walkthrough of a Claude session using this skill start-to-finish on a real bug.

---

## Templates (copy into your project)

- `templates/DEBUG_LOG.template.md` — the file to drop at your project root. Contains `DL-000` seed entry and the header block.
- `templates/PREVENTION_RULES.template.md` — an optional summary document a team maintains alongside `DEBUG_LOG.md`, indexing the prevention rules that matter most.

---

## Philosophy — why this exists

Three assumptions power this skill:

**One: the best bug-fix is the one someone else already logged.** Every codebase accumulates invisible rules — "don't call X from Y", "watch out for Z on Android 14". New contributors rediscover them one crash at a time. A DEBUG_LOG makes the invisible rules visible, so the *second* person never hits the bug.

**Two: platforms leak.** The biggest category of bugs in modern apps is not "my code is wrong" but "the platform behaves in a way I didn't expect." Android 14's foreground service crash, SwiftUI's `@State` semantics inside `List`, React's effect cleanup timing, the `FLAG_SECURE` black-bitmap behaviour — these are platform contracts you can either learn by shipping a thousand apps, or by reading a reference catalog compiled from people who already did. This skill is the second option.

**Three: LLMs need ambient memory.** Claude and its peers are brilliant when given the right context at the right time. This skill gives them the context (the catalog), the discipline (the protocol), and the memory (the log) to produce code that is first-time-correct far more often than it would be without. The productivity win compounds: every prevention rule you write is a bug a future session won't have to fix.

If you want to understand why a particular decision in this skill was made, read `references/preempt-checklist.md` — most of the questions there are the distilled form of a story someone lived.

Good luck. Log your bugs.
