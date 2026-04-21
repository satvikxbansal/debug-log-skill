# Pre-mortem checklist

A set of questions to run through **before** writing code — per track.

> The goal is not to answer "yes" to every question. It is to surface the ones you can't answer confidently, so you name them in your plan and look them up before you ship.

Pair this with [`cross-cutting.md`](cross-cutting.md) — whose questions apply to every track.

## How to use this

When a new task is non-trivial (touches more than one file, or any module new to you), copy the relevant track's checklist into your plan as a "pre-mortem" section. For each question:

- **Yes, I know the answer** — write the answer in one line, move on.
- **No, I don't** — look it up in the track's reference catalog, in the project's `DEBUG_LOG.md`, or in docs. Write the answer.
- **Doesn't apply** — cross it out with a one-line justification.

Skipping a question silently is the failure mode. The checklist exists because the LLM (or human) is about to make a confident-looking guess, and the whole point is to convert a guess into a known answer.

---

## Cross-cutting — always ask these

1. What is the time-of-day and timezone behaviour? If the code runs "every day at midnight", whose midnight?
2. What happens if the network call returns 5xx? Is the operation idempotent? Does the retry carry an idempotency key?
3. What happens if two users / two tabs / two devices make the same change at the same time? Last-write-wins, or conflict-detected?
4. What's the unit of every number? Milliseconds or seconds? Cents or dollars? Grapheme count or byte count?
5. Where do secrets come from? Are they in the repo, a vault, or an env var? Is the env var validated at boot?
6. Is any text input or output being compared with string equality across platforms? Line endings? Unicode normalisation? Emoji?
7. What's the cache policy? Where is the invalidation? If I deploy at 14:00, when does every user see the change?
8. Is this test order-dependent? Does it assume network? Does it start with a clean state?
9. How does this fail in production? Where does the error surface? Is there enough context in the log to debug without a repro?

---

## Web

1. Does this render on the server? If so, what non-deterministic values does it read? (`Date.now()`, `window`, `Math.random()`, user's zone?)
2. What `useEffect` dependencies does this introduce? Is the effect idempotent? Does it cancel in-flight work on unmount?
3. Is this component's state owned by the right level? (`useState` where, parent prop where?)
4. Are the data list items keyed by a stable id? Does that id survive refetch?
5. Is any cross-origin request involved? What does the preflight look like? What cookies / credentials?
6. Does the CSP allow everything the code runs (inline styles, third-party script, eval)?
7. Is the bundle going to pull in anything big? Check `npm ls` and bundle analyzer.
8. What's the LCP / CLS impact? Any new images without explicit dimensions?
9. What env vars does this touch? Are they `NEXT_PUBLIC_*` (exposed) or server-only?
10. Does this work on Mobile Safari — the 100vh bug, the iOS keyboard, the home bar?

---

## iOS

1. Does this call any privacy-gated API? Is the `Info.plist` usage description in place?
2. If it uses SwiftUI state: is ownership right? `@State` / `@StateObject` / `@ObservedObject` / `@EnvironmentObject` — matches lifetime?
3. Is there a `List` / `ForEach` — are items `Identifiable` with a stable id?
4. Does it open a sheet / cover carrying data — `item:` or `isPresented:`?
5. If it uses `Task { }` inside a class: does it `[weak self]`? Cancel on deinit?
6. Any `@Published` writes from non-main? Actor isolation?
7. Any URLSession — is the completion handler hopping to main?
8. Background modes / push / audio / location — entitlements and capabilities set?
9. Is there a Preview for every new view? Does it inject environment?
10. What's the minimum OS and does every API used exist there? `@available` guards?
11. Is `async`/`await` used or is this still a completion-handler API? If mixed, who owns the bridge?
12. If this is a screen with text input: keyboard avoidance tested?

---

## Android

1. Is this running inside a foreground service? Is the `foregroundServiceType` declared (Android 14+) and does it match the `startForeground()` call?
2. If it's Compose: which composables have `remember` that would lose state on rotation? Is `rememberSaveable` needed?
3. Overlay window? Flags state machine for focus / IME set up?
4. Any screen capture? Does it detect `FLAG_SECURE` / `isSecure` and handle gracefully?
5. API level branching: anything used below `minSdk`? Any `@RequiresApi` needed?
6. Accessibility service? Auto-disable handling?
7. Activity / Fragment lifecycle: `onNewIntent`, config change survival?
8. Permissions: all three states handled (first ask, rationale, permanent-deny)?
9. Hilt scoping: is the ViewModel scoped to the right `NavBackStackEntry`?
10. Room: is the DAO async / Flow? Is there a migration if schema changed?
11. WorkManager / AlarmManager: is it revokable-on-14 aware? Idempotent if run twice?
12. R8 / ProGuard: is any class used via reflection — does it have a keep rule?
13. `targetSdk` bump side effects — any permission behaviour change?

---

## macOS

1. What TCC permissions does this feature need? (Screen Recording, Accessibility, Input Monitoring, Full Disk Access, Automation.) Are they declared in entitlements and the user is prompted?
2. Is the app sandboxed? What files outside the container does it touch? Security-scoped bookmarks or entitlement?
3. Menu-bar app — `LSUIElement = YES`? Activation policy?
4. NSWindow behaviour across spaces / displays? `collectionBehavior` declared?
5. Full-screen semantics — native space, presentation options, borderless?
6. Are all embedded binaries (frameworks, helper CLIs) code-signed and notarised?
7. Universal link / URL scheme — registered via Launch Services?
8. Login item — using `SMAppService` (macOS 13+), not the deprecated API?
9. If it scripts other apps: `NSAppleEventsUsageDescription` and `com.apple.security.automation.apple-events`?
10. External displays / hot-plug — does window position validate against `NSScreen.screens`?
11. If it's Catalyst-compatible: any iOS-only APIs that crash on mac?
12. Apple Silicon vs Intel — are both slices in embedded binaries?

---

## Kotlin (language-level, in any context)

1. Which coroutine scope launches this work, and what cancels it?
2. Is this `GlobalScope`? If so, why?
3. Is `SupervisorJob` / `supervisorScope` used where child-independent failure matters? Or the default `Job` where it doesn't?
4. `Flow` builder — is this `flow { }`, `callbackFlow { }`, or `channelFlow { }` — by producer semantics?
5. `StateFlow` vs `SharedFlow(replay = 1)` — state or events?
6. Dispatcher for CPU-bound work is `Default`, not `IO`?
7. Is there `runBlocking` anywhere in production code?
8. Serialisation: any new non-nullable field without a default?
9. Platform types from Java — any `T!` leaking through without an explicit nullability declaration?
10. `lateinit` — who guarantees initialisation before first read?
11. `when` over a sealed hierarchy — expression, so compiler checks exhaustiveness?

---

## Swift (language-level, in any context)

1. Actor isolation — does this method need `@MainActor`?
2. Sendable — does any class cross actor boundaries without being `Sendable`?
3. Actor re-entrancy — is any state read before an `await` assumed intact after?
4. `Task { }` in a class — `[weak self]`?
5. `async let` or `TaskGroup` used correctly for concurrency?
6. Codable round-trip for every DTO — tested with fixtures? Key strategy set?
7. Money math — `Decimal` or integer minor units, never `Double`?
8. Force-unwraps (`!`) — any that could hit nil?
9. Value type with a class inside — is the sharing intentional?
10. `@escaping` closure stored on a class — `[weak self]`?
11. SwiftUI body decomposition — any body > ~30 lines of dense generics?
12. `#Preview` — injected environment, mocked state?
