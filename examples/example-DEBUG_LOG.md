# DEBUG_LOG (example)

> Log of every bug fixed in this repository — build errors, runtime crashes, ANRs, logic bugs, flaky tests, perf regressions, and production incidents.
>
> This log is maintained under the `debug-log-skill` protocol (v2.0). See [`SKILL.md`](../SKILL.md) for the full rules.

## Tracks active in this project

- [x] web
- [x] ios
- [x] android
- [ ] macos
- [x] kotlin
- [x] swift
- [x] cross-cutting (always on)

## The four non-negotiable rules

1. **Sequence** — entries are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip. Never reuse.
2. **Never skip** — every bug fix gets an entry, no matter how small.
3. **Active pre-flight** — grep this log by filename / tag / Root Cause Category before editing. Do not read end-to-end.
4. **Append-only** — never delete or edit an existing entry. When a rule is retired, prepend `[OBSOLETE]` to its title and add a superseding entry.

---

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
| **Root Cause Context** | Seed entry. Category `Other` is acceptable for seed / meta entries. |
| **Fix** | Initialised the log. Adopted the `debug-log-skill` protocol v2.0. |
| **Iterations** | 0 |
| **Prevention Rule** | Before editing any file in this repository, grep this log by filename / tag / Root Cause Category, and name the prevention rules that apply in your plan. **Why:** every rule here is scar tissue from a real bug; ignoring them is how we re-ship them. |

### DL-001 — [OBSOLETE] Hydration mismatch on timestamp rendering

| Field | Value |
|-------|-------|
| **Date** | 2026-04-03 |
| **Tags** | `#web #React #NextJS #Hydration #SSR` |
| **Severity** | Runtime Warning |
| **Environment** | Next.js 14.2, React 18.3, Node 20.12 |
| **File(s)** | `app/components/PostCard.tsx` |
| **Symptom** | Console on every page load: `Warning: Text content did not match. Server: "12:04 PM" Client: "12:04:01 PM"`. Some cards rendered blank below the title. |
| **Root Cause Category** | Hydration Mismatch |
| **Root Cause Context** | `PostCard` called `new Date(post.createdAt).toLocaleTimeString()` during render. Server rendered with container UTC formatting; client rendered with the user's locale — producing different output. Classic SSR/CSR divergence. |
| **Fix** | Moved the timestamp format into a client-only child component (`<TimeAgo date={...} />`) that reads the value in `useEffect` and initialises to the server-rendered ISO string. Commit `a4c1f90`. |
| **Iterations** | 1 |
| **Prevention Rule** | Never read `window`, `document`, `localStorage`, `Date.now()`, `new Date()`, or `Math.random()` inside a server-rendered React component body. Time / locale-dependent formatting belongs in a client component or `useEffect`. **Why:** hydration mismatches corrupt the tree in ways that don't always warn (DL-001). |

### DL-002 — Android 14 foreground service crash on startup

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Tags** | `#android #ForegroundService #Permissions` |
| **Severity** | Runtime Crash |
| **Environment** | Android API 34 (device), Kotlin 1.9.25, compileSdk 34, targetSdk 34 |
| **File(s)** | `app/src/main/AndroidManifest.xml`, `app/src/main/java/.../SyncService.kt` |
| **Symptom** | On Android 14 devices, app crashed on sign-in with `android.app.MissingForegroundServiceTypeException: Starting FGS without a type`. Worked fine on API 33 and older. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | Android 14 (API 34) requires every foreground service to declare `android:foregroundServiceType` in the manifest *and* pass the matching type to `startForeground(id, notification, type)`. The manifest entry for `SyncService` had no `foregroundServiceType`. We missed the migration because the crash is silent on API 33 and prior. |
| **Fix** | Added `android:foregroundServiceType="dataSync"` to the manifest and `FOREGROUND_SERVICE_DATA_SYNC` permission. Updated the `startForeground` call to pass `ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC`. Commit `b7e21d5`. |
| **Iterations** | 2 |
| **Prevention Rule** | Every `<service>` that calls `startForeground` declares `android:foregroundServiceType`; the runtime call passes the matching `ServiceInfo.FOREGROUND_SERVICE_TYPE_*`. Add a CI lint rule that fails if any service is missing the type. **Why:** API 34's requirement is mandatory with no graceful fallback (DL-002). |

### DL-003 — SwiftUI list selection resets on refresh

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Tags** | `#ios #SwiftUI #UI #Rendering` |
| **Severity** | Logic Bug |
| **Environment** | iOS 17.4, Swift 5.10, Xcode 15.3 |
| **File(s)** | `Shared/Views/FeedView.swift`, `Shared/Models/Post.swift` |
| **Symptom** | User was reading a long post list, pull-to-refresh completed, and the list jumped back to the top. Detail view sometimes closed. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | `Post` was decoded with a fresh `UUID()` for its `id` each time the API response arrived. When `List` re-diffed after refresh, every row looked like a brand-new row; selection and scroll position were invalidated. The API's own `postId` (String) was stored but not used for identity. |
| **Fix** | Made `Post: Identifiable` with `var id: String { postId }`. Removed the `let id = UUID()` line. Commit `c9f1d44`. |
| **Iterations** | 3 |
| **Prevention Rule** | Models shown in `List` or `ForEach` use an identity that survives refetch — the server's primary key, not a client-minted UUID. Identity is **stable**: same logical object yields the same id across every decode. **Why:** SwiftUI diffing preserves selection and scroll position via id (DL-003). |

### DL-004 — Double charge on flaky payment network

| Field | Value |
|-------|-------|
| **Date** | 2026-04-10 |
| **Tags** | `#cross-cutting #Network #HTTP #Retry #Idempotency` |
| **Severity** | Incident |
| **Environment** | iOS client 4.12.0, Android client 4.12.0, Go backend 1.22, Redis 7.2 |
| **File(s)** | `backend/handlers/payment.go`, `ios/Services/PaymentClient.swift`, `android/.../PaymentRepository.kt` |
| **Symptom** | Three users reported being charged twice for a single order. Payment logs showed two Stripe `PaymentIntent.confirm` calls within 400 ms from the same device. |
| **Root Cause Category** | Race Condition |
| **Root Cause Context** | Mobile client retried `POST /api/v1/payments/confirm` on a 504 from our API gateway. The upstream payment handler had actually succeeded before the gateway timed out — so the retry was a second successful charge. No idempotency key; the client and server had no way to tell the retry from a new intent. |
| **Fix** | (1) Client generates an idempotency key (UUID v4) per payment intent and includes it in the `Idempotency-Key` header. (2) Server stores `(key, result)` in Redis with 24h TTL; a second request with the same key returns the cached result without re-calling Stripe. (3) Stripe's own idempotency mechanism also consumes the same key. Commit `d1b8c0e`. Incident post-mortem: `docs/incidents/2026-04-10-double-charge.md`. |
| **Iterations** | 4 |
| **Prevention Rule** | Every mutating request (non-GET) that initiates a side effect in a downstream system carries an `Idempotency-Key` header. Server has a deduplication store keyed by it, TTL ≥ 24h. Retry preserves the key. **Why:** 5xx on a payment endpoint leaves state ambiguous; retries without idempotency produce duplicate side effects (DL-004). |

### DL-005 — Flaky Playwright test on CI only

| Field | Value |
|-------|-------|
| **Date** | 2026-04-12 |
| **Tags** | `#web #Test #FlakyTest #Playwright #E2E #CI` |
| **Severity** | Flaky Test |
| **Environment** | Playwright 1.43, Node 20.12, GitHub Actions ubuntu-latest |
| **File(s)** | `e2e/tests/checkout.spec.ts` |
| **Symptom** | `checkout.spec.ts > completes purchase with stored card` passed locally. Failed ~1 in 8 runs on GitHub Actions with `expect(locator).toBeVisible() — element not found`. |
| **Root Cause Category** | Race Condition |
| **Root Cause Context** | The test used `await page.click('[data-testid=pay]')` followed immediately by `await expect(page.locator('[data-testid=success]')).toBeVisible()`. The click triggered navigation; the success locator raced with navigation. On faster local hardware, the assertion arrived after navigation completed. On slower CI runners, it arrived during navigation. |
| **Fix** | Wrapped the flow with `await Promise.all([page.waitForNavigation(), page.click('[data-testid=pay]')])`. Then the success assertion is safe. Commit `e3a7b91`. |
| **Iterations** | 2 |
| **Prevention Rule** | Playwright / Cypress tests that trigger navigation follow the click with an explicit wait — `waitForNavigation`, `waitForURL`, or `waitFor(response, …)`. Never rely on "the next assertion will retry". **Why:** visibility assertions during navigation produce intermittent failures that only appear on slow machines (DL-005). |

### DL-006 — Kotlin coroutine leaked on view model scope mismatch

| Field | Value |
|-------|-------|
| **Date** | 2026-04-15 |
| **Tags** | `#kotlin #android #Coroutines #ScopeLeak #Memory #Leak` |
| **Severity** | Logic Bug |
| **Environment** | Kotlin 1.9.25, kotlinx.coroutines 1.8.1, Hilt 2.51, LeakCanary 2.13 |
| **File(s)** | `app/src/main/java/.../UploadManager.kt` |
| **Symptom** | LeakCanary reported an `UploadScreenViewModel` instance leaking after the upload screen was dismissed. Memory grew over a session. |
| **Root Cause Category** | Scope Leak |
| **Root Cause Context** | `UploadManager` was a Hilt `@Singleton`. It launched uploads with `GlobalScope.launch { … }`. The coroutine outlived the upload screen, and its closure captured a callback lambda that closed over the `UploadScreenViewModel` from the screen that started it. Screen gone, VM still alive. |
| **Fix** | Replaced `GlobalScope.launch` with an injected `ApplicationScope: CoroutineScope` backed by `SupervisorJob() + Dispatchers.IO`. Cross-boundary events are now sent via a `SharedFlow<UploadEvent>` the screen collects via `repeatOnLifecycle`. Screen dismissal drops the collector; the upload continues and its events go unheard (correctly). Commit `f5c20a2`. |
| **Iterations** | 3 |
| **Prevention Rule** | `GlobalScope` is banned in production code. A single `ApplicationScope` is provided via DI for genuinely process-lifetime work; everything else uses a lifecycle-bound scope. Cross-boundary events go through `SharedFlow`, not captured callbacks. A detekt rule (`GlobalCoroutineUsage`) enforces. **Why:** captured callbacks in long-lived coroutines leak the owner of the callback (DL-006). |

### DL-007 — Agent invented a Compose modifier that doesn't exist

| Field | Value |
|-------|-------|
| **Date** | 2026-04-17 |
| **Tags** | `#android #Compose #Build #LLM` |
| **Severity** | Build Error |
| **Environment** | Compose 1.6.8, Kotlin 1.9.25, Claude Code session |
| **File(s)** | `app/src/main/java/.../ProfileScreen.kt` |
| **Symptom** | Build failed with `Unresolved reference: onHoverEnter`. The agent had added `.onHoverEnter { … }` to a `Column` modifier chain. |
| **Root Cause Category** | LLM Hallucination or Assumption |
| **Root Cause Context** | The agent produced the modifier by analogy with desktop frameworks' `onHoverEnter` / `onHoverExit` APIs. Jetpack Compose's pointer-input API does not have that modifier name — the correct call is `.pointerInput { … awaitPointerEventScope { … } }` with `PointerEventType.Enter`. The agent did not verify the API existed before calling it. |
| **Fix** | Rewrote the hover detection using `PointerInteropFilter` and `PointerEventType.Enter` / `PointerEventType.Exit`. Commit `a71ef33`. |
| **Iterations** | 4 |
| **Prevention Rule** | Before calling an uncommon API in agent-generated code, grep the codebase for at least one prior usage; if zero results, open the library's official docs and cite the exact symbol + version in the commit message or plan. **Why:** LLM-invented API names compile against the model's fictional world and only fail at build time here (DL-007). |

### DL-008 — [OBSOLETE] DL-001: hydration guard no longer needed after RSC migration

| Field | Value |
|-------|-------|
| **Date** | 2026-04-19 |
| **Tags** | `#web #React #NextJS #RSC #Hydration` |
| **Severity** | Informational |
| **Environment** | Next.js 15.0 (App Router, RSC), React 19.0 |
| **File(s)** | `app/components/PostCard.tsx`, `app/components/TimeAgo.tsx` |
| **Symptom** | N/A — planned migration. |
| **Root Cause Category** | API Change |
| **Root Cause Context** | The project migrated from Pages Router + SSR to App Router + React Server Components. `PostCard` is now a Server Component; it runs only on the server and its output is streamed to the client. Date formatting in `PostCard` no longer risks hydration mismatch because there is no client render of that component. The prevention rule from DL-001 ("never read `new Date()` during render in SSR components") still holds in spirit, but now applies to Client Components (`"use client"`) only, not Server Components. |
| **Fix** | Inlined the formatted timestamp in `PostCard` (now a Server Component). Kept `TimeAgo.tsx` for the one place we still need live-updating relative time (it is marked `"use client"`). Marked DL-001 as `[OBSOLETE]`: prepended `[OBSOLETE]` to its title line (the only permitted edit to a prior entry). Commit `b82d14c`. |
| **Iterations** | 1 |
| **Prevention Rule** | Server Components may read non-deterministic values (dates, random) freely because they render once per request with no client counterpart. Client Components (`"use client"`) must still obey the DL-001 rule. **Why:** the RSC boundary changes which components are subject to hydration; the old rule was correct but over-broad for the new architecture (DL-008 supersedes DL-001). |

> Supersedes DL-001. Reason: migration to React Server Components removed the class of bug DL-001 addressed for most components; the rule now applies only to components explicitly marked `"use client"`.
