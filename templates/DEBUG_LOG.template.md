# DEBUG_LOG

> Log of every bug fixed in this repository — build errors, runtime crashes, ANRs, logic bugs, flaky tests, perf regressions, and production incidents.
>
> This log is maintained under the `debug-log-skill` protocol. See [`SKILL.md`](https://github.com/YOUR_ORG/debug-log-skill) for the full rules.

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
3. **Read before coding** — skim this log at the start of every non-trivial task. Prevention rules that touch your area must be named in your plan.
4. **Append-only** — never delete or edit an existing entry. If superseded, add a new one that cross-references.

## Entry template

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident |
| **Track** | web / ios / android / macos / kotlin / swift / cross-cutting |
| **File(s)** | `path/to/file.ext` |
| **Symptom** | What failed. Quote the error, include the firing stack frame. |
| **Root Cause** | Why it happened. Name the misconception, not the line. |
| **Fix** | What was changed. Reference the commit SHA if available. |
| **Prevention Rule** | Imperative, checkable, specific. Includes a "Why:" clause. |
```

---

## Entries

### DL-000 — DEBUG_LOG started

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD <!-- fill in when you initialise --> |
| **Severity** | Informational |
| **Track** | cross-cutting |
| **File(s)** | `DEBUG_LOG.md` |
| **Symptom** | N/A |
| **Root Cause** | N/A |
| **Fix** | Initialised the log. Adopted the `debug-log-skill` protocol. |
| **Prevention Rule** | Before editing any file in this repository, skim this log and name the prevention rules that apply in your plan. Why: every rule here is the scar tissue from a real bug; ignoring them is how we re-ship them. |

<!--
Add new entries below this line, newest at the bottom.
Example of what DL-001 might look like:

### DL-001 — Short title

| Field | Value |
|-------|-------|
| **Date** | 2026-04-22 |
| **Severity** | Build Error |
| **Track** | android |
| **File(s)** | `app/build.gradle.kts` |
| **Symptom** | `Unresolved reference: ComposeView` after upgrading Compose BOM to 2026.04.00. |
| **Root Cause** | The BOM bumped `compose.ui` to a version that removed the deprecated `androidx.compose.ui.platform.ComposeView` import path. |
| **Fix** | Updated import to `androidx.compose.ui.platform.ComposeView` from the new package. Bumped `compose-compiler` to match. |
| **Prevention Rule** | Always bump the Compose BOM in isolation — commit it alone, run the full build, and grep for removed symbols before bundling with unrelated changes. Why: BOM bumps silently move many packages (DL-001). |
-->
