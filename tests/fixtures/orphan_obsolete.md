# DEBUG_LOG (fixture: orphan_obsolete)

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
| **Fix** | Initialised. |
| **Iterations** | 0 |
| **Prevention Rule** | Grep this log by filename / tag / category before editing. **Why:** every rule is scar tissue from a shipped bug. |

### DL-001 — [OBSOLETE] Some retired rule with no superseder

| Field | Value |
|-------|-------|
| **Date** | 2026-04-03 |
| **Tags** | `#web #Hydration` |
| **Severity** | Runtime Warning |
| **Environment** | Next.js 14.2 |
| **File(s)** | `app/components/PostCard.tsx` |
| **Symptom** | Hydration text mismatch warning. |
| **Root Cause Category** | Hydration Mismatch |
| **Root Cause Context** | Date formatting ran in render. |
| **Fix** | Moved formatting to client-only child. |
| **Iterations** | 1 |
| **Prevention Rule** | Short rule. |
