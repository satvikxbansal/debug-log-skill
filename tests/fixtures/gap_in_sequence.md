# DEBUG_LOG (fixture: gap_in_sequence)

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
| **Prevention Rule** | Grep by filename / tag / category before editing. **Why:** every rule here is scar tissue. |

### DL-001 — First entry

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Tags** | `#web #React` |
| **Severity** | Logic Bug |
| **Environment** | React 18.3 |
| **File(s)** | `src/app.tsx` |
| **Symptom** | Stuff. |
| **Root Cause Category** | Null or Unchecked Access |
| **Root Cause Context** | Null-check missed. |
| **Fix** | Added guard. |
| **Iterations** | 1 |
| **Prevention Rule** | Null-check every server response before dereferencing nested fields. **Why:** defensive code prevents cascading crashes. |

### DL-003 — Skips DL-002 (deliberate gap)

| Field | Value |
|-------|-------|
| **Date** | 2026-04-07 |
| **Tags** | `#web #React` |
| **Severity** | Logic Bug |
| **Environment** | React 18.3 |
| **File(s)** | `src/app.tsx` |
| **Symptom** | Stuff. |
| **Root Cause Category** | Null or Unchecked Access |
| **Root Cause Context** | Another null. |
| **Fix** | Another guard. |
| **Iterations** | 1 |
| **Prevention Rule** | Check the second optional field too, not just the first. **Why:** the second is the one that crashed. |
