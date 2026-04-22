# DEBUG_LOG (fixture: valid_supersede)

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
| **Prevention Rule** | Grep this log by filename / tag / category before editing; cite DL numbers in your plan. **Why:** every rule here came from a shipped bug. |

### DL-001 — [OBSOLETE] Hydration mismatch on timestamp rendering

| Field | Value |
|-------|-------|
| **Date** | 2026-04-03 |
| **Tags** | `#web #Hydration` |
| **Severity** | Runtime Warning |
| **Environment** | Next.js 14.2 |
| **File(s)** | `app/components/PostCard.tsx` |
| **Symptom** | Hydration text mismatch warning on server vs client render. |
| **Root Cause Category** | Hydration Mismatch |
| **Root Cause Context** | Date formatting ran in render; server and client produced divergent locale-dependent output. |
| **Fix** | Moved formatting into a client-only child. |
| **Iterations** | 1 |
| **Prevention Rule** | Do not read locale-dependent values in server-rendered component bodies. **Why:** SSR/CSR divergence. |

### DL-002 — RSC migration retires DL-001 hydration guard

| Field | Value |
|-------|-------|
| **Date** | 2026-04-19 |
| **Tags** | `#web #RSC #Hydration` |
| **Severity** | Informational |
| **Environment** | Next.js 15.0, React 19 |
| **File(s)** | `app/components/PostCard.tsx` |
| **Symptom** | N/A — planned migration. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | Migration to App Router + RSC means PostCard is server-only; hydration divergence is no longer possible for it. |
| **Fix** | Marked DL-001 [OBSOLETE] and inlined the formatted timestamp. |
| **Iterations** | 1 |
| **Prevention Rule** | Server Components may read non-deterministic values freely; Client Components (`"use client"`) must still obey the DL-001 rule. **Why:** the RSC boundary changes which components are subject to hydration. |

> Supersedes DL-001. Reason: migration to RSC removed the class of bug DL-001 addressed for most components.
