# DEBUG_LOG (fixture: dangling_supersede)

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
| **Prevention Rule** | Grep by filename / tag / category before editing. **Why:** every rule here is scar tissue from a shipped bug. |

### DL-001 — Real entry referencing nonexistent superseded one

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Tags** | `#web #React` |
| **Severity** | Logic Bug |
| **Environment** | React 18.3 |
| **File(s)** | `app/components/PostCard.tsx` |
| **Symptom** | List rerenders lost selection. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | Pretend this replaces an older rule. |
| **Fix** | See commit abc1234. |
| **Iterations** | 2 |
| **Prevention Rule** | Models used in list views carry a stable id from the server, not a client-minted UUID. **Why:** diffing preserves selection via id. |

> Supersedes DL-999. Reason: this is a dangling reference.
