---
name: debug-log-skill
description: Engineer-grade debugging discipline for any codebase. Invoke this skill before writing code on any non-trivial task AND every time you fix a bug, crash, build error, UI regression, flaky test, or unexpected behaviour. It enforces a structured `DEBUG_LOG.md` protocol, an *active pre-flight* grep-based retrieval of applicable prevention rules, a "think before coding" five-item plan, and a pre-mortem catalog of frequently-encountered traps in web (React / Next.js / Node / TypeScript), iOS (Swift / SwiftUI / UIKit), Android (Kotlin / Compose), and macOS (Swift / AppKit / SwiftUI) codebases. Use this skill whenever the user mentions debugging, crashes, errors, "it's not working", "why is this broken", "the build is failing", "this test is flaky", "fix this bug", stack traces, exception types (NullPointerException, TypeError, SIGSEGV, fatal error), or when starting new implementation work in any of the supported tracks so prevention rules from prior bugs are retrieved first.
---

# Debug Log Skill — v2.0

This skill turns `DEBUG_LOG.md` into an **active knowledge graph**. Every bug produces a tagged, categorised, environment-stamped, iteration-counted entry. Before writing code, you *query* the log with a grep — you do not read it end-to-end. When rules go stale, you mark them `[OBSOLETE]` and supersede them. Over time the log becomes the single highest-signal document in the repo.

Three assumptions power the skill:

1. **The best bug-fix is the one someone else already logged.** New contributors rediscover invisible rules one crash at a time. A DEBUG_LOG makes the rules visible; the active pre-flight makes them *retrievable*.
2. **Platforms leak.** Most bugs are not "my code is wrong" — they are "the platform behaved in a way I didn't expect." The reference catalogs pre-bank that pattern recognition.
3. **LLMs need ambient memory and active retrieval.** Context windows fill fast. Skimming a 100-entry log is expensive and noisy. Targeted grep is cheap and precise. Every prevention rule you write is a bug a future session won't have to fix.

---

## When this skill loads, do these things in order

### 1. Determine the track(s) this project uses

Look at the project root. Identify which apply (more than one is normal):

- **web** — `package.json`, `next.config.*`, `vite.config.*`, React/Vue/Svelte deps.
- **ios** — `*.xcodeproj`, `*.xcworkspace`, `Info.plist`, `Podfile`, `Package.swift` with iOS targets.
- **android** — `build.gradle.kts`, `AndroidManifest.xml`, `*.kt` in `app/`, `compileSdk` declarations.
- **macos** — AppKit references, `.entitlements` with hardened-runtime, `NSWindow` / `MenuBarExtra` code.
- **kotlin** — any Kotlin beyond Android (JVM, KMP, server).
- **swift** — any Swift beyond iOS/macOS (async/await, Sendable, SwiftPM).

Pick all that apply.

### 2. Read the matching reference(s)

For each track, read `references/<track>.md`. Skim titles; read in full the entries whose symptoms match the current task.

- `references/web.md`, `references/ios.md`, `references/android.md`, `references/macos.md`, `references/kotlin.md`, `references/swift.md`
- `references/cross-cutting.md` — universal traps. Read every time.
- `references/tag-taxonomy.md` — the canonical Tag list and Root Cause Category list. Load it once per session so your entries and queries speak the same vocabulary.

For **new feature work**, also read `references/pre-mortem-workflow.md` and `references/preempt-checklist.md`.

### 3. Active pre-flight — grep `DEBUG_LOG.md` before editing

**Do not read `DEBUG_LOG.md` end-to-end.** The log grows without bound; reading it in full burns context and buries the relevant rule in noise. Instead, before you edit any file, run targeted searches:

```bash
# By file path (strongest signal — we have shipped a bug in this exact file)
grep -niE "path/to/File\.ext" DEBUG_LOG.md

# By tag (semantic grouping — anything involving Compose state, say)
grep -niE "#Compose|#StateFlow" DEBUG_LOG.md

# By library / dependency / API name
grep -niE "Room|startForeground|useEffect" DEBUG_LOG.md

# By Root Cause Category
grep -niE "Race Condition|Scope Leak|LLM Hallucination" DEBUG_LOG.md
```

Read **only** the entries the grep surfaces, plus any entries they cross-reference via `Supersedes DL-XXX` or `See DL-XXX`. If zero results come back and the feature area is non-trivial, widen the grep (by track, by component, by broader tag) before falling back to a full skim.

When you state your plan (step 4), list the DL numbers your grep returned and the prevention rules from them that apply.

### 4. State your plan before writing code

Post a short plan in the chat:

1. **Goal** — one sentence of user-visible behaviour.
2. **Files touched** — bullet list with a one-line reason each.
3. **Interfaces preserved** — contracts you will NOT change.
4. **Applicable prevention rules** — the DL numbers your grep surfaced, quoted with a one-line applicability note.
5. **Verification** — how you will know it works (test, manual check, log line).

Skip only if the user explicitly says "just do it" or the change is purely cosmetic.

See `references/pre-mortem-workflow.md` for the expanded version applied to new features.

---

## The DEBUG_LOG protocol — v2.0 template

Append a numbered entry to `DEBUG_LOG.md` **in the same commit as the fix** for every one of:

- Build error (compile / transpile / bundle failure)
- Runtime crash, exception, or signal
- ANR / main-thread block / UI freeze
- Logic bug (ran, but behaviour was wrong)
- Flaky test
- Warning-as-error (a lint or compiler warning that surfaced a real bug)
- Performance regression
- Production incident

Even a five-minute typo fix gets an entry. Logging is cheap; rediscovering a subtle bug six months later is not.

### Entry template (v2.0)

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Tags** | `#Tag1 #Tag2 #Tag3` (see references/tag-taxonomy.md — at least one track tag + one semantic tag) |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident (plus: Informational, Runtime Warning, UX Regression, Security — see below) |
| **Environment** | Relevant SDK / library / OS versions (e.g., `Compose 1.7.2, Kotlin 2.0.0, Android API 34`) |
| **File(s)** | `path/to/file.ext` (relative to project root; list all touched) |
| **Symptom** | What failed. Quote the error message. Include the relevant stack frame if known. |
| **Root Cause Category** | One of: API Change / API Deprecation / Race Condition / Scope Leak / Main Thread Block / Hydration Mismatch / Null or Unchecked Access / Type Coercion / Off-By-One / Syntax Error / Config or Build / Test Infrastructure / LLM Hallucination or Assumption / Other (see references/tag-taxonomy.md) |
| **Root Cause Context** | Why it happened. 1–3 sentences. Name the misconception — "what did I believe about this code that turned out to be wrong?" |
| **Fix** | What changed. Be specific about the logic change. Commit SHA if available. |
| **Iterations** | Integer. How many agent/human turns it took to land a correct fix. `0` = first try. `5+` is a signal to reflect on *why* — often a deep hallucination loop. |
| **Prevention Rule** | Imperative, specific, checkable. **Why:** one-liner. |
```

### Severity vocabulary

Eight **core severities** cover almost every entry: `Build Error`, `Runtime Crash`, `ANR`, `Logic Bug`, `Flaky Test`, `Warning-as-Error`, `Perf Regression`, `Incident`. Four **extended severities** are also accepted by the validator for the minority cases that don't fit the core set: `Informational` (seed rows, meta entries), `Runtime Warning` (warnings that surfaced a latent bug without a crash), `UX Regression` (visible-to-the-user but not a crash), `Security` (security-motivated fix without a crash). Pick the most specific label; when in doubt, prefer a core severity.

### The four non-negotiable rules

1. **Sequence.** Entries are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip, never reuse. Zero-pad to three digits; extend to four past `DL-999`.
2. **Never skip.** Every bug fix gets an entry, no matter how small.
3. **Active pre-flight, not passive skim.** Grep the log for files/tags/categories before editing (step 3 above). Read only what matches.
4. **Append-only.** Never delete or modify an existing entry. If a rule becomes obsolete, supersede it (see *Rule lifecycle* below).

### Tags — the semantic index

Tags are what make the log searchable. Every entry carries **at least two tags**:

- **1–2 track tags** from: `#web #ios #android #macos #kotlin #swift #cross-cutting`. Use two only when the bug genuinely spans stacks.
- One or more **semantic tags** from `references/tag-taxonomy.md` (e.g., `#Compose`, `#StateFlow`, `#Hydration`, `#Permissions`, `#URLSession`).

Prefer tags from the taxonomy. If you need a new tag, add it to `references/tag-taxonomy.md` in the same commit — a one-off tag that only appears once helps nobody.

### Root Cause Category — the meta-index

The Root Cause Category is a short, closed-vocabulary label on the *kind* of mistake. It lives alongside the free-text Root Cause Context. Over time, counting categories tells you where the codebase (or the LLM) keeps slipping — e.g., "42% of DL entries are Race Conditions" is a loud signal to invest in a concurrency story.

Canonical categories (see `references/tag-taxonomy.md` for definitions and examples):

`API Change` · `API Deprecation` · `Race Condition` · `Scope Leak` · `Main Thread Block` · `Hydration Mismatch` · `Null or Unchecked Access` · `Type Coercion` · `Off-By-One` · `Syntax Error` · `Config or Build` · `Test Infrastructure` · `LLM Hallucination or Assumption` · `Other`

Use `Other` only as a last resort, and in that case describe the category in one noun phrase in the Root Cause Context so future entries can promote it.

### Iterations — the struggle counter

The Iterations field captures how many attempts it took to land the fix. Record honestly:

- `0` — first attempt worked.
- `1–2` — one or two revisions (typical).
- `3–4` — considerable trial-and-error; the bug was genuinely tricky or you held a wrong model of the system.
- `5+` — investigate. This is almost always a deep hallucination loop, a missing piece of context, or a flawed mental model. The prevention rule for a 5+ iteration fix should usually name *the wrong assumption you kept re-making*, not just the code fix.

When running as an LLM agent, treat an Iteration count ≥ 3 as a mandatory reflection trigger: before closing the entry, write one extra sentence in Root Cause Context explaining which reasoning step kept failing, and why.

### Rule lifecycle — `[OBSOLETE]` and supersede

Codebases evolve. A rule written for Compose 1.5 may be moot after upgrading to Compose 1.7. When you realise a prior prevention rule no longer applies:

1. Do **not** delete or edit the old entry.
2. Append a new DL entry whose **Fix** explains the architectural change that retired the rule, and whose **Prevention Rule** captures the new invariant (if any).
3. In the old entry's **Title** field, prepend `[OBSOLETE]`. This is the only permitted mutation to an existing entry — purely a tombstone flag.
4. Add `> Supersedes DL-XXX. Reason: …` as the first line of the new entry's body.

The validator treats `[OBSOLETE]` entries specially: they do not count for active prevention-rule retrieval, but they remain in the sequence and in the history.

### Writing good prevention rules

A rule is good when it is:

- **Specific** — names the API, pattern, or file it applies to.
- **Checkable** — a human or linter can verify it.
- **Imperative** — says what to do, not what to think about.
- **Carries why** — one-line justification for edge cases.

| Weak rule | Strong rule |
|---|---|
| "Be careful with coroutines." | "Always call `SpeechRecognizer.startListening()` on the main thread; wrap in `withContext(Dispatchers.Main.immediate)` when the caller may be on IO. **Why:** the speech API silently drops the session from a worker thread (DL-023)." |
| "Don't break hydration." | "Never read `window`, `document`, `localStorage`, `Date.now()`, or `Math.random()` during React render in Next.js. Move into `useEffect` or a client-only component. **Why:** SSR/CSR mismatch corrupts the hydration tree (DL-014)." |
| "Think about main thread." | "Never call `URLSession` handlers that touch `@Published` properties without hopping to `@MainActor` first; use `await MainActor.run { … }` or mark the caller `@MainActor`. **Why:** SwiftUI's publisher machinery is not thread-safe below iOS 17 (DL-031)." |

### Promoting rules

When the same prevention rule appears in **three or more** DL entries (count non-`[OBSOLETE]` entries only), promote it to `PREVENTION_RULES.md`. Per-language starter templates live in `templates/PREVENTION_RULES.<track>.template.md`. If the rule can be encoded as a linter / CI check, do that too — ambient tooling beats ambient discipline.

---

## Examples

- `examples/example-DEBUG_LOG.md` — a filled-in DEBUG_LOG with worked v2.0 entries across tracks.
- `examples/example-session.md` — a Claude session using this skill start-to-finish, including the active pre-flight grep.

## Templates

- `templates/DEBUG_LOG.template.md` — seed `DEBUG_LOG.md` for a new project (v2.0 format).
- `templates/PREVENTION_RULES.template.md` — generic `PREVENTION_RULES.md` starter.
- `templates/PREVENTION_RULES.<track>.template.md` — per-language variants.

## Integrations

- `editor-integrations/CLAUDE.md` — sample project rules for Claude Code / Cowork.
- `editor-integrations/cursor/rules/debug-log.mdc` — Cursor rule file.
- `editor-integrations/AGENTS.md` — for Aider / Codex / OpenAI Agents.
- `github-actions/validate-debug-log.yml` + `validate_debug_log.py` — CI check for DEBUG_LOG format (v2.0).
- `scripts/init.sh` — one-shot project initialiser.

Good luck. Log your bugs.
