# DEBUG_LOG (fixture: valid_full)

## Entries

### DL-000 — DEBUG_LOG started

| Field | Value |
|-------|-------|
| **Date** | 2026-04-01 |
| **Tags** | `#cross-cutting #Logging` |
| **Severity** | Informational |
| **Environment** | N/A |
| **File(s)** | `DEBUG_LOG.md` |
| **Symptom** | N/A |
| **Root Cause Category** | Other |
| **Root Cause Context** | Seed. |
| **Fix** | Initialised the log. |
| **Iterations** | 0 |
| **Prevention Rule** | Before editing any file in this repository, grep this log by filename / tag / Root Cause Category, and cite the applicable DL numbers in your plan. **Why:** every rule here is scar tissue from a real bug. |

### DL-001 — Compose BOM bump moved ComposeView

| Field | Value |
|-------|-------|
| **Date** | 2026-04-12 |
| **Tags** | `#android #Compose #Build` |
| **Severity** | Build Error |
| **Environment** | Compose BOM 2026.04.00, Kotlin 2.0.0, Gradle 8.7 |
| **File(s)** | `app/build.gradle.kts` |
| **Symptom** | `Unresolved reference: ComposeView` after BOM upgrade. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | The BOM reorganised the ComposeView import path; the old symbol compiled for a year before the bump reshuffled it. |
| **Fix** | Updated import to `androidx.compose.ui.platform.ComposeView`. |
| **Iterations** | 2 |
| **Prevention Rule** | Bump the Compose BOM in an isolated commit, run the full build, and grep for renamed/removed symbols before bundling feature work. **Why:** BOM bumps silently move packages; bundled diffs make breakage hard to attribute. |
