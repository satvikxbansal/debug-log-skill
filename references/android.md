# Android — error catalog

Covers: Kotlin-on-Android surface, Jetpack Compose (recomposition, state, lifecycle), foreground services (Android 14 rules), Accessibility services, WindowManager overlays, Hilt / DI, Room, DataStore, WorkManager, permissions, R8 / ProGuard, deep links, configuration changes, notifications, Play Store policies that bite at runtime.

Each entry follows the same shape: **Symptom → Root cause → Fix → Prevention rule.**

## Table of contents

1. [Android 14: `MissingForegroundServiceTypeException`](#a01)
2. [Compose: recomposition loop from unstable state reads](#a02)
3. [Compose: `remember` without a key resets on config change](#a03)
4. [Compose: reading a `MutableState` from a background thread](#a04)
5. [Compose in `WindowManager` overlay: crashes on first recomposition](#a05)
6. [Overlay window steals IME input from the target app](#a06)
7. [`FLAG_SECURE` windows return blank screenshots](#a07)
8. [`AccessibilityService.takeScreenshot` only exists on API 30+](#a08)
9. [Accessibility service killed and not restarted](#a09)
10. [Activity recreated on rotation loses ViewModel data](#a10)
11. [`LiveData` / `StateFlow` fires stale value on config change](#a11)
12. [Hilt: "Cannot provide X without @Inject constructor" on a Compose screen](#a12)
13. [`hiltViewModel()` + Navigation: ViewModel scoped to wrong back-stack entry](#a13)
14. [Room: "Cannot access database on main thread"](#a14)
15. [Room migration missing — "A migration from N to N+1 was required"](#a15)
16. [Room returns empty list on first query after insert](#a16)
17. [DataStore write races with another process](#a17)
18. [WorkManager one-time work runs twice](#a18)
19. [Doze / App Standby: periodic work doesn't run](#a19)
20. [Runtime permission request doesn't show dialog the second time](#a20)
21. [`POST_NOTIFICATIONS` — notifications silently dropped on Android 13+](#a21)
22. [`SCHEDULE_EXACT_ALARM` revocable on Android 14](#a22)
23. [R8 / ProGuard strips a class used via reflection (JSON, DI, serialization)](#a23)
24. [R8 strips Compose `@Preview` providers — release builds crash](#a24)
25. [Deep link intent filter swallowed by another activity](#a25)
26. [`onNewIntent` not called — stale `getIntent()`](#a26)
27. [`Context` leak via a retained singleton](#a27)
28. [`ANR` from long-running `BroadcastReceiver.onReceive`](#a28)
29. [`StrictMode` disk / network on main thread in release only](#a29)
30. [Edge-to-edge insets double-apply on Android 15](#a30)
31. [`targetSdk` bump silently changes background-location behaviour](#a31)
32. [Gradle: "Unresolved reference" after AGP / Compose BOM bump](#a32)

---

## <a name="a01"></a>1. Android 14: `MissingForegroundServiceTypeException`

**Symptom.** On Android 14 (API 34), `startForeground()` crashes with `android.app.MissingForegroundServiceTypeException: Starting FGS without a type…`. Service that worked on API 33 dies immediately.

**Root cause.** API 34 requires every foreground service to declare a specific `android:foregroundServiceType` in the manifest *and* pass the matching type to `startForeground(id, notification, type)`. The old typeless API is deprecated and crashes.

**Fix.** In `AndroidManifest.xml`:
```xml
<service
    android:name=".CaptureService"
    android:foregroundServiceType="mediaProjection"
    android:exported="false" />
<service
    android:name=".AssistantService"
    android:foregroundServiceType="specialUse|microphone"
    android:exported="false">
  <property android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE"
            android:value="on-device-assistant-overlay" />
</service>
```
Add the matching permissions: `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MEDIA_PROJECTION`, `FOREGROUND_SERVICE_MICROPHONE`, `FOREGROUND_SERVICE_SPECIAL_USE`. Call `startForeground(id, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)`.

**Prevention rule.** Every `<service>` that calls `startForeground` declares `android:foregroundServiceType`, and the runtime call passes the matching `ServiceInfo.FOREGROUND_SERVICE_TYPE_*`. Why: API 34 made this mandatory with no graceful fallback; crash is immediate and user-facing.

## <a name="a02"></a>2. Compose: recomposition loop from unstable state reads

**Symptom.** A screen recomposes continuously — frame rate drops, CPU stays high, logs show the same `Composable` emitting on every frame.

**Root cause.** A composable reads a value that changes every composition (e.g., `remember { mutableStateOf(System.currentTimeMillis()) }` without a key, or a parent passes a new lambda / list instance every render, which the child reads into state).

**Fix.** Hoist unstable objects out of composition: pass stable primitives or remember them keyed by the data that should invalidate them. Use `derivedStateOf` for values computed from state. For lambdas that shouldn't change, use `remember { { … } }`.

**Prevention rule.** If a composable recomposes more than once per user event, profile with Compose's `Recomposition Counts` (Layout Inspector). Fix by making inputs stable or memoising. Why: unstable state reads escalate from "slow screen" to battery regression before anyone notices.

## <a name="a03"></a>3. Compose: `remember` without a key resets on config change

**Symptom.** User rotates the device. Scroll position, input draft, tab selection — all reset.

**Root cause.** `remember { … }` survives recomposition but not configuration changes (rotation, theme, font size, language). For that, use `rememberSaveable { … }`, which persists via `Bundle`.

**Fix.** `rememberSaveable { mutableStateOf("") }` for strings / numbers / parcelables. For complex types, provide a `Saver`. For scroll state, `rememberLazyListState()` is already saveable.

**Prevention rule.** Any state that would annoy the user if it reset on rotation uses `rememberSaveable` or lives in a `ViewModel`. Why: Compose's `remember` is per-composition-instance, not per-process; config changes are a common path that recreates the composition.

## <a name="a04"></a>4. Compose: reading a `MutableState` from a background thread

**Symptom.** Purple LogCat warning or `IllegalStateException: Reading states is only allowed from the main thread`. Or UI updates silently fail to reflect a value change.

**Root cause.** `mutableStateOf`, `MutableStateFlow.collectAsState`, and `@Published`-equivalent Compose state are main-thread-only on write. Writing from a coroutine dispatched to `Dispatchers.IO` or a JNI callback violates this.

**Fix.** Hop dispatcher before the write: `withContext(Dispatchers.Main) { state.value = newValue }`. Or shape the code so state lives in a `ViewModel` that exposes `StateFlow` and the collector is `LaunchedEffect`/`collectAsState` on main.

**Prevention rule.** Compose state is written on main only. ViewModels expose cold `Flow` / hot `StateFlow` and the composable collects on the main dispatcher. Never assign to `mutableStateOf` from outside the composition root. Why: cross-thread writes to Compose state produce read-inconsistency that is not guaranteed to warn.

## <a name="a05"></a>5. Compose in `WindowManager` overlay: crashes on first recomposition

**Symptom.** Overlay view created with `WindowManager.addView(ComposeView(ctx).apply { setContent { … } }, params)` crashes on first interaction with `IllegalStateException: ViewTreeLifecycleOwner not found` or `…SavedStateRegistryOwner not found`.

**Root cause.** Compose requires a `LifecycleOwner`, `ViewModelStoreOwner`, and `SavedStateRegistryOwner` attached to the view. Activity-hosted `ComposeView` gets these automatically; a service-hosted one does not.

**Fix.** Wire them manually:
```kotlin
class OverlayLifecycleHost : SavedStateRegistryOwner, ViewModelStoreOwner, LifecycleOwner {
    private val lifecycleRegistry = LifecycleRegistry(this)
    private val store = ViewModelStore()
    private val savedStateRegistryController = SavedStateRegistryController.create(this)
    override val lifecycle: Lifecycle get() = lifecycleRegistry
    override val viewModelStore: ViewModelStore get() = store
    override val savedStateRegistry get() = savedStateRegistryController.savedStateRegistry
    fun attach() { savedStateRegistryController.performRestore(null); lifecycleRegistry.currentState = Lifecycle.State.RESUMED }
    fun detach() { lifecycleRegistry.currentState = Lifecycle.State.DESTROYED; store.clear() }
}
// after addView:
host.attach()
view.setViewTreeLifecycleOwner(host)
view.setViewTreeViewModelStoreOwner(host)
view.setViewTreeSavedStateRegistryOwner(host)
```

**Prevention rule.** Any `ComposeView` added outside an `Activity` (service overlay, custom `Window`, widget host) comes with an explicit lifecycle host. Set all three owners before the first `setContent`. Why: the owners are assumed-present by Compose; missing one crashes on first IME, gesture, or state save.

## <a name="a06"></a>6. Overlay window steals IME input from the target app

**Symptom.** When an overlay window is showing, the user can't type into apps underneath — the keyboard responds to the overlay or doesn't come up at all.

**Root cause.** `WindowManager.LayoutParams.flags` defaults (or a carelessly set `FLAG_NOT_TOUCHABLE` clearing) leave the overlay as a focusable window. A focusable top window eats IME events.

**Fix.** A small state machine on flags:
```kotlin
fun overlayFlagsFor(mode: OverlayMode): Int = when (mode) {
    OverlayMode.IDLE ->
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
        WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
    OverlayMode.CHAT -> // the user types into OUR overlay
        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
}
wm.updateViewLayout(overlay, params.apply { flags = overlayFlagsFor(mode) })
```

**Prevention rule.** Focusability on overlay windows is a mode, not a default. Declare the mode (idle → not focusable, chat → focusable) and update flags when the mode transitions. Why: a focusable idle overlay is a silent input-black-hole and users uninstall before filing a bug.

## <a name="a07"></a>7. `FLAG_SECURE` windows return blank screenshots

**Symptom.** App takes a screenshot for its own features. Screenshot is entirely black (or mostly black with only the status bar). User sees a "nothing captured" toast even though the screen has content.

**Root cause.** The target app set `WindowManager.LayoutParams.FLAG_SECURE` on its window — banking, password managers, DRM video, incognito Chrome, and many fintech apps do this. The OS returns a black frame buffer to both `MediaProjection` and `AccessibilityService.takeScreenshot`.

**Fix.** Detect it and fail gracefully. Do not retry:
```kotlin
sealed interface CaptureResult {
    data class Bitmap(val bitmap: android.graphics.Bitmap) : CaptureResult
    object SecureWindow : CaptureResult
    object NotPermitted : CaptureResult
    object Unsupported : CaptureResult
    data class Failed(val reason: String) : CaptureResult
}

val window = accessibilityService.windows.firstOrNull { it.root?.packageName == focusedPkg }
if (window?.isSecure == true) return CaptureResult.SecureWindow

// After capture, sample the bitmap: if > 99% of pixels are (0,0,0), treat as SecureWindow.
```
When `SecureWindow` is returned, surface a user-visible explanation (not a retry) and don't spend tokens calling the LLM with a black image.

**Prevention rule.** Any code path that captures screen pixels checks `windowInfo.isSecure` *and* samples the result for all-black before treating the bitmap as real. Return a distinct `SecureWindow` outcome. Why: silent black-frame submission wastes tokens, produces nonsense LLM output, and confuses users who don't understand why the assistant is "seeing nothing".

## <a name="a08"></a>8. `AccessibilityService.takeScreenshot` only exists on API 30+

**Symptom.** `NoSuchMethodError` on Android 10 (API 29) and older, or a compile error if `minSdk` < 30 and the call site isn't guarded.

**Root cause.** The `AccessibilityService.takeScreenshot(displayId, executor, callback)` API was added in API 30. Older OS versions need `MediaProjection` (API 21+) with explicit user consent.

**Fix.** Branch by OS version:
```kotlin
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
    accessibilityService.takeScreenshot(Display.DEFAULT_DISPLAY, mainExecutor, callback)
} else {
    mediaProjectionCapture(callback) // separate code path, different permission UX
}
```
Gate call sites with `@RequiresApi(Build.VERSION_CODES.R)` where appropriate.

**Prevention rule.** Every platform API not available on `minSdk` is guarded by `Build.VERSION.SDK_INT` check with a tested fallback, and the site is annotated with `@RequiresApi`. Why: `NoSuchMethodError` slips through unit tests and surfaces on older devices in the field.

## <a name="a09"></a>9. Accessibility service killed and not restarted

**Symptom.** After a while, or after a device reboot, the assistant stops responding. User has to re-enable the accessibility service in Settings.

**Root cause.** Accessibility services can be killed by the OS (low memory, user action, OEM battery optimisations). Android does *not* always re-enable them on reboot, and some OEM skins (MIUI, ColorOS, OneUI) revoke accessibility permission aggressively.

**Fix.** (a) In `AccessibilityServiceInfo`, set `FLAG_RETRIEVE_INTERACTIVE_WINDOWS` and appropriate event types to keep the service active. (b) On startup (app process launch via another trigger — broadcast receiver, scheduled work, user tap), check `AccessibilityServiceInfo.getSettingsActivityName()`-style heuristics (actually: iterate `AccessibilityManager.getEnabledAccessibilityServiceList(...)`) to detect disabled state and prompt the user. (c) For OEM-specific kill behaviours, document "add app to protected / auto-start list" with screenshots per OEM.

**Prevention rule.** The app has a health-check that detects "accessibility service is disabled" on every cold start and surfaces a one-tap re-enable flow. Why: silent-disable is the #1 support ticket for accessibility-backed apps and OEM behaviour diverges wildly.

## <a name="a10"></a>10. Activity recreated on rotation loses ViewModel data

**Symptom.** User rotates device. In-flight request starts over. Form resets. Loading spinner flashes then goes away.

**Root cause.** The activity was instantiated anew, and so was the view model — because `ViewModelProvider(this)[MyVM::class.java]` was called with a wrong scope, or the VM was built by hand without going through the factory.

**Fix.** Use `by viewModels()` (activity-scoped) or `by activityViewModels()` (fragment sharing activity) or `hiltViewModel()` (Compose + Hilt). Never `MyViewModel()` with a raw constructor from UI.

**Prevention rule.** Every ViewModel is obtained via a Google-provided delegate (`viewModels`, `hiltViewModel`, `viewModel()`) — never newed up. That's what preserves instance across config change. Why: config-change survival is the core value of the ViewModel; bypassing the factory throws it away silently.

## <a name="a11"></a>11. `LiveData` / `StateFlow` fires stale value on config change

**Symptom.** Snackbar or navigation event fires a second time after rotation.

**Root cause.** `LiveData` and `StateFlow` are stateful — on resubscription they emit the current (last) value. A one-shot event ("show toast") modelled as `LiveData<String>` is replayed on every observer re-attach.

**Fix.** Model events differently from state. Use `Channel<Event>` + `receiveAsFlow()` (consumed once) or `SharedFlow(replay = 0)`. For `LiveData`, wrap in an `Event` class with a `getContentIfNotHandled()` consumer. Settled state (loading, data, error) stays in `StateFlow`; transient events go through channels.

**Prevention rule.** State is rendered (idempotent); events are consumed (one-shot). Pick the primitive that matches — never put "show toast" in `StateFlow`. Why: replay-on-subscribe is correct for state and wrong for events; mixing them produces double-fires that only appear on rotation.

## <a name="a12"></a>12. Hilt: "Cannot provide X without @Inject constructor" on a Compose screen

**Symptom.** Build fails: `[Hilt] Cannot provide com.example.MyRepo without an @Inject constructor or @Provides-annotated method`.

**Root cause.** Either `MyRepo` is missing `@Inject constructor`, or a binding is declared in a `@Module` that isn't installed in the right `@InstallIn` scope, or the class is in a module that doesn't apply the Hilt plugin.

**Fix.** Most common fixes, in order of frequency: (a) add `@Inject constructor(...)` on `MyRepo`; (b) confirm the Gradle module applies `dagger.hilt.android.plugin`; (c) for interfaces, add `@Binds` in an `@Module @InstallIn(SingletonComponent::class)`; (d) for types you don't own, add `@Provides`.

**Prevention rule.** When adding a new Gradle module, the first commit applies the Hilt plugin and adds a smoke-test binding. Compose screens that need injection use `hiltViewModel()`. Why: Hilt errors are compile-time and look cryptic; a module without the plugin produces the same error as a missing `@Inject`.

## <a name="a13"></a>13. `hiltViewModel()` + Navigation: ViewModel scoped to wrong back-stack entry

**Symptom.** Two screens that both call `hiltViewModel<FooViewModel>()` share state unexpectedly, or a screen's VM survives too long / too short.

**Root cause.** `hiltViewModel()` scopes to the nearest `ViewModelStoreOwner`. In Jetpack Navigation Compose, each composable in the graph *is* a `NavBackStackEntry` — so VMs are scoped per destination. But if you call `hiltViewModel()` outside the destination's `composable { }` block, the scope is wrong.

**Fix.** For per-screen VMs: call `hiltViewModel()` inside the `composable(route = …) { hiltViewModel<FooViewModel>() }` block. For shared-across-flow VMs: call `hiltViewModel(navController.getBackStackEntry("flow/parent"))` with the parent route as the scope owner.

**Prevention rule.** Every `hiltViewModel()` call documents (in the parameter) which back-stack entry owns it. The scope is explicit: self, parent, or nav graph. Why: implicit scope rules silently produce shared or leaked VMs, which manifest as "my state leaked between screens" bugs.

## <a name="a14"></a>14. Room: "Cannot access database on main thread"

**Symptom.** `IllegalStateException: Cannot access database on the main thread since it may potentially lock the UI for a long period of time`.

**Root cause.** A synchronous DAO method (returning `List<…>` or `Entity`) was called from the main thread. Room forbids it by default.

**Fix.** Make DAO methods `suspend` (for one-shot reads/writes) or return `Flow<List<…>>` (for observation). Call suspending methods from `viewModelScope.launch { … }`. Do not enable `allowMainThreadQueries()` — it papers over the problem.

**Prevention rule.** Every DAO method is `suspend` or returns `Flow`. Writers are `suspend`, observers are `Flow`. Why: Room's main-thread block is a UI-latency guarantee; bypassing it ships ANRs to slower devices.

## <a name="a15"></a>15. Room migration missing — "A migration from N to N+1 was required"

**Symptom.** Release build crashes on app upgrade: `java.lang.IllegalStateException: A migration from 3 to 4 was required but not found.`. App loses user data until uninstalled and reinstalled.

**Root cause.** The schema version was bumped (new column, renamed table, changed type) without supplying a `Migration`. Room refuses to destructively recreate by default in release.

**Fix.** Write the migration: `val MIGRATION_3_4 = object : Migration(3, 4) { override fun migrate(db: SupportSQLiteDatabase) { db.execSQL("ALTER TABLE user ADD COLUMN email TEXT") } }` and pass it to the builder: `.addMigrations(MIGRATION_3_4)`. In development, use `.fallbackToDestructiveMigration()` only behind a build-type check — never in release.

**Prevention rule.** Any `@Entity` change that affects the schema is accompanied by (a) a bumped version, (b) a matching `Migration` object, (c) a test that migrates from N → N+1 with seeded data. CI runs the migration tests. Why: Room won't drop tables in release; a missing migration is an unrecoverable crash on upgrade.

## <a name="a16"></a>16. Room returns empty list on first query after insert

**Symptom.** Code does `dao.insert(item)` then `dao.getAll()` and gets back an empty list, even though the insert succeeded.

**Root cause.** The two calls aren't in the same transaction, and the observer was set up before the insert ran. Or the DAO returns `Flow<List<T>>` but the test harness is consuming only the initial emission.

**Fix.** For consistent reads, wrap in a single transaction: `@Transaction suspend fun insertAndFetch(item: T): List<T>`. For `Flow` observation, collect `first { it.isNotEmpty() }` in the test (or use `Turbine`).

**Prevention rule.** Insert-then-read flows are either inside a `@Transaction`, or tested with `Flow` semantics (expect multiple emissions). Why: the "empty result" isn't a bug in Room; it's a bug in the caller assuming synchronous visibility.

## <a name="a17"></a>17. DataStore write races with another process

**Symptom.** Multi-process apps (main + widget, or main + service in `:remote` process) show stale values. Widget never updates, or shows last-week's state.

**Root cause.** Preferences DataStore is single-process by design. Writes from process A don't reach process B. The `dataStore` delegate was declared twice.

**Fix.** Use `MultiProcessDataStore` (androidx.datastore:datastore-preferences + :multiprocess) or move cross-process shared state to a `ContentProvider`-backed store. For config flags that rarely change, a broadcast + re-read works.

**Prevention rule.** Before adding DataStore, audit which process each reader / writer runs in. Declare single-process or multi-process explicitly. Why: the single-process default is silent — there's no crash, just a stale widget.

## <a name="a18"></a>18. WorkManager one-time work runs twice

**Symptom.** Upload job fires twice for one user action. Analytics double-count.

**Root cause.** Either the work was enqueued without an `ExistingWorkPolicy` and the previous enqueue hadn't finished, or the worker returned `Result.retry()` when it shouldn't have (transient vs permanent error confusion).

**Fix.** Use `enqueueUniqueWork(name, ExistingWorkPolicy.KEEP, request)` or `ExistingWorkPolicy.REPLACE`. Inside the worker, distinguish retryable transport errors (`Result.retry`) from permanent ones (`Result.failure`). Make the work idempotent — inserting with a de-dupe key — so that a retry is safe even if it duplicates.

**Prevention rule.** Every WorkManager job is either unique-by-name with a stated policy, or idempotent on the server. No job relies on "it will only run once". Why: WorkManager is designed to over-deliver; at-least-once is the contract.

## <a name="a19"></a>19. Doze / App Standby: periodic work doesn't run

**Symptom.** "Sync every 15 minutes" fires regularly in debug, drops to once-every-few-hours in production.

**Root cause.** Doze mode defers non-critical wakeups when the device is idle. `PeriodicWorkRequest` minimum interval is 15 minutes, but it runs inside maintenance windows. App Standby Buckets (active, working set, frequent, rare, restricted) further throttle — apps users don't open slide to `rare`/`restricted` and get one or two syncs per day.

**Fix.** Accept the scheduling as "eventually consistent". For user-visible freshness, sync on screen-unlock (via `BROADCAST_ACTION_USER_PRESENT`) or app foregrounding. For critical time-sensitive alerts, use `setExpedited()` (Android 12+) sparingly — each expedited job consumes a quota. Do not request `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` unless you have a Play Store-approvable reason.

**Prevention rule.** Periodic work is a hint, not a guarantee. User-visible "latest" data is refreshed on app open. Critical pushes go through FCM high-priority messages. Why: battery restrictions make background scheduling fundamentally unreliable; designing around it saves months of "why doesn't my sync work" debugging.

## <a name="a20"></a>20. Runtime permission request doesn't show dialog the second time

**Symptom.** User taps "Deny" on camera permission. App's "Open Camera" button does nothing — no dialog, no feedback.

**Root cause.** After the user denies twice, Android sets the "Don't ask again" flag automatically. `requestPermissions(...)` returns `PERMISSION_DENIED` without showing UI. Checking `shouldShowRequestPermissionRationale()` returns `false` in this state (same as "first time ever asked"), which trips a lot of apps.

**Fix.** A three-state permission flow: (a) not asked — `shouldShowRationale == false` and `checkSelfPermission == DENIED` — call `request`; (b) asked and should-show-rationale — show explainer, then call `request`; (c) permanently denied — `shouldShowRationale == false` after the user clicked deny — send the user to the app's settings screen via `Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)`.

**Prevention rule.** Permission UX is a state machine with an explicit "permanently denied" branch that navigates to Settings. Never silently fail when `request` returns `DENIED` with `!shouldShowRationale`. Why: the "do nothing" failure mode looks like the app is broken.

## <a name="a21"></a>21. `POST_NOTIFICATIONS` — notifications silently dropped on Android 13+

**Symptom.** `NotificationManager.notify(...)` returns without error; nothing appears. Works on Android 12, silent on Android 13+.

**Root cause.** Android 13 (API 33) introduced the `POST_NOTIFICATIONS` runtime permission. Apps targeting 33+ must request it; the system does not show notifications if denied.

**Fix.** Declare `<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>`, request at runtime before the first notification, handle denial gracefully (log, fallback to an in-app indicator).

**Prevention rule.** On every `targetSdk` bump, skim the "behaviour changes" page and diff the permission list. `POST_NOTIFICATIONS` is a required runtime permission for `targetSdk >= 33`. Why: missing runtime permissions manifest as "nothing happens", which is the worst kind of bug to triage.

## <a name="a22"></a>22. `SCHEDULE_EXACT_ALARM` revocable on Android 14

**Symptom.** Alarm-based reminders stop firing on Android 14. User reports "the 7am reminder just didn't come".

**Root cause.** Android 14 (API 34) lets users revoke `SCHEDULE_EXACT_ALARM` from an app that previously had it. `AlarmManager.canScheduleExactAlarms()` returns `false`. Calling `setExactAndAllowWhileIdle` throws `SecurityException`.

**Fix.** Check before scheduling: `if (!alarmManager.canScheduleExactAlarms()) { /* guide user to Settings or fall back to setWindow */ }`. For non-critical reminders, use `setWindow` or WorkManager instead — the exact-alarm API is intended for calendars and clocks.

**Prevention rule.** `setExact*` calls are guarded by `canScheduleExactAlarms()` and have a fallback to `setWindow`. User-visible text explains when exact-alarm is missing. Why: revocable permissions can flip at any time; assuming permanence produces silent failures.

## <a name="a23"></a>23. R8 / ProGuard strips a class used via reflection (JSON, DI, serialization)

**Symptom.** Debug build works. Release build crashes on a JSON parse with `NoSuchMethodException` or `ClassNotFoundException`, or a Hilt injection fails, or a `Parcelable` round-trip blows up.

**Root cause.** R8 (the default shrinker in AGP 4+) removes code it believes is unused. Classes accessed only via reflection — Gson / Moshi / kotlinx.serialization models, Hilt-generated components, `@Parcelize` generated methods — are "unused" from a static-analysis standpoint.

**Fix.** Keep rules in `proguard-rules.pro`:
```
-keep class com.example.dto.** { *; }
-keepattributes Signature, *Annotation*
-keep class kotlinx.serialization.** { *; }
-keep @kotlinx.serialization.Serializable class * { *; }
```
For Moshi / Gson, use the library-provided consumer rules (most ship them automatically now). For `@Parcelize`, no extra rules are needed in modern AGP. When in doubt, build with `-dontobfuscate` temporarily to see if the problem is renaming vs removal.

**Prevention rule.** Every release candidate runs the full integration-test suite on a R8'd build — not only the debug build. Models used via reflection are covered by a `-keep` rule *and* a unit test that decodes a fixture. Why: R8 problems only appear in release; a clean debug run is not evidence of correctness.

## <a name="a24"></a>24. R8 strips Compose `@Preview` providers — release builds crash

**Symptom.** A screen uses `@PreviewParameter(MyProvider::class)` for design-time previews. Release build crashes with `ClassNotFoundException` on that provider class even though the `@Preview`-annotated function isn't called at runtime.

**Root cause.** The preview-only provider class is referenced in annotations that R8 scans. Without a keep rule, it's stripped.

**Fix.** Keep preview providers only in `debug` source sets (Gradle `sourceSets`) or add `-keep class * implements androidx.compose.ui.tooling.preview.PreviewParameterProvider`. Better: put preview code under `src/debug/` so it's not in release at all.

**Prevention rule.** Preview-only scaffolding (providers, preview parameter classes, sample data) lives under `src/debug/` or a separate Gradle module applied only to debug. Why: keeping preview noise out of release shrinks APKs and eliminates a class of R8 surprises.

## <a name="a25"></a>25. Deep link intent filter swallowed by another activity

**Symptom.** `https://yourapp.com/foo` link launches the wrong activity, or opens the chooser dialog instead of going straight in.

**Root cause.** Two activities in the manifest claim the same `<intent-filter>`, or `android:autoVerify="true"` wasn't set and the `assetlinks.json` wasn't published, so the OS treats the intent as "ambiguous".

**Fix.** Exactly one activity owns each URL pattern. Set `android:autoVerify="true"` on the intent filter, publish `https://yourapp.com/.well-known/assetlinks.json` with your SHA-256 signing key fingerprint. Verify via `adb shell pm verify-app-links --re-verify com.example.app`.

**Prevention rule.** Deep link ownership is one-to-one — one URL pattern, one activity. The assetlinks.json is generated from the upload key (via Play Console) and kept in version control. CI checks the file resolves over HTTPS. Why: "the chooser shows" and "wrong activity opens" both mean the link routing is broken in a way that's invisible until users complain.

## <a name="a26"></a>26. `onNewIntent` not called — stale `getIntent()`

**Symptom.** User taps a notification. The app (already in foreground on a different screen) switches to the target activity, but the payload is from the *previous* notification.

**Root cause.** With `launchMode="singleTask"` or `singleTop`, reopening the activity with a new intent does not call `onCreate()` — it calls `onNewIntent(intent)`. If the activity only reads `getIntent()` in `onCreate()`, it sees the stale one.

**Fix.** Override `onNewIntent(intent)`, call `setIntent(intent)`, then handle the payload. Shared payload handling: extract into a `handle(intent: Intent)` method called from both `onCreate` and `onNewIntent`.

**Prevention rule.** Any activity with `singleTask` / `singleTop` launch mode overrides `onNewIntent`, calls `setIntent(intent)`, and funnels intent handling through one method used by both entry points. Why: launch modes that avoid recreation also skip `onCreate`; intent logic duplicated across them is a recipe for staleness.

## <a name="a27"></a>27. `Context` leak via a retained singleton

**Symptom.** LeakCanary report: `Activity instance is leaking`. App memory grows over time; rotation accelerates the leak.

**Root cause.** A singleton (object class, `@Singleton`-scoped Hilt binding, or `companion object` cache) holds a reference to `Activity` context — usually passed into it directly or captured inside a listener.

**Fix.** Singletons hold `Context.applicationContext`, never an Activity. If a feature needs Activity context, it's Activity-scoped (Hilt `@ActivityScoped` or `@ActivityRetainedScoped`), not singleton.

**Prevention rule.** The scope of a context reference matches the lifetime of the holder. `applicationContext` for app-lifetime; Activity context only from Activity-lifetime holders. LeakCanary is always enabled on debug builds. Why: Activity leaks are the most common Android memory bug and the pattern is almost always "singleton keeps Activity".

## <a name="a28"></a>28. `ANR` from long-running `BroadcastReceiver.onReceive`

**Symptom.** User sees "App isn't responding" dialog. Play Console reports ANRs clustered around broadcast handling.

**Root cause.** `BroadcastReceiver.onReceive` has a ~10-second budget on the main thread. Work beyond that — disk writes, network, SQLite — causes an ANR.

**Fix.** Use `goAsync()` to extend slightly; for real work, enqueue to `WorkManager` or `JobScheduler` and return immediately. `CoroutineWorker` inside `onReceive` via a scope is fine only if the scope is not the main thread and the receiver awaits completion via `goAsync()`.

**Prevention rule.** `BroadcastReceiver.onReceive` does at most "filter and enqueue". No disk, no network, no SQLite inline. Why: broadcasts fire on main thread with a short budget; the OS reports the ANR with a stack that doesn't point at the slow line.

## <a name="a29"></a>29. `StrictMode` disk / network on main thread in release only

**Symptom.** Debug build feels fine. Release build stutters during navigation.

**Root cause.** `StrictMode` was enabled only on debug. Development environments also tend to have faster disks. A sync disk read that takes 5ms in dev takes 120ms on a low-end phone.

**Fix.** Run `StrictMode` in debug with `.penaltyDeath()` so violations are immediate. Profile release builds on mid-range physical hardware (Pixel 4a, Galaxy A-series). Move any `Preferences` read, SharedPreferences, asset file read, or small DB read off the main thread — especially on app startup.

**Prevention rule.** `StrictMode` is on in debug with fatal penalties. Any `I/O` on the main thread has a ticket and a date for removal. Startup time is measured on a 2019-era mid-range device, not a flagship. Why: "works on my device" is the dominant Android perf failure; the developer's phone is always faster than the median user's.

## <a name="a30"></a>30. Edge-to-edge insets double-apply on Android 15

**Symptom.** After `targetSdk = 35`, toolbars are cut off by the status bar, or content gets double-padding at the bottom.

**Root cause.** Android 15 enforces edge-to-edge by default for apps targeting 35+. If the app was already handling insets manually (via `fitsSystemWindows` or `OnApplyWindowInsetsListener`), the new default layers on top.

**Fix.** Pick one strategy: (a) embrace edge-to-edge, remove manual `fitsSystemWindows=true` from layouts, consume insets explicitly in Compose via `WindowInsets.systemBars.asPaddingValues()` or XML via `ViewCompat.setOnApplyWindowInsetsListener`; (b) opt out with `enableEdgeToEdge(...)` disabled via theme attributes. Don't mix.

**Prevention rule.** Insets have one strategy per screen, explicit in code. `fitsSystemWindows`, `enableEdgeToEdge`, and manual listeners are never combined. Why: double-applied insets look like "the toolbar moved" and require visual QA per device size.

## <a name="a31"></a>31. `targetSdk` bump silently changes background-location behaviour

**Symptom.** Background location tracking that worked on a previous target SDK silently stops working after bumping `targetSdk`. User sees permission UI they didn't see before.

**Root cause.** Each OS version since Android 10 has tightened background-location rules: API 29 added `ACCESS_BACKGROUND_LOCATION`, API 30 added the two-step "enable in Settings" grant, API 31 separated precise vs coarse, API 34 made foreground-service-type `location` mandatory. Bumping `targetSdk` opts in to the newer, stricter rules.

**Fix.** On any `targetSdk` bump, re-audit location handling: (a) check `ACCESS_BACKGROUND_LOCATION` is requested only after `ACCESS_FINE_LOCATION` is granted and the user has used the feature in foreground; (b) confirm `foregroundServiceType="location"` is declared; (c) ensure users understand the two-step consent. Ship a user-visible migration note.

**Prevention rule.** `targetSdk` bumps are a first-class project: diff the behaviour-changes page, re-test permissions end to end on each OS version, write a changelog entry. Why: silent platform policy changes are the single biggest source of "app worked, now doesn't" complaints.

## <a name="a32"></a>32. Gradle: "Unresolved reference" after AGP / Compose BOM bump

**Symptom.** Build fails after a dependency-version bump with `Unresolved reference: ComposeView` or `Unresolved reference: collectAsStateWithLifecycle`. Nothing else changed.

**Root cause.** A BOM bump (Compose BOM, Kotlin, AGP) moved many packages at once. An API moved to a new artifact, a package was renamed, or a Kotlin-stdlib symbol was removed.

**Fix.** Isolate the bump: revert, commit the bump on its own branch, full clean build, `grep` for every removed symbol, update imports. Bump Kotlin and Compose Compiler together — the Compose Compiler version must match the Kotlin version per Google's compatibility matrix.

**Prevention rule.** BOM / AGP / Kotlin bumps are each their own commit with a clean build + full test run before any other change. Compose Compiler version follows the Kotlin version — lookup table is consulted on every bump. Why: bundling a BOM bump with unrelated work makes breakage almost impossible to attribute.
