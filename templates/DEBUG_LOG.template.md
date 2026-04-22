# DEBUG_LOG

> Log of every bug fixed in this repository — build errors, runtime crashes, ANRs, logic bugs, flaky tests, perf regressions, and production incidents.
>
> This log is maintained under the `debug-log-skill` protocol (v2.0). See [`SKILL.md`](https://github.com/YOUR_ORG/debug-log-skill) for the full rules.

## Tracks active in this project

<!-- Edit this list to reflect your project. The skill reads this to decide which reference catalogs to consult. -->

- [ ] web
- [ ] ios
- [ ] android
- [ ] macos
- [ ] kotlin
- [ ] swift
- [x] cross-cutting (always on)

## The four non-negotiable rules

1. **Sequence** — entries are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip. Never reuse.
2. **Never skip** — every bug fix gets an entry, no matter how small.
3. **Active pre-flight** — before editing any file, **grep this log** for the filename, tags, or Root Cause Category that apply. Do not skim end-to-end.
4. **Append-only** — never delete or edit an existing entry. If an entry becomes obsolete, prepend `[OBSOLETE]` to its title and add a superseding entry.

## Active pre-flight — the grep patterns

Run at least one of these before editing any file:

```bash
# By file path (strongest signal)
grep -niE "path/to/File\.ext" DEBUG_LOG.md

# By tag (semantic grouping — see references/tag-taxonomy.md)
grep -niE "#Compose|#StateFlow" DEBUG_LOG.md

# By Root Cause Category
grep -niE "Race Condition|Scope Leak|LLM Hallucination" DEBUG_LOG.md
```

Read only the entries grep surfaces, plus any they cross-reference.

## Entry template (v2.0)

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Tags** | `#track-tag #semantic-tag [#more]` — at least one track tag + one semantic tag (see references/tag-taxonomy.md) |
| **Severity** | Core: Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident · Extended: Informational / Runtime Warning / UX Regression / Security |
| **Environment** | Relevant SDK / library / OS versions (e.g., `Compose 1.7.2, Kotlin 2.0.0, Android API 34`) |
| **File(s)** | `path/to/file.ext` (relative to repo root; list all touched) |
| **Symptom** | What failed. Quote the error, include the firing stack frame. |
| **Root Cause Category** | One of the 14 canonical categories (see references/tag-taxonomy.md) |
| **Root Cause Context** | Why it happened. 1–3 sentences. Name the misconception. |
| **Fix** | What was changed. Commit SHA if available. |
| **Iterations** | Integer. `0` = first try. `5+` = investigate the reasoning loop. |
| **Prevention Rule** | Imperative, checkable, specific. **Why:** one-liner. |
```

---

## Entries

### DL-000 — DEBUG_LOG started

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD <!-- fill in when you initialise --> |
| **Tags** | `#cross-cutting #Logging` |
| **Severity** | Informational |
| **Environment** | N/A |
| **File(s)** | `DEBUG_LOG.md` |
| **Symptom** | N/A |
| **Root Cause Category** | Other |
| **Root Cause Context** | N/A — seed entry to anchor the sequence. |
| **Fix** | Initialised the log. Adopted the `debug-log-skill` protocol v2.0. |
| **Iterations** | 0 |
| **Prevention Rule** | Before editing any file in this repository, grep this log by filename / tag / Root Cause Category, and name the prevention rules that apply in your plan. **Why:** every rule here is scar tissue from a real bug; ignoring them is how we re-ship them. |

<!--
Add new entries below this line, newest at the bottom.
Example of what DL-001 might look like:

### DL-001 — Compose BOM bump removed ComposeView import path

| Field | Value |
|-------|-------|
| **Date** | 2026-04-22 |
| **Tags** | `#android #Compose #Build #Gradle` |
| **Severity** | Build Error |
| **Environment** | Compose BOM 2026.04.00, Kotlin 2.0.0, Gradle 8.7 |
| **File(s)** | `app/build.gradle.kts`, `app/src/.../HomeActivity.kt` |
| **Symptom** | `Unresolved reference: ComposeView` after upgrading Compose BOM. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | The BOM bumped compose.ui to a version that reorganised the `ComposeView` import path. The old import compiled for 18 months before the BOM change reshuffled it. |
| **Fix** | Updated import to the new `androidx.compose.ui.platform.ComposeView` path. Bumped `compose-compiler` to match. |
| **Iterations** | 2 |
| **Prevention Rule** | Always bump the Compose BOM in isolation — commit it alone, run the full build, and grep for removed/renamed symbols before bundling with unrelated changes. **Why:** BOM bumps silently move many packages; bundling them with feature work makes the breakage hard to attribute (DL-001). |
-->
