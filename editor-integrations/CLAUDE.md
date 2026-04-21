# CLAUDE.md — sample

> Drop this file at the **root** of your project (not inside a subdirectory) and rename it if it's already present — or merge the `DEBUG_LOG discipline` section into your existing CLAUDE.md.

---

## DEBUG_LOG discipline

This project follows the [debug-log-skill](https://github.com/<you>/debug-log-skill) protocol. The skill lives at `~/.claude/skills/debug-log/` (user-scope) or `.claude/skills/debug-log/` (project-scope). Its SKILL.md is the source of truth; this file is the project-level pointer.

### The four non-negotiable rules

1. **Sequence.** Entries in `DEBUG_LOG.md` are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip. Never reuse.
2. **Never skip.** Every bug fix — build error, runtime crash, ANR, logic bug, flaky test, warning-as-error, perf regression, incident — gets an entry in `DEBUG_LOG.md` in the same commit as the fix.
3. **Read before coding.** At the start of any non-trivial task, skim `DEBUG_LOG.md` and the relevant `references/<track>.md` from the skill. Name applicable prevention rules in your plan.
4. **Append-only.** Never delete or edit an existing entry. Supersede with a new entry that cross-references the old.

### Tracks active in this project

Edit this list to reflect your stack (delete what doesn't apply):

- [ ] web — React / Next.js / TypeScript / Node
- [ ] ios — Swift / SwiftUI / UIKit
- [ ] android — Kotlin / Compose
- [ ] macos — Swift / AppKit
- [ ] kotlin — language-level (beyond Android)
- [ ] swift — language-level (beyond iOS/macOS)
- [x] cross-cutting — always on

### Workflow

**Before coding any non-trivial change:**

1. Identify the track(s) above.
2. Read `DEBUG_LOG.md` at the project root — skim titles, read any entry whose prevention rule touches the file you're about to edit.
3. Read `references/<track>.md` from the skill folder for your track(s), plus `references/cross-cutting.md` always.
4. For new features: also work through `references/preempt-checklist.md` and `references/pre-mortem-workflow.md`.
5. State a plan: goal, files touched, interfaces preserved, applicable prevention rules, verification approach.

**After fixing a bug, before committing:**

1. Append a `DL-NNN` entry to `DEBUG_LOG.md` using the seven-field template.
2. The prevention rule is the most important field — make it specific, checkable, imperative, and carry a **Why:** one-liner.
3. Stage `DEBUG_LOG.md` in the same commit as the fix.

### Promoting rules

When the same prevention rule appears in three or more DEBUG_LOG entries, promote it to `PREVENTION_RULES.md` (and potentially to a linter / CI check). Keep `PREVENTION_RULES.md` short — it's an index of rules that have earned their place.

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
