# AGENTS.md — sample

> Drop this file at the **root** of your project (not inside a subdirectory). If you already have an `AGENTS.md`, merge the `DEBUG_LOG discipline` section into it.
>
> `AGENTS.md` is the convention read by Aider, Codex CLI, OpenAI Agents SDK, and a growing number of other agent harnesses. The skill itself lives at `~/.claude/skills/debug-log/` or `tools/debug-log-skill/` (submodule). This file is the pointer.

---

## DEBUG_LOG discipline

This project follows the [debug-log-skill](https://github.com/<you>/debug-log-skill) protocol. When you (the agent) begin any non-trivial task, you are expected to:

1. Skim `DEBUG_LOG.md` at the project root for prior entries touching files you're about to edit.
2. Read `references/<track>.md` inside the skill folder for the track(s) applicable to this project, plus `references/cross-cutting.md` always.
3. For new features, also read `references/pre-mortem-workflow.md` and `references/preempt-checklist.md`.
4. State a plan that names the applicable prevention rules before writing code.

### The four non-negotiable rules

1. **Sequence.** Entries in `DEBUG_LOG.md` are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip. Never reuse a number.
2. **Never skip an entry.** Every bug fix — build error, runtime crash, logic bug, flaky test, warning-as-error, perf regression, incident — gets an entry in `DEBUG_LOG.md` in the same commit as the fix.
3. **Read before coding.** See step 1–4 above.
4. **Append-only.** Never delete or edit an existing entry. Supersede with a new entry that cross-references the old one.

### Tracks active in this project

Edit this list to reflect your stack (delete what doesn't apply):

- [ ] web — React / Next.js / TypeScript / Node
- [ ] ios — Swift / SwiftUI / UIKit
- [ ] android — Kotlin / Compose
- [ ] macos — Swift / AppKit
- [ ] kotlin — language-level (beyond Android)
- [ ] swift — language-level (beyond iOS/macOS)
- [x] cross-cutting — always on

### After fixing a bug

Before your commit lands:

1. Append a `DL-NNN` entry to `DEBUG_LOG.md` using the seven-field template below.
2. Write the prevention rule as imperative, specific, and checkable, with a **Why:** one-liner.
3. Stage `DEBUG_LOG.md` in the same commit as the fix.
4. If the same prevention rule now appears in three or more entries, promote it to `PREVENTION_RULES.md`.

### Entry template

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident |
| **Track** | web / ios / android / macos / kotlin / swift / cross-cutting |
| **File(s)** | `path/to/file.ext` |
| **Symptom** | What failed. Quote the error message. |
| **Root Cause** | Why. 1–3 sentences. Name the misconception. |
| **Fix** | What was changed. Commit SHA if available. |
| **Prevention Rule** | Imperative, specific, checkable. **Why:** one-liner. |
```

### Why this matters

Without this discipline, the same class of bug ships again six weeks later because the context evaporated. The log is the project's shared memory across humans and LLM sessions.
