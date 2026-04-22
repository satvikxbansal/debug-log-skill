# CLAUDE.md — sample

> Drop this file at the **root** of your project. If you already have a `CLAUDE.md`, merge the `DEBUG_LOG discipline` section into it.
>
> This is a sample. The real skill lives at `~/.claude/skills/debug-log-skill/` (or `.claude/skills/debug-log-skill/` for project-scope). This file is the pointer that activates the discipline in agent sessions.

---

## DEBUG_LOG discipline (v2.0)

This project follows the [debug-log-skill](https://github.com/<you>/debug-log-skill) protocol (v2.0 — active knowledge graph). Before any non-trivial task, and after every bug fix, obey the rules below.

### The four non-negotiable rules

1. **Sequence.** Entries in `DEBUG_LOG.md` are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip. Never reuse.
2. **Never skip.** Every bug fix — build error, runtime crash, logic bug, flaky test, perf regression, incident — gets a `DL-NNN` entry in the same commit as the fix.
3. **Active pre-flight, not passive skim.** Before editing any file, **grep** `DEBUG_LOG.md` for the filename, relevant tags, or Root Cause Category. Read only the entries that match. Do not load the whole log into context.
4. **Append-only.** Never delete or edit an existing entry. When an entry becomes obsolete, prepend `[OBSOLETE]` to its title line (the only permitted mutation) and add a superseding entry that explains the change.

### Active pre-flight — the grep patterns

Run at least one before editing:

```bash
# By file path (strongest signal)
grep -niE "path/to/File\.ext" DEBUG_LOG.md

# By tag (semantic grouping — see references/tag-taxonomy.md in the skill)
grep -niE "#Compose|#StateFlow" DEBUG_LOG.md

# By Root Cause Category (the 14 canonical categories)
grep -niE "Race Condition|Scope Leak|LLM Hallucination" DEBUG_LOG.md
```

Read only the entries grep surfaces plus those they cross-reference (`Supersedes DL-XXX` / `See DL-XXX`).

### Tracks active in this project

Edit the checkbox list. Delete rows that don't apply.

- [ ] web — React / Next.js / TypeScript / Node
- [ ] ios — Swift / SwiftUI / UIKit
- [ ] android — Kotlin / Compose
- [ ] macos — Swift / AppKit
- [ ] kotlin — language-level
- [ ] swift — language-level
- [x] cross-cutting — always on

### After fixing a bug

1. Append a `DL-NNN` entry to `DEBUG_LOG.md` using the v2.0 template below.
2. Record the **Iterations** count honestly. `5+` triggers a mandatory reflection on the wrong assumption you kept making.
3. Write the prevention rule as imperative, specific, checkable, with a **Why:** one-liner.
4. Stage `DEBUG_LOG.md` in the same commit as the fix.
5. If the same rule now appears in three or more active (non-`[OBSOLETE]`) entries, promote it to `PREVENTION_RULES.md`.

### Entry template (v2.0)

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Tags** | `#track-tag #semantic-tag [#more]` — at least one track tag + one semantic tag |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident (or extended: Informational, Runtime Warning, UX Regression, Security) |
| **Environment** | Relevant SDK / library / OS versions |
| **File(s)** | `path/to/file.ext` |
| **Symptom** | What failed. Quote the error. |
| **Root Cause Category** | One of the 14 canonical categories (see tag-taxonomy.md) |
| **Root Cause Context** | Why. 1–3 sentences. Name the misconception. |
| **Fix** | What changed. Commit SHA if available. |
| **Iterations** | Integer. `0` = first try. `5+` = investigate the loop. |
| **Prevention Rule** | Imperative, specific, checkable. **Why:** one-liner. |
```

### Root Cause Categories (closed list)

`API Change` · `API Deprecation` · `Race Condition` · `Scope Leak` · `Main Thread Block` · `Hydration Mismatch` · `Null or Unchecked Access` · `Type Coercion` · `Off-By-One` · `Syntax Error` · `Config or Build` · `Test Infrastructure` · `LLM Hallucination or Assumption` · `Other`

### Why this matters

Without this discipline, the same class of bug ships again six weeks later because the context evaporated. The log is the project's shared memory across humans and LLM sessions. The active grep keeps the memory *retrievable* as the log grows past 100 entries.
