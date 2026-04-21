# iOS — error catalog

Covers: Swift language surface as it appears in iOS apps, SwiftUI (iOS 14+), UIKit, UIScene lifecycle, AVFoundation / AVAudioSession, URLSession, Core Data, background modes, deep links, App Transport Security, `Info.plist` usage descriptions, keyboard handling, SwiftUI Previews, concurrency (`async`/`await`, `@MainActor`, `Sendable`).

Each entry follows the same shape: **Symptom → Root cause → Fix → Prevention rule.**

## Table of contents

1. [Missing `Info.plist` usage description — first permission request crashes](#i01)
2. [`@State` survives across identity changes it shouldn't](#i02)
3. [`@StateObject` vs `@ObservedObject` — object re-created every render](#i03)
4. [`@EnvironmentObject` crash: "may be missing as an ancestor"](#i04)
5. [SwiftUI list selection / navigation resets on data reload](#i05)
6. [`NavigationStack` path goes out of sync with data](#i06)
7. [SwiftUI sheet shows wrong content after rapid toggle](#i07)
8. [Modifier order changes behaviour](#i08)
9. [`onAppear` fires more often than expected](#i09)
10. [SwiftUI Previews crash with "failed to launch" or blank canvas](#i10)
11. [`@Published` update from background thread — "Publishing changes from background threads"](#i11)
12. [`async` function called from synchronous context — "async call in a function that does not support concurrency"](#i12)
13. [`@MainActor` isolation violated silently before Swift 6](#i13)
14. [`Sendable` warnings after enabling strict concurrency](#i14)
15. [Task cancellation ignored — work continues after view disappears](#i15)
16. [Structured-concurrency `Task { }` captures `self` strongly](#i16)
17. [UIKit retain cycle in closure](#i17)
18. [`weak self` causes "self deallocated" crash when force-unwrapped](#i18)
19. [`AVAudioSession` interruption leaves the app muted](#i19)
20. [`AVAudioPlayer` silently fails in background](#i20)
21. [`URLSession` upload task times out only on cellular](#i21)
22. [App Transport Security blocks HTTP in release](#i22)
23. [`URLSession` completion handler called on background queue — UI doesn't update](#i23)
24. [Core Data: "context is a different queue" crash](#i24)
25. [Core Data: merge policy silently drops changes](#i25)
26. [`NSFetchedResultsController` misses updates after background insert](#i26)
27. [Background task expires before work completes](#i27)
28. [Deep link opens but state isn't restored](#i28)
29. [Universal links open in Safari, not the app](#i29)
30. [Keyboard obscures text field in scroll view](#i30)
31. [UIScene migration — `application(_:didFinishLaunching)` side effects lost](#i31)
32. [`Codable` decoding silently drops optional keys with wrong casing](#i32)
33. [`Date` decoded off by hours because of timezone assumption](#i33)

---

## <a name="i01"></a>1. Missing `Info.plist` usage description — first permission request crashes

**Symptom.** App crashes on first call to a privacy-gated API (camera, microphone, photos, location, contacts, Bluetooth, local network, speech, HealthKit). Console: `This app has crashed because it attempted to access privacy-sensitive data without a usage description. The app's Info.plist must contain an NSCameraUsageDescription key with a string value explaining to the user how the app uses this data.`

**Root cause.** iOS enforces an `NS…UsageDescription` key in `Info.plist` (or the target's "Custom iOS Target Properties") *before* it will even show the permission prompt. The crash is deliberate — Apple wants the description written before shipping.

**Fix.** Add the specific key the crash names. The exact keys differ per resource: `NSCameraUsageDescription`, `NSMicrophoneUsageDescription`, `NSPhotoLibraryUsageDescription`, `NSPhotoLibraryAddUsageDescription`, `NSLocationWhenInUseUsageDescription`, `NSLocationAlwaysAndWhenInUseUsageDescription`, `NSContactsUsageDescription`, `NSBluetoothAlwaysUsageDescription`, `NSLocalNetworkUsageDescription`, `NSSpeechRecognitionUsageDescription`, `NSHealthShareUsageDescription`. The value is the human-readable justification that appears in the system prompt — keep it specific, not generic.

**Prevention rule.** Before calling any Apple framework that touches a privacy resource, grep `Info.plist` for the corresponding `NS…UsageDescription` key. If the entitlement also requires provisioning (HealthKit, Sign in with Apple, Push), add the entitlement at the same time. Why: the crash is unrecoverable, ships to users unless an integration test exercises the permission path.

## <a name="i02"></a>2. `@State` survives across identity changes it shouldn't

**Symptom.** A child view shows stale text or selection after its parent swaps which model it's viewing. Looks like the view "remembers" the old data.

**Root cause.** SwiftUI reuses view instances based on structural identity. If two sibling views have the same position in the parent's body, SwiftUI treats them as the same view and keeps their `@State` across the swap — even if the *data* they're rendering is different.

**Fix.** Force a new identity with `.id(model.id)` on the child. When the id changes, SwiftUI tears down the subtree and rebuilds it with fresh `@State`.

**Prevention rule.** When a view is parameterised by an identity (user id, document id, selection), attach `.id(identity)` to the view — unless you have a specific reason to want the `@State` to persist. Why: SwiftUI's identity rules are positional by default, not value-based, and the stale-state bug doesn't warn.

## <a name="i03"></a>3. `@StateObject` vs `@ObservedObject` — object re-created every render

**Symptom.** An `ObservableObject` inside a view seems to lose its state every time the parent updates. Timers restart, in-flight requests get cancelled, transient UI state resets.

**Root cause.** `@ObservedObject var vm = MyViewModel()` *creates a new instance every time the parent re-renders*. SwiftUI does not own the lifecycle. `@StateObject` is what owns the lifecycle — it creates the instance once per view identity and holds it across re-renders.

**Fix.** Use `@StateObject` when the view *owns* the object. Use `@ObservedObject` when the object is passed in from a parent that owns it. Rule of thumb: only the view that first constructs the object should use `@StateObject`; every descendant that receives it as a parameter uses `@ObservedObject` (or `@EnvironmentObject`).

**Prevention rule.** If you see `@ObservedObject var x = SomeType()` — with an initialiser in the property — you almost always meant `@StateObject`. Why: the default-value initialiser runs on every re-render, which silently invalidates state.

## <a name="i04"></a>4. `@EnvironmentObject` crash: "may be missing as an ancestor"

**Symptom.** Fatal error: `No ObservableObject of type AppState found. A View.environmentObject(_:) for AppState may be missing as an ancestor of this view.` Crash happens during a navigation push, sheet present, or preview render.

**Root cause.** The object was installed on one branch of the view tree but the crashing view lives in another — typically a sheet, fullScreenCover, `UIHostingController`, or SwiftUI Preview. Sheets and `UIHostingController` content are *separate environment scopes*; they do not inherit from the presenter automatically in all iOS versions.

**Fix.** Re-inject the environment on the presented content: `.sheet(isPresented: $show) { ChildView().environmentObject(appState) }`. For previews, wrap the preview in a `Group` that injects: `ContentView().environmentObject(AppState.preview)`.

**Prevention rule.** At every `.sheet`, `.fullScreenCover`, `.popover`, `UIHostingController` entry, and SwiftUI Preview, re-inject the environment objects the subtree needs — or use plain `@ObservedObject`/`@StateObject` passed as a parameter. Why: environment inheritance is not guaranteed across presentation boundaries.

## <a name="i05"></a>5. SwiftUI list selection / navigation resets on data reload

**Symptom.** User is reading row #47 in a long list. Background refresh completes. List jumps back to the top or the detail view closes.

**Root cause.** The list data was replaced with a new array of model structs that don't preserve identity. SwiftUI re-diffs and treats every row as a new row, invalidating selection and navigation.

**Fix.** Make the model `Identifiable` with a *stable* id (backend primary key, UUID that's persisted — **not** `UUID()` minted at decode time). Pass `id:` explicitly to `ForEach`/`List` if the type isn't `Identifiable`.

**Prevention rule.** Every model shown in a SwiftUI `List` or `ForEach` must have a stable id that survives refetch. If the id is minted client-side, persist it, don't regenerate. Why: SwiftUI diffing uses id to preserve selection, scroll position, and subtree state.

## <a name="i06"></a>6. `NavigationStack` path goes out of sync with data

**Symptom.** User deep-links into a detail view. Back button doesn't work, or taps on the list no longer push. `NavigationStack(path: $path)` and the underlying data diverge.

**Root cause.** Mutating `path` from two sources (programmatic deep link + tap-driven `NavigationLink(value:)`) without a single source of truth. Often, a deep-link handler replaces `path` while a `NavigationLink` concurrently appends.

**Fix.** Make `path` a `@Published` array on the app's router / coordinator, and route *all* navigation through it: `router.push(.detail(id))`, `router.popToRoot()`, `router.handle(deepLink:)`. The view layer binds to `router.path` and does not call `path.append` directly.

**Prevention rule.** Navigation state has exactly one owner. Views describe intent (`router.go(.detail(id))`) and the owner mutates the path. Why: two sources mutating the same stack produce divergence that looks like navigation bugs but is a state-ownership bug.

## <a name="i07"></a>7. SwiftUI sheet shows wrong content after rapid toggle

**Symptom.** User taps row A, sheet opens showing row B's data. Or sheet shows previous content briefly before updating.

**Root cause.** `@State var showSheet = false` + `@State var selected: Model?` is two separate pieces of state. The binding to `showSheet` and the binding to `selected` update out of order, and `.sheet(isPresented:)` captures the *current* value of `selected` at present time, not the value the user tapped.

**Fix.** Use `.sheet(item:)` with an optional identifiable model: `.sheet(item: $selected) { model in DetailView(model: model) }`. This binds the sheet's presence and its content to a *single* piece of state; no race.

**Prevention rule.** Prefer `.sheet(item:)` / `.fullScreenCover(item:)` / `.alert(_:presenting:)` over the `isPresented:` variant whenever the sheet carries data. Why: two-state presentation always has a race window; item-based presentation is atomic.

## <a name="i08"></a>8. Modifier order changes behaviour

**Symptom.** `.padding().background(Color.red)` and `.background(Color.red).padding()` produce different visuals. Tap areas shrink unexpectedly. `.frame().background()` makes the background larger than intended.

**Root cause.** SwiftUI modifiers wrap the view they're applied to. Each modifier produces a new view whose behaviour depends on the wrapped view's bounds at that point in the chain. Order matters.

**Fix.** Think of modifiers as `wrap(wrap(wrap(view, M1), M2), M3)`. The modifier nearest the view is innermost. For tappable areas, `.contentShape(Rectangle())` is often the real fix: it says "treat this region as tappable regardless of visible fill".

**Prevention rule.** For every nontrivial modifier chain, name the bounds it produces. If `.padding()` comes after `.background()`, the padding is outside the color — that's a conscious choice, not a typo. Why: silent behavioural drift from modifier order is the single biggest SwiftUI footgun.

## <a name="i09"></a>9. `onAppear` fires more often than expected

**Symptom.** `onAppear` handler runs twice (or more) for one navigation. Analytics events double-count. Fetches hit the network twice on push.

**Root cause.** SwiftUI calls `onAppear` every time the view enters the view hierarchy, which is not the same as "the user navigated here". A view wrapped in `TabView`, `NavigationSplitView`, or re-identity'd parents can reappear without the user doing anything. Also, `UIHostingController` in a UIKit host calls `viewWillAppear` → `onAppear` pairs that don't map 1:1.

**Fix.** For one-time effects (fetch on first load, analytics), use `.task { }` instead of `.onAppear { }`. `.task` runs once per view identity and cancels its work when the view disappears.

**Prevention rule.** Default to `.task { }` for async fetches and `.onAppear` only for cheap visual setup. Why: `.task` is correct-by-construction for "run once per view lifecycle"; `.onAppear` is a repeatable hook.

## <a name="i10"></a>10. SwiftUI Previews crash with "failed to launch" or blank canvas

**Symptom.** Preview canvas shows "Failed to build", "Preview diagnostics: failed to launch", or renders blank. `#Preview` macro crashes with `EnvironmentObject` missing errors.

**Root cause.** Previews run in a separate process with a stripped environment. They don't get `AppDelegate`, launch flags, or singletons that were set up in `@main`. Anything the view depends on — URLSession mocks, Core Data stack, environment objects, feature flags — has to be explicitly provided.

**Fix.** Build a `.preview` static instance for each model / store and inject it in the `#Preview` block:
`#Preview { ContentView().environmentObject(AppState.preview).modelContainer(.preview) }`.
Wrap side-effectful code in `if !ProcessInfo.processInfo.isPreview { … }` (via an extension on `ProcessInfo` checking `environment["XCODE_RUNNING_FOR_PREVIEWS"] == "1"`).

**Prevention rule.** Every `ObservableObject` / model / store gets a `.preview` instance. Every view with an `@EnvironmentObject` dependency gets a `#Preview` block that injects it. Why: broken previews destroy the SwiftUI feedback loop; the team stops trusting the canvas and regressions compound.

## <a name="i11"></a>11. `@Published` update from background thread — "Publishing changes from background threads"

**Symptom.** Purple runtime warning: `Publishing changes from background threads is not allowed; make sure to publish values from the main thread (via operators like receive(on:)) on model updates.` UI may stall or stutter.

**Root cause.** A `URLSession` completion handler (queue: background) or Combine operator pipeline wrote to a `@Published` property without hopping to main. SwiftUI `ObservableObject` publishers must publish on the main thread.

**Fix.** Hop to main explicitly: `await MainActor.run { self.items = new }`, or on Combine: `.receive(on: DispatchQueue.main)`. Annotating the whole `ObservableObject` with `@MainActor` is often the cleanest answer for view models:
`@MainActor final class FeedViewModel: ObservableObject { @Published var items: [Item] = [] }`.

**Prevention rule.** View models driving SwiftUI are `@MainActor`. All network / disk work inside them is `async` and hops back to main on assignment. Why: SwiftUI diffs on main; off-main mutations race with the diff and produce the purple warning plus visual glitches.

## <a name="i12"></a>12. `async` function called from synchronous context — "async call in a function that does not support concurrency"

**Symptom.** Compile error: `'async' call in a function that does not support concurrency`. Or: app calls an `async` API from a button action and nothing happens.

**Root cause.** Swift concurrency is cooperative — `async` functions must be awaited from another async context. Button actions in SwiftUI are synchronous unless you wrap the call in `Task { … }`.

**Fix.** `Button("Go") { Task { await viewModel.load() } }`. Or give the action itself an async signature when the API supports it (SwiftUI's `.task` modifier, `.refreshable`, async `action:` variants).

**Prevention rule.** When bridging synchronous UI callbacks to async work, use `Task { … }` and attach cancellation to view lifecycle via `.task`. Do not `.sync { await … }` on `DispatchQueue.main` — that deadlocks. Why: the sync/async boundary is cooperative; there is no "block and wait" shortcut on main.

## <a name="i13"></a>13. `@MainActor` isolation violated silently before Swift 6

**Symptom.** Code compiles without warnings on Swift 5.x, crashes or misbehaves in production on main-thread assumptions. Migrating to Swift 6 (strict concurrency) produces a cascade of "non-sendable type crossing actor boundary" errors.

**Root cause.** Pre-Swift 6 checking is advisory. Code that calls into a `@MainActor` method from a non-isolated context compiles but may execute on the wrong thread. The proper checks are gated behind `-strict-concurrency=complete` or Swift 6 mode.

**Fix.** Turn on strict concurrency checking *now* in a non-shipping branch: Build Settings → "Strict Concurrency Checking" = `Complete`. Fix the warnings in batches per module. Annotate view models and UI-facing classes `@MainActor`; mark DTOs `Sendable`; introduce `actor` for shared-mutable state.

**Prevention rule.** New code is written assuming Swift 6 rules even if the compiler setting is still `Minimal`. Annotate actor isolation at the type level, not the method level. Why: Swift 6 is the terminal state; code written under old rules will need to be rewritten.

## <a name="i14"></a>14. `Sendable` warnings after enabling strict concurrency

**Symptom.** `Non-sendable type 'Foo' returned by implicitly asynchronous call from main actor to non-isolated context`. Dozens of warnings after flipping the compiler setting.

**Root cause.** Sending a value across actor boundaries requires the value to be `Sendable` — i.e. thread-safe by construction. Classes aren't `Sendable` by default. Closures that capture non-sendable state aren't sendable.

**Fix.** For value types (struct/enum) with only sendable stored properties: add `: Sendable` to the declaration. For classes: use `final class … : @unchecked Sendable` only if you've *actually* made the class thread-safe (all state behind a lock, or immutable after init). Prefer converting to `struct` where possible. For closures: capture copies of sendable values, not the reference to a view model — or mark the closure `@Sendable` and let the compiler enforce.

**Prevention rule.** New types default to `struct` with sendable fields. Reach for `class` only for identity / reference semantics; when you do, consider whether it's an `actor` instead. Why: `@unchecked Sendable` is a hand-waved promise; every one you write is a future bug.

## <a name="i15"></a>15. Task cancellation ignored — work continues after view disappears

**Symptom.** User navigates away from a screen but the fetch finishes and updates a dismissed view model, writes to disk, or fires a toast on the wrong screen.

**Root cause.** `Task { await longRunning() }` started from a button action is not tied to the view's lifecycle. Swift concurrency supports cancellation, but only for tasks that *check* `Task.isCancelled` / `try Task.checkCancellation()` or use cancellation-aware APIs (`URLSession` async methods do; `Task.sleep` does; hand-rolled loops do not).

**Fix.** Two prongs: (a) start lifecycle-bound work with `.task { }` on the view, which auto-cancels on disappear; (b) inside long-running loops, call `try Task.checkCancellation()` between units of work.

**Prevention rule.** For any async work started from a view, ask "who cancels it when the view goes away?" If the answer is "nobody", rewrite to use `.task` or pass an explicit task handle stored in the view model and `.cancel()` on deinit. Why: orphan tasks update dismissed UI and leak resources in ways that only surface at scale.

## <a name="i16"></a>16. Structured-concurrency `Task { }` captures `self` strongly

**Symptom.** A view model outlives the screen that owned it; Instruments shows a leak anchored on `Task`. Fetch work keeps running, analytics double-fire.

**Root cause.** `Task { await self.fetch() }` implicitly captures `self` *strongly* — the task holds the view model alive until it finishes.

**Fix.** Capture weak: `Task { [weak self] in await self?.fetch() }`. Or scope the task to `.task { }` on a SwiftUI view (the framework owns the lifetime). For UIKit, store the `Task` and cancel in `deinit` or `viewDidDisappear`.

**Prevention rule.** In `class`-based view models, any `Task { }` that runs work across suspension points captures `[weak self]` — unless the task is explicitly meant to keep the owner alive. Why: structured concurrency doesn't save you from reference cycles when the task is unstructured.

## <a name="i17"></a>17. UIKit retain cycle in closure

**Symptom.** Screen doesn't `deinit` after pop. Instruments' Leaks graph shows a cycle through a closure property.

**Root cause.** `self.someCallback = { self.doThing() }` — the closure captures `self` strongly and `self` holds the closure strongly. Classic cycle.

**Fix.** `self.someCallback = { [weak self] in self?.doThing() }`. For code where `self` must be alive during the callback, `[unowned self]` works — at the cost of a crash if the assumption breaks.

**Prevention rule.** Any stored closure property on a class captures `[weak self]` or `[unowned self]` by default; capturing `self` strongly is a decision that needs justification. Why: UIKit view controllers and their delegates are the #1 source of leaks in iOS apps.

## <a name="i18"></a>18. `weak self` causes "self deallocated" crash when force-unwrapped

**Symptom.** Crash on `self!.doThing()` with `Fatal error: Unexpectedly found nil while unwrapping an Optional value`. Happens on low-memory devices or after dismissal animations.

**Root cause.** The fix for a retain cycle (`[weak self]`) makes `self` optional. Force-unwrapping it reintroduces the problem in a new form: instead of a leak, you now crash when the view controller has been deallocated between the async work starting and finishing.

**Fix.** Use `guard let self else { return }` at the top of the closure. Or propagate the `self?.` chain. Never `self!` in a `[weak self]` closure.

**Prevention rule.** `[weak self]` + `guard let self else { return }` is the canonical pair. If you find yourself writing `self!`, stop and rewrite. Why: force-unwrap of `[weak self]` turns a memory bug into a crash without solving either.

## <a name="i19"></a>19. `AVAudioSession` interruption leaves the app muted

**Symptom.** A phone call or Siri invocation arrives during audio playback. After the call ends, the app is silent. User has to force-quit to recover.

**Root cause.** iOS sends an `AVAudioSession.interruptionNotification` with `.began`, then `.ended` with an `optionShouldResume`. The app is responsible for re-activating the session and resuming playback — it does not happen automatically.

**Fix.** Subscribe to the notification, handle both phases, re-activate on `.ended`:
```swift
NotificationCenter.default.addObserver(forName: AVAudioSession.interruptionNotification, object: nil, queue: .main) { note in
    guard let typeValue = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
          let type = AVAudioSession.InterruptionType(rawValue: typeValue) else { return }
    switch type {
    case .began: pause()
    case .ended:
        let opts = AVAudioSession.InterruptionOptions(rawValue: note.userInfo?[AVAudioSessionInterruptionOptionKey] as? UInt ?? 0)
        if opts.contains(.shouldResume) {
            try? AVAudioSession.sharedInstance().setActive(true)
            resume()
        }
    @unknown default: break
    }
}
```

**Prevention rule.** Any app that plays or records audio registers for `AVAudioSession.interruptionNotification` and `routeChangeNotification`, and has a manual-test checklist for the phone-call, Siri, alarm, and AirPods-disconnect scenarios. Why: audio interruption is the single most common "works on my device" bug in media apps.

## <a name="i20"></a>20. `AVAudioPlayer` silently fails in background

**Symptom.** Music stops when the app backgrounds, even though the capability is for a music app.

**Root cause.** Two things must both be true: (1) the target's "Background Modes" capability has "Audio, AirPlay, and Picture in Picture" enabled, and (2) `AVAudioSession` is configured with category `.playback` (not `.soloAmbient`, which is the default) *and* activated.

**Fix.** `try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: []); try AVAudioSession.sharedInstance().setActive(true)` — and enable the Background Modes capability in the target's Signing & Capabilities tab.

**Prevention rule.** Media playback is a two-step setup (category + capability) and silently degrades if either is missing. Add an automated test that asserts `AVAudioSession.sharedInstance().category == .playback` after app launch. Why: the default category is designed to be quiet; you have to opt in.

## <a name="i21"></a>21. `URLSession` upload task times out only on cellular

**Symptom.** Large uploads succeed on Wi-Fi, time out on cellular. Or work in debug, fail in release.

**Root cause.** `URLSessionConfiguration.default.timeoutIntervalForRequest` defaults to 60 seconds. On cellular, the *initial connection* can take longer than that, let alone the transfer. Background uploads have a separate timeout (`timeoutIntervalForResource`, default 7 days) but require `URLSessionConfiguration.background`.

**Fix.** For large transfers, use a `.background(withIdentifier:)` configuration and `URLSession` with a delegate. Set `timeoutIntervalForResource` to the realistic transfer ceiling. Never bump `timeoutIntervalForRequest` past ~120 s — if individual requests are taking longer, the transport is the problem, not the timeout.

**Prevention rule.** Uploads / downloads > a few MB use a background session with a delegate. Request timeout stays short (per-packet); resource timeout covers the whole transfer. Why: default timeouts are tuned for API calls, not media uploads.

## <a name="i22"></a>22. App Transport Security blocks HTTP in release

**Symptom.** In debug, an HTTP URL works. In release (or on device), `URLSession` fails with `kCFErrorDomainCFNetwork` error code `-1022` ("The resource could not be loaded because the App Transport Security policy requires the use of a secure connection.").

**Root cause.** ATS, on by default since iOS 9, forbids cleartext HTTP. The debug build may have been hitting a localhost exception or a proxy that upgraded.

**Fix.** Use HTTPS. If you must hit HTTP (developer box, IoT device on LAN), add a narrow `NSAppTransportSecurity` / `NSExceptionDomains` entry for *exactly* the host, or `NSAllowsLocalNetworking` for LAN-only. Never ship `NSAllowsArbitraryLoads: true` — it blocks App Review.

**Prevention rule.** Every URL the app ever constructs is HTTPS. The only HTTP allowance is explicit, hostname-scoped, and annotated with a comment explaining why and when it can be removed. Why: ATS is a privacy / security guarantee users rely on; arbitrary-loads opt-outs get apps rejected.

## <a name="i23"></a>23. `URLSession` completion handler called on background queue — UI doesn't update

**Symptom.** Data arrives (log prints confirm it), but the UI doesn't redraw. Or a purple warning fires about publishing from background.

**Root cause.** `URLSession.shared.dataTask(with:completionHandler:)` invokes the handler on a delegate queue — *not* main. Assigning to a `@Published` property there triggers the background-publish warning.

**Fix.** Prefer the async variant: `let (data, _) = try await URLSession.shared.data(from: url)`. If you're on `@MainActor`, the continuation resumes on main. For the completion variant, hop explicitly: `DispatchQueue.main.async { self.items = decoded }`.

**Prevention rule.** New networking is written with `async`/`await` in a `@MainActor`-isolated view model; legacy completion-handler networking is wrapped in `withCheckedContinuation` at the boundary and the rest of the app is main-actor. Why: queue discipline is easy to get wrong with callbacks; actors enforce it at compile time.

## <a name="i24"></a>24. Core Data: "context is a different queue" crash

**Symptom.** `'NSGenericException', reason: 'Data access was attempted on a different queue than the one the context was created on.'` Crashes on random API boundaries.

**Root cause.** `NSManagedObjectContext` is queue-confined. `viewContext` is main-queue; `newBackgroundContext()` has its own private queue. Crossing a managed object between contexts without going through `objectID` causes the crash.

**Fix.** Never pass `NSManagedObject` instances across queues. Pass the `objectID`, re-fetch in the target context. Wrap writes in `context.performAndWait { … }` (sync) or `context.perform { … }` (async). In Swift concurrency, use `NSManagedObjectContext.perform` which is already async-aware.

**Prevention rule.** The only way a managed object crosses a queue boundary is via its `objectID`. Every `perform`/`performAndWait` block is contained; no captured `NSManagedObject` escapes it. Why: Core Data's threading rules are strict and the crash has no helpful stack trace when violated.

## <a name="i25"></a>25. Core Data: merge policy silently drops changes

**Symptom.** Two contexts save in quick succession; one set of changes disappears from disk.

**Root cause.** Default merge policy is `NSErrorMergePolicy` (throws on conflict) or — worse if mistakenly set — `NSOverwriteMergePolicyType`, which wins by overwrite without reporting what was lost.

**Fix.** Set `context.mergePolicy = NSMergeByPropertyObjectTrumpMergePolicy` (external state wins, predictable for sync). Or use `NSMergeByPropertyStoreTrumpMergePolicy` (store wins). Always enable `persistentContainer.viewContext.automaticallyMergesChangesFromParent = true` on the view context so it reflects background writes.

**Prevention rule.** Merge policy is chosen explicitly per persistent container and documented. Background contexts write; `viewContext` auto-merges; conflict behaviour is a design decision, not a default. Why: silent overwrites are the hardest Core Data bug to trace.

## <a name="i26"></a>26. `NSFetchedResultsController` misses updates after background insert

**Symptom.** Inserts and updates from a background context don't show up in the UI until the app is relaunched.

**Root cause.** The FRC's context isn't receiving the background context's save notifications. Either `automaticallyMergesChangesFromParent` is off, or the background context is a *sibling* (not child) of `viewContext` and `NSManagedObjectContextDidSave` isn't being merged.

**Fix.** Use `persistentContainer.newBackgroundContext()` and enable `viewContext.automaticallyMergesChangesFromParent = true`. For manually-constructed sibling contexts, listen for `NSManagedObjectContextDidSave` and call `viewContext.mergeChanges(fromContextDidSave:)`.

**Prevention rule.** Every Core Data stack has exactly one parent and the view context auto-merges. Any manual sibling context is documented and explicitly merged. Why: the propagation graph of `save → merge → UI` is invisible; get it wrong once and updates silently stop.

## <a name="i27"></a>27. Background task expires before work completes

**Symptom.** `BGAppRefreshTask` / `BGProcessingTask` is scheduled, logs show it started, but the work never finishes. Sometimes `expirationHandler` fires and terminates partial work.

**Root cause.** `BGTaskScheduler` gives the app seconds (refresh) to minutes (processing) and *only when iOS decides*. Tasks must (a) set `expirationHandler` to cancel gracefully, (b) call `setTaskCompleted(success:)` before returning, and (c) be registered in `Info.plist` under `BGTaskSchedulerPermittedIdentifiers`.

**Fix.** Register identifiers at launch: `BGTaskScheduler.shared.register(forTaskWithIdentifier: "...", using: nil) { task in … }`. Inside, wire cancellation: `task.expirationHandler = { operation.cancel() }`; and at the end: `task.setTaskCompleted(success: !operation.isCancelled)`.

**Prevention rule.** Background work is idempotent (can be interrupted and retried) and completes in chunks each bounded by the scheduler's budget. State is persisted between chunks. Why: iOS does not guarantee background execution time; code that assumes it will finish in one call is a lottery.

## <a name="i28"></a>28. Deep link opens but state isn't restored

**Symptom.** Tapping a push notification or universal link opens the app to the root screen instead of the intended detail. Sometimes works from cold launch, fails from warm launch (or vice versa).

**Root cause.** Deep links can arrive through multiple entry points (`application(_:continue:restorationHandler:)`, `scene(_:continue:)`, `application(_:open:options:)`, notification response). Each path must route to the same handler. Often one path is implemented, another isn't.

**Fix.** Centralise: one `DeepLinkRouter` type with a single `handle(url:)` or `handle(activity:)` method. Every AppDelegate / SceneDelegate entry calls into it. The router builds a `NavigationStack` path and applies it.

**Prevention rule.** There is one deep-link router. All OS entry points are thin adapters that convert the input to a `DeepLink` enum and call `router.handle(_:)`. Why: N entry points × M destinations = N·M bugs; one router is N + M.

## <a name="i29"></a>29. Universal links open in Safari, not the app

**Symptom.** Tapping a `https://yourapp.com/foo` link opens Safari instead of the app. Associated Domains are configured; works in TestFlight; fails in App Store build or on a colleague's device.

**Root cause.** Universal links require (a) Associated Domains entitlement with `applinks:yourapp.com`, (b) an `apple-app-site-association` (AASA) file at `https://yourapp.com/.well-known/apple-app-site-association` served over HTTPS with correct MIME type (`application/json`) and no redirects, (c) the app installed and *never dismissed* from Safari (users can swipe-up to permanently prefer Safari for a domain).

**Fix.** Validate the AASA via `https://app-site-association.cdn-apple.com/a/v1/yourapp.com` (Apple's CDN fetches once per install). If the user opted into Safari, the cure is deleting and reinstalling the app, then tapping a link from Mail/Messages (where long-press reveals the "Open in …" choice).

**Prevention rule.** CI validates the AASA file structure and CDN cache. A manual-test SOP covers fresh-install and opted-into-Safari-then-recover. Why: universal-link breakage is invisible — the link "just opens Safari", and users assume it's intended.

## <a name="i30"></a>30. Keyboard obscures text field in scroll view

**Symptom.** User taps a text field near the bottom; keyboard rises; field is hidden behind it.

**Root cause.** UIKit `UIScrollView` doesn't automatically inset for the keyboard. `UITableViewController` used to do it; `UICollectionView` doesn't. SwiftUI `ScrollView` handles it automatically on iOS 14+ *for its own first responder chain*, but not when the field is inside a `UIHostingController` embedded in UIKit.

**Fix.** For UIKit: observe `UIResponder.keyboardWillShowNotification`, adjust `contentInset.bottom` and `scrollIndicatorInsets.bottom`, reverse on hide. For SwiftUI with a UIKit host: wrap the host in a container that forwards keyboard insets via `safeAreaInsets` adjustments.

**Prevention rule.** Any screen with a text input below the mid-screen line has a manual test: "type on smallest supported device, keyboard up, confirm caret visible". Why: this bug never reproduces on the dev's main device; it ships.

## <a name="i31"></a>31. UIScene migration — `application(_:didFinishLaunching)` side effects lost

**Symptom.** After enabling `UIApplicationSceneManifest` in `Info.plist`, setup code that lived in `application(_:didFinishLaunchingWithOptions:)` silently stops running, runs twice, or runs after the first UI has already appeared.

**Root cause.** The app-delegate lifecycle and the scene-delegate lifecycle are not the same. `didFinishLaunching` runs once per app process; `scene(_:willConnectTo:options:)` runs once per scene (and a multi-window iPad app has many). Code that assumed "there is one window" is no longer correct.

**Fix.** Classify each setup step: *app-wide-one-time* (analytics SDK init, crash reporter) stays in `AppDelegate`. *Per-scene* (root view construction, incoming URL / activity handling) moves to `SceneDelegate`. Deep-link handling lives in the scene; most `window.rootViewController` code moves.

**Prevention rule.** When adopting scenes, audit every `application(_:…)` method and decide per-call whether it's app-level or scene-level. Don't leave code in both. Why: scene adoption is mechanical on the happy path and subtle everywhere else; silent duplication / omission is the failure mode.

## <a name="i32"></a>32. `Codable` decoding silently drops optional keys with wrong casing

**Symptom.** An API field named `user_name` never populates on a Swift struct with `var userName: String?`. No error, just `nil`.

**Root cause.** `Codable` maps names 1:1 by default. `userName` ≠ `user_name`. An `Optional` field that fails to decode doesn't throw — it becomes `nil`. So the symptom is invisible unless you check.

**Fix.** Set the decoder's key strategy: `decoder.keyDecodingStrategy = .convertFromSnakeCase`. For irregular mappings, write a `CodingKeys` enum: `enum CodingKeys: String, CodingKey { case userName = "user_name" }`.

**Prevention rule.** One `JSONDecoder` per layer, configured once with `.convertFromSnakeCase` and the date strategy the API uses. All DTOs share it. Write a decode-round-trip test for every API response type. Why: silent-nil is the worst kind of bug — it passes QA and surfaces as "the feature just doesn't work for some users".

## <a name="i33"></a>33. `Date` decoded off by hours because of timezone assumption

**Symptom.** Dates from the backend display in the right hour on dev's machine, off by N hours on users'.

**Root cause.** `JSONDecoder().dateDecodingStrategy = .iso8601` assumes the string carries a timezone (`…Z` or `…+05:30`). If the backend sends a naïve `2026-04-21T09:00:00` with no zone, `.iso8601` will fail; some teams fall back to a custom formatter that interprets the string in the *device's* local zone, which varies per user.

**Fix.** Fix the contract: backend sends UTC with a `Z` suffix (or an explicit offset); client decodes with `.iso8601` or `.iso8601withFractionalSeconds`. If you can't change the backend, pin the decoding formatter to a specific zone (UTC) and apply the user's zone only at display time.

**Prevention rule.** Dates cross process boundaries as UTC with an explicit marker. Timezone is applied once, at the UI layer, using the user's current zone — never baked into stored data or API payloads. Why: the "off by hours" bug only reproduces when a developer travels or a user does; untraceable in bug reports.
