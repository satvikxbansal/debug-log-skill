# DEBUG_LOG (example)

> Log of every bug fixed in this repository — build errors, runtime crashes, ANRs, logic bugs, flaky tests, perf regressions, and production incidents.
>
> This log is maintained under the `debug-log-skill` protocol. See [`SKILL.md`](../SKILL.md) for the full rules.

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
3. **Read before coding** — skim this log at the start of every non-trivial task. Prevention rules that touch your area must be named in your plan.
4. **Append-only** — never delete or edit an existing entry. If superseded, add a new one that cross-references.

---

## Entries

### DL-000 — DEBUG_LOG started

| Field | Value |
|-------|-------|
| **Date** | 2026-04-01 |
| **Severity** | Informational |
| **Track** | cross-cutting |
| **File(s)** | `DEBUG_LOG.md` |
| **Symptom** | N/A |
| **Root Cause** | N/A |
| **Fix** | Initialised the log. Adopted the `debug-log-skill` protocol. |
| **Prevention Rule** | Before editing any file in this repository, skim this log and name the prevention rules that apply in your plan. Why: every rule here is the scar tissue from a real bug; ignoring them is how we re-ship them. |

### DL-001 — Hydration mismatch on timestamp rendering

| Field | Value |
|-------|-------|
| **Date** | 2026-04-03 |
| **Severity** | Runtime Warning |
| **Track** | web |
| **File(s)** | `app/components/PostCard.tsx` |
| **Symptom** | Console warning on every page load: `Warning: Text content did not match. Server: "12:04 PM" Client: "12:04:01 PM"`. Some cards rendered blank below the title. |
| **Root Cause** | `PostCard` called `new Date(post.createdAt).toLocaleTimeString()` during render. Server rendered with the container's UTC formatting, client rendered with the user's locale — producing different output. This is the classic SSR/CSR divergence. |
| **Fix** | Moved the timestamp format into a client-only child component (`<TimeAgo date={...} />`) that reads the value in `useEffect` and initialises to the server-rendered ISO string. Commit `a4c1f90`. |
| **Prevention Rule** | Never read `window`, `document`, `localStorage`, `Date.now()`, `new Date()`, or `Math.random()` inside a server-rendered React component body. Time / locale-dependent formatting belongs in a client component or `useEffect`. Why: hydration mismatches corrupt the tree in ways that don't always warn (DL-001). |

### DL-002 — Android 14 foreground service crash on startup

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Severity** | Runtime Crash |
| **Track** | android |
| **File(s)** | `app/src/main/AndroidManifest.xml`, `app/src/main/java/.../SyncService.kt` |
| **Symptom** | On Android 14 devices, app crashed on sign-in with `android.app.MissingForegroundServiceTypeException: Starting FGS without a type`. Worked fine on API 33 and older. |
| **Root Cause** | Android 14 (API 34) requires every foreground service to declare `android:foregroundServiceType` in the manifest *and* pass the matching type to `startForeground(id, notification, type)`. The manifest entry for `SyncService` had no `foregroundServiceType`. |
| **Fix** | Added `android:foregroundServiceType="dataSync"` to the manifest and `FOREGROUND_SERVICE_DATA_SYNC` permission. Updated the `startForeground` call to pass `ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC`. Commit `b7e21d5`. |
| **Prevention Rule** | Every `<service>` that calls `startForeground` declares `android:foregroundServiceType`; the runtime call passes the matching `ServiceInfo.FOREGROUND_SERVICE_TYPE_*`. Add a CI lint rule that fails if any service is missing the type. Why: API 34's requirement is mandatory with no graceful fallback (DL-002). |

### DL-003 — SwiftUI list selection resets on refresh

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Severity** | Logic Bug |
| **Track** | ios |
| **File(s)** | `Shared/Views/FeedView.swift`, `Shared/Models/Post.swift` |
| **Symptom** | User was reading a long post list, pull-to-refresh completed, and the list jumped back to the top. Detail view sometimes closed. |
| **Root Cause** | `Post` was decoded with a fresh `UUID()` for its `id` each time the API response arrived. When `List` re-diffed after refresh, every row looked like a brand-new row; selection and scroll position were invalidated. The API's own `postId` (String) was stored but not used for identity. |
| **Fix** | Made `Post: Identifiable` with `var id: String { postId }`. Removed the `let id = UUID()` line. Commit `c9f1d44`. |
| **Prevention Rule** | Models shown in `List` or `ForEach` use an identity that survives refetch — the server's primary key, not a client-minted UUID. Identity is **stable**: same logical object yields the same id across every decode. Why: SwiftUI diffing preserves selection and scroll position via id (DL-003). |

### DL-004 — Double charge on flaky payment network

| Field | Value |
|-------|-------|
| **Date** | 2026-04-10 |
| **Severity** | Incident |
| **Track** | cross-cutting |
| **File(s)** | `backend/handlers/payment.go`, `ios/Services/PaymentClient.swift`, `android/.../PaymentRepository.kt` |
| **Symptom** | Three users reported being charged twice for a single order. Payment logs showed two Stripe `PaymentIntent.confirm` calls within 400 ms from the same device. |
| **Root Cause** | Mobile client retried `POST /api/v1/payments/confirm` on a 504 from our API gateway. The upstream payment handler had actually succeeded before the gateway timed out — so the retry was a second successful charge. No idempotency key. |
| **Fix** | (1) Client generates an idempotency key (UUID v4) per payment intent and includes it in the `Idempotency-Key` header. (2) Server stores `(key, result)` in Redis with 24h TTL; a second request with the same key returns the cached result without re-calling Stripe. (3) Stripe's own idempotency mechanism also consumes the same key. Commit `d1b8c0e`. Incident post-mortem: `docs/incidents/2026-04-10-double-charge.md`. |
| **Prevention Rule** | Every mutating request (non-GET) that initiates a side effect in a downstream system carries an `Idempotency-Key` header. Server has a deduplication store keyed by it, TTL ≥ 24h. Retry preserves the key. Why: 5xx on a payment endpoint leaves state ambiguous; retries without idempotency produce duplicate side effects (DL-004). |

### DL-005 — Flaky Playwright test on CI only

| Field | Value |
|-------|-------|
| **Date** | 2026-04-12 |
| **Severity** | Flaky Test |
| **Track** | web |
| **File(s)** | `e2e/tests/checkout.spec.ts` |
| **Symptom** | `checkout.spec.ts > completes purchase with stored card` passed locally. Failed ~1 in 8 runs on GitHub Actions with `expect(locator).toBeVisible() — element not found`. |
| **Root Cause** | The test used `await page.click('[data-testid=pay]')` followed immediately by `await expect(page.locator('[data-testid=success]')).toBeVisible()`. The click navigated to a new page; the success locator race-raced with navigation. On faster local hardware (M2 Mac), the assertion arrived after navigation completed. On slower CI runners, it arrived during navigation. |
| **Fix** | Wrapped the flow with `await Promise.all([page.waitForNavigation(), page.click('[data-testid=pay]')])`. Then the success assertion is safe. Commit `e3a7b91`. |
| **Prevention Rule** | Playwright / Cypress tests that trigger navigation follow the click with an explicit wait — `waitForNavigation`, `waitForURL`, or `waitFor(response, …)`. Never rely on "the next assertion will retry". Why: visibility assertions during navigation produce intermittent failures that only appear on slow machines (DL-005). |

### DL-006 — Kotlin coroutine leaked on view model scope mismatch

| Field | Value |
|-------|-------|
| **Date** | 2026-04-15 |
| **Severity** | Logic Bug |
| **Track** | kotlin |
| **File(s)** | `app/src/main/java/.../UploadManager.kt` |
| **Symptom** | LeakCanary reported an `UploadManager` instance leaking after the upload screen was dismissed. Memory grew over a session. |
| **Root Cause** | `UploadManager` was a singleton (Hilt `@Singleton`). It launched uploads with `GlobalScope.launch { … }`. The `Task`-equivalent coroutine outlived the upload screen, and its closure captured `this@UploadManager` — which was fine, since `UploadManager` itself is long-lived. But it *also* captured a callback lambda that closed over the `UploadScreenViewModel` from the screen that started it. Screen gone, VM still alive. |
| **Fix** | Replaced `GlobalScope.launch` with an injected `ApplicationScope: CoroutineScope` backed by `SupervisorJob() + Dispatchers.IO`. The callback is invoked via a weak reference or — better — via a `SharedFlow<UploadEvent>` the screen collects via `repeatOnLifecycle`. Screen dismissal drops the collector; the upload continues and its events go unheard (correctly). Commit `f5c20a2`. |
| **Prevention Rule** | `GlobalScope` is banned in production code. A single `ApplicationScope` is provided via DI for genuinely process-lifetime work; everything else uses a lifecycle-bound scope. Cross-boundary events go through `SharedFlow`, not captured callbacks. A detekt rule (`GlobalCoroutineUsage`) enforces. Why: captured callbacks in long-lived coroutines leak the owner of the callback (DL-006). |
