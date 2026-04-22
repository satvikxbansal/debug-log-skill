# DEBUG_LOG (fixture: wrong_target_supersede)

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

### DL-001 — Active rule (not marked [OBSOLETE])

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
| **Prevention Rule** | Do not read locale-dependent values in server-rendered component bodies. **Why:** SSR/CSR divergence. |

### DL-002 — Second entry points Supersedes at a non-obsolete target

| Field | Value |
|-------|-------|
| **Date** | 2026-04-10 |
| **Tags** | `#web #RSC` |
| **Severity** | Informational |
| **Environment** | Next.js 15.0 |
| **File(s)** | `app/components/PostCard.tsx` |
| **Symptom** | N/A. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | Claims to supersede DL-001 but DL-001 is not tombstoned. |
| **Fix** | Moved to RSC. |
| **Iterations** | 1 |
| **Prevention Rule** | Server Components may read non-deterministic values freely; Client Components must still obey DL-001. **Why:** RSC boundary changes hydration scope. |

> Supersedes DL-001. Reason: migration.
