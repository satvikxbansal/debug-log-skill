# Example session — debug-log-skill in action (v2.0)

> A narrated Claude Code session showing the v2.0 active pre-flight in action. The user is building a social app with a React/Next.js web client and Android/iOS native clients. The feature: let users react to a message with an emoji.
>
> Commentary is in italics. Everything else is literal chat transcript.

---

**User:** Add emoji reactions to messages. Tap the heart icon on a row, pick an emoji from a sheet, it shows next to the message grouped with anyone else who reacted the same way. Works on web, iOS, and Android. Offline-friendly.

*The skill loads via its description (keywords: "new feature", "work", implicit multi-track). Claude begins the active pre-flight.*

**Claude:**
Let me work through the pre-flight before touching any code.

### 1. Track selection

Scanning the repo:

- `apps/web/package.json` with Next.js 15 → **#web**
- `apps/ios/App.xcworkspace` → **#ios**
- `apps/android/build.gradle.kts` with Compose → **#android**, **#kotlin**
- `#cross-cutting` (always on)

### 2. Reference catalog load

Reading in full:

- `references/web.md` — the `#React`, `#RSC`, and `#Hydration` sections
- `references/ios.md` — the `#SwiftUI`, `#List`, `#Network` sections
- `references/android.md` — the `#Compose`, `#Lifecycle`, `#Coroutines` sections
- `references/cross-cutting.md` — always
- `references/tag-taxonomy.md` — to align my vocabulary

Skimming `references/preempt-checklist.md` for the web, ios, android pre-mortem questions.

### 3. Active pre-flight grep on DEBUG_LOG.md

```bash
# Files I'm likely to touch
$ grep -niE "MessageRow|ReactionBar|ReactionSheet" DEBUG_LOG.md
(no results — greenfield feature area)

# Semantic tags for the domain
$ grep -niE "#Compose|#SwiftUI|#React|#Hydration" DEBUG_LOG.md
DL-001: #web #React #NextJS #Hydration #SSR
DL-003: #ios #SwiftUI #UI #Rendering
DL-008: [OBSOLETE] supersedes DL-001 — hydration rule now applies only to client components

# Patterns our feature hits: list diffing, idempotent mutations, offline
$ grep -niE "List.*identity|#Idempotency|#Offline|#Retry" DEBUG_LOG.md
DL-003: SwiftUI list identity on refetch (stable id from server, not client UUID)
DL-004: #cross-cutting #Idempotency — mutating requests need Idempotency-Key + server dedup

# Root Cause Categories that have bitten this codebase
$ grep -niE "Race Condition|Scope Leak" DEBUG_LOG.md
DL-004 (Race), DL-005 (Race, test-only), DL-006 (Scope Leak)
```

**Four entries are directly relevant:**

- **DL-003** (ios, list identity) — reactions mutate a message row; the row's identity must survive that.
- **DL-004** (cross-cutting, idempotency) — reacting is a mutating request. Double-tap or retry must not produce two reactions.
- **DL-006** (kotlin/android, scope leak) — the reaction sheet opens and closes; any in-flight coroutine must not outlive it.
- **DL-008** (web, RSC hydration) — the message list is an RSC; the reaction bar must be a Client Component since it has interactivity and local state.

### 4. Plan

**Goal:** a user can tap a reaction affordance on a message and see their reaction appear grouped with others. Offline-friendly, idempotent, consistent across web / iOS / Android.

**Files touched:**
- `apps/web/components/MessageRow.tsx` (RSC) → extract a new `ReactionBar.tsx` (client component)
- `apps/web/components/ReactionBar.tsx` *(new)*
- `apps/web/app/api/reactions/route.ts` *(new)* — POST with `Idempotency-Key`
- `apps/ios/Shared/Views/MessageRow.swift` — add reaction bar
- `apps/ios/Shared/Views/ReactionSheet.swift` *(new)*
- `apps/ios/Shared/Services/ReactionClient.swift` *(new)* — sends `Idempotency-Key`
- `apps/android/.../MessageRow.kt` — reaction bar composable
- `apps/android/.../ReactionSheet.kt` *(new)*
- `apps/android/.../ReactionRepository.kt` *(new)*
- `backend/handlers/reactions.go` *(new)* — idempotent write

**Interfaces preserved:** message schema (no breaking changes), existing read paths, existing auth middleware.

**Applicable prevention rules** (from grep):

- DL-003: use the server's `message.id` (String) as the list key, not a client UUID. I'll add assertions in tests.
- DL-004: client sends an `Idempotency-Key: <uuid>` header per reaction tap. Server dedupes by (user_id, message_id, emoji, key) in Redis with 24h TTL. Retries reuse the key.
- DL-006: no `GlobalScope`. Reaction requests run on the app-level `ApplicationScope` when triggered, with result delivered via `SharedFlow`. Sheet dismissal drops the collector; request continues. On iOS, equivalent is a `Task { }` on an actor scoped to the app, not the view.
- DL-008: the reaction bar is a Client Component (`"use client"`). Message list stays a Server Component. No `Date.now()` in the server component; if we show "just now" indicators, they're inside the client ReactionBar.

**Verification:**
- Unit: `ReactionRepository` emits the same server key on double-tap within 2s (iOS + Android).
- Playwright: two rapid clicks produce one reaction in the DB.
- Manual: toggle airplane mode mid-tap; confirm the reaction is queued and applied when online.
- Log: server logs `reaction.created` vs `reaction.deduped` — during soak, ratio should stabilise near the expected retry rate.

Ready to code. Starting with the backend endpoint since the client contracts flow from it.

**User:** Go.

*Claude implements. After the backend is done and during iOS work, a test failure surfaces.*

**Claude:**
Three iterations in, the iOS unit test `ReactionRepositoryTests.doubleTap_producesSingleReaction` is still flaky. Running it 20 times — fails 3. Let me pre-flight again before changing more code.

```bash
$ grep -niE "FlakyTest|TestInfrastructure|#XCTest" DEBUG_LOG.md
DL-005: #web Playwright navigation race — "rely on the next assertion will retry" was the mistake

$ grep -niE "Race Condition" DEBUG_LOG.md
DL-004, DL-005
```

DL-005 flags a class I think I'm in: I'm asserting on a post-condition before its precondition has settled. In the iOS test, I'm checking that `repository.pendingCount == 0` right after firing two `react()` calls back-to-back — but both go through an actor, and the assertion runs before the second call has even reached the actor's queue.

Fix: await both calls explicitly, then assert.

*Fix lands. Tests green on 100 runs.*

---

**User:** All good. Time to log this.

**Claude:**
Appending DL-009. Iteration count 3 — not catastrophic, but above "first try" so I'll note the wrong assumption I kept making.

```markdown
### DL-009 — Actor-dispatched test assertions raced before work landed

| Field | Value |
|-------|-------|
| **Date** | 2026-04-21 |
| **Tags** | `#ios #swift #Test #FlakyTest #AsyncAwait` |
| **Severity** | Flaky Test |
| **Environment** | iOS 17.4, Swift 5.10, Xcode 15.3, XCTest |
| **File(s)** | `apps/ios/Tests/ReactionRepositoryTests.swift` |
| **Symptom** | `doubleTap_producesSingleReaction` failed ~3 in 20 runs with `XCTAssertEqual failed: 1 != 0`. |
| **Root Cause Category** | Race Condition |
| **Root Cause Context** | The test fired two `await repository.react(...)` calls, then asserted on a private `pendingCount` property of the repository's actor. Because `pendingCount` was read on a separate task without awaiting the work to land, the assertion occasionally observed the state before the second call had enqueued. I kept re-reading the assertion as if it were synchronous — it wasn't, because the repository's internal work dispatches off the actor. Took me three iterations to stop treating "await react()" as "react() has committed all its effects." |
| **Fix** | Collected both operations into `async let a = ...; async let b = ...; _ = await (a, b)`, then awaited a quiescence flush on the actor (`await repository.flushPending()`), then asserted. Commit `9ae421d`. |
| **Iterations** | 3 |
| **Prevention Rule** | In tests that assert on actor-internal state, await a public quiescence point on the actor (e.g., a `flushPending()` sentinel that returns once the internal queue is empty) before the assertion. Never assert on actor state directly after firing async work — the work has been submitted, not completed. **Why:** actor methods commit effects on their own serial queue; the caller returning does not mean the effect is durable (DL-009). |
```

*Entry committed in the same commit as the test fix. The next time someone writes an actor test, DL-009 surfaces via `grep -niE "#FlakyTest|actor"`.*

---

## What the transcript demonstrates

1. **The active pre-flight is cheap and directional.** Four targeted greps returned four relevant entries in seconds — without loading the whole log into context. Two new entries (DL-008, superseding DL-001) flowed in automatically via cross-reference.
2. **Tags compose with category.** `#Hydration` narrowed to the web component model; `Root Cause Category = Race Condition` surfaced across three tracks and made the pattern visible.
3. **Iteration counting flags hallucination.** When the agent's count went past 2 on the iOS test, the prompt to "pre-flight again before changing more code" is what caught the actor assumption before a fourth wrong attempt.
4. **The log stays append-only even as architecture changes.** DL-001 is `[OBSOLETE]`, not deleted; DL-008 records *why* it retired, so a contributor reading the history can understand both the old rule and its current form.
5. **The prevention rule of DL-009 is the whole point.** The next time anyone — human or agent — writes a test that touches actor state, the rule is in the grep radius. The bug does not ship twice.
