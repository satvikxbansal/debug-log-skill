# AGENTS.md — sample

> Drop this file at the **root** of your project (not inside a subdirectory). If you already have an `AGENTS.md`, merge the `DEBUG_LOG discipline` section into it.
>
> `AGENTS.md` is the convention read by Aider, Codex CLI, OpenAI Agents SDK, and a growing number of other agent harnesses. The skill itself lives at `~/.claude/skills/debug-log/` or `tools/debug-log-skill/` (submodule). This file is the pointer.

---

## DEBUG_LOG discipline (v2.0)

This project follows the [debug-log-skill](https://github.com/<you>/debug-log-skill) protocol (v2.0 — active knowledge graph). When you (the agent) begin any non-trivial task, you are expected to:

1. Read `references/<track>.md` inside the skill folder for the track(s) applicable to this project, plus `references/cross-cutting.md` and `references/tag-taxonomy.md` always.
2. **Grep** `DEBUG_LOG.md` (do not read it end-to-end) for the filenames, tags, or Root Cause Categories relevant to this task. See patterns below.
3. For new features, also read `references/pre-mortem-workflow.md` and `references/preempt-checklist.md`.
4. State a plan that names the applicable prevention rules by DL number before writing code.

### The four non-negotiable rules

1. **Sequence.** Entries in `DEBUG_LOG.md` are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip. Never reuse.
2. **Never skip an entry.** Every bug fix — build error, runtime crash, logic bug, flaky test, warning-as-error, perf regression, incident — gets an entry in `DEBUG_LOG.md` in the same commit as the fix.
3. **Active pre-flight.** Grep the log for the specific file, tag, or category. Do not load the whole log into context.
4. **Append-only.** Never delete or edit an existing entry. When an entry becomes obsolete, prepend `[OBSOLETE]` to its title line and supersede it with a new entry.

### Active pre-flight — grep patterns

```bash
# By file path (strongest signal)
grep -niE "path/to/File\.ext" DEBUG_LOG.md

# By tag (see references/tag-taxonomy.md)
grep -niE "#Compose|#StateFlow" DEBUG_LOG.md

# By Root Cause Category
grep -niE "Race Condition|Scope Leak|LLM Hallucination" DEBUG_LOG.md
```

### Tracks active in this project

Edit the list to reflect your stack:

- [ ] web — React / Next.js / TypeScript / Node
- [ ] ios — Swift / SwiftUI / UIKit
- [ ] android — Kotlin / Compose
- [ ] macos — Swift / AppKit
- [ ] kotlin — language-level
- [ ] swift — language-level
- [x] cross-cutting — always on

### After fixing a bug

Before your commit lands:

1. Append a `DL-NNN` entry to `DEBUG_LOG.md` using the v2.0 template below.
2. Fill **Tags** (track + semantic), **Environment** (SDK versions), and **Root Cause Category** (from the closed list).
3. Record **Iterations** honestly. `5+` is a signal that your model of the system is wrong; reflect on which assumption kept failing.
4. Write the prevention rule as imperative, specific, checkable, with a **Why:** one-liner.
5. Stage `DEBUG_LOG.md` in the same commit as the fix.
6. If the rule now appears in three or more active entries, promote it to `PREVENTION_RULES.md`.

### Entry template (v2.0)

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Tags** | `#track-tag #semantic-tag [#more]` |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident |
| **Environment** | Relevant SDK / library / OS versions |
| **File(s)** | `path/to/file.ext` |
| **Symptom** | What failed. Quote the error. |
| **Root Cause Category** | One of: API Change / API Deprecation / Race Condition / Scope Leak / Main Thread Block / Hydration Mismatch / Null or Unchecked Access / Type Coercion / Off-By-One / Syntax Error / Config or Build / Test Infrastructure / LLM Hallucination or Assumption / Other |
| **Root Cause Context** | Why. 1–3 sentences. Name the misconception. |
| **Fix** | What changed. Commit SHA. |
| **Iterations** | Integer. `0` = first try. `5+` = investigate the loop. |
| **Prevention Rule** | Imperative, specific, checkable. **Why:** one-liner. |
```

### Why this matters

Without this discipline, the same class of bug ships again six weeks later because the context evaporated. The log is the project's shared memory across humans and LLM sessions. The active grep keeps the memory *retrievable* as the log grows past 100 entries. The Root Cause Category taxonomy turns the log into a countable signal — if 40% of your entries are `LLM Hallucination or Assumption`, your agent setup needs stronger grounding.
