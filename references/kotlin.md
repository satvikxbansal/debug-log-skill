# Kotlin — language-level error catalog

Covers: Kotlin language features that trip up engineers independent of platform — coroutines & structured concurrency, `Flow` / `StateFlow` / `SharedFlow`, kotlinx.serialization, null safety nuance, data-class semantics, Java interop, generics / variance, inline functions, delegated properties, sealed hierarchies.

Each entry follows the same shape: **Symptom → Root cause → Fix → Prevention rule.**

Platform-specific Kotlin bugs (Compose recomposition, Room, Hilt, Android permissions) are in [`android.md`](android.md).

## Table of contents

1. [Coroutine launched without a scope — work leaks on cancellation](#k01)
2. [`GlobalScope.launch` — the canonical scope mistake](#k02)
3. [Child coroutine failure cancels unrelated siblings](#k03)
4. [`Flow.collect` in a loop — never returns](#k04)
5. [`StateFlow` emits nothing because equals-check rejects new value](#k05)
6. [`SharedFlow(replay = 1)` used as state — subtle semantic drift](#k06)
7. [`channelFlow` vs `flow` — wrong builder for the job](#k07)
8. [`Dispatchers.Main` on JVM — "Module with the Main dispatcher had failed to initialize"](#k08)
9. [`runBlocking` inside a suspend function](#k09)
10. [`withContext(Dispatchers.IO)` wrapping CPU-bound work](#k10)
11. [kotlinx.serialization: `@Serializable` class missing default on a new field — old clients crash](#k11)
12. [kotlinx.serialization: polymorphism fails with "Class … is not registered"](#k12)
13. [Data class `copy()` breaks encapsulation of a private constructor](#k13)
14. [`equals()` / `hashCode()` on data class with mutable property](#k14)
15. [`val` property on a `var` backing field — unexpected nullability](#k15)
16. [Platform type (`T!`) from Java slips past null safety](#k16)
17. [`lateinit` read before assignment — `UninitializedPropertyAccessException`](#k17)
18. [`by lazy` with unsynchronised lock in multi-thread context](#k18)
19. [Generic `List<out T>` and the "cannot add to it" surprise](#k19)
20. [Inline function with `noinline` / `crossinline` forgotten](#k20)
21. [Sealed class exhaustive `when` stops being exhaustive after refactor](#k21)
22. [`Result<T>` swallowed exceptions when returned from a suspend function](#k22)

---

## <a name="k01"></a>1. Coroutine launched without a scope — work leaks on cancellation

**Symptom.** Feature completes; the view model is released; the fetch finishes anyway and updates a dismissed UI, writes to a disposed Room dao, or fires a toast on the wrong screen.

**Root cause.** `GlobalScope.launch { … }` or `CoroutineScope(Dispatchers.IO).launch { … }` created an unmanaged scope with no owner. Nothing cancels it when the owning component is gone.

**Fix.** Launch into a scope tied to a lifecycle: `viewModelScope.launch { … }`, `lifecycleScope.launch { … }`, or a scope you build with a `SupervisorJob` and cancel in `onCleared()`. `GlobalScope` is discouraged in production code.

**Prevention rule.** Every coroutine launch has a named scope whose lifetime matches the work. `GlobalScope` is banned; a CI lint check (`detekt` rule `GlobalCoroutineUsage`) catches usage. Why: orphan coroutines violate structured concurrency and produce "why is that toast showing" bugs.

## <a name="k02"></a>2. `GlobalScope.launch` — the canonical scope mistake

**Symptom.** `GlobalScope.launch { apiCall() }` — apparently fine. But a test that runs to completion reports "coroutine leaked"; or production memory creeps over hours.

**Root cause.** `GlobalScope` has the lifetime of the application process. Work launched into it is not cancelled by anything short of process death. Also, it uses `Dispatchers.Default` unless overridden — which might be the wrong pool.

**Fix.** Replace with a properly-owned scope. If the work is genuinely process-lifetime (analytics flush, log rotation), create an `ApplicationScope` injected via Hilt with a `SupervisorJob` and document why.

**Prevention rule.** `GlobalScope` appears in exactly one place per app (the documented `ApplicationScope`) or zero places. Why: its name suggests "just use this", but it's the coroutine equivalent of a static reference — essentially unmanaged.

## <a name="k03"></a>3. Child coroutine failure cancels unrelated siblings

**Symptom.** Three coroutines launched from the same parent. One fails. The other two stop too, even though their work is independent.

**Root cause.** A plain `Job` propagates cancellation up to the parent, which then cancels all children. `SupervisorJob` is the variant that doesn't propagate child failure.

**Fix.** When independent tasks should survive each other's failures, use `supervisorScope { … }` or a scope created with `SupervisorJob()`. Inside, each `launch` handles its own exception.

**Prevention rule.** Parent-child coroutine relationships default to `Job`: "we rise and fall together". Use `SupervisorJob` / `supervisorScope` only where independent failure is the intent, and annotate why. Why: silent cross-cancellation is confusing; `SupervisorJob` reverses the default.

## <a name="k04"></a>4. `Flow.collect` in a loop — never returns

**Symptom.** Code calls `flow.collect { … }` expecting it to run once per emission and return. It never returns; the calling function hangs.

**Root cause.** `collect` is a *terminal operator* that suspends for the lifetime of the flow. Cold flows run until the upstream completes; hot flows (`StateFlow`, `SharedFlow`) never complete.

**Fix.** For "just the next value", use `flow.first()` or `flow.firstOrNull()`. For "all values collected so far", use `flow.toList()` (cold flow only). For fire-and-forget collection, launch a new coroutine: `viewModelScope.launch { flow.collect { … } }`.

**Prevention rule.** Terminal operators are named explicitly by intent: `first`, `toList`, `fold`. Only launch a `collect` in a scope when you want lifecycle-bound ongoing collection. Why: the suspend-forever semantics of hot flow collection surprises devs coming from `List` / `Sequence`.

## <a name="k05"></a>5. `StateFlow` emits nothing because equals-check rejects new value

**Symptom.** `state.value = newValue` — collector doesn't fire. `state.value` *does* change.

**Root cause.** `StateFlow` de-duplicates emissions by `equals`. If `newValue == oldValue`, subscribers don't see the update. Often hits data classes where a nested field changed but `equals` treats them as equal.

**Fix.** Ensure new state has a different `equals` — often by using an immutable data class where the changed field is part of equality. For one-shot events that should always fire, use `SharedFlow` (replay = 0) or `Channel`, not `StateFlow`.

**Prevention rule.** `StateFlow` is state (with equality semantics); `SharedFlow(replay = 0)` / `Channel` is events. The semantic choice is conscious. Why: modelling events as state produces skipped emissions; modelling state as events produces replay bugs on rotation.

## <a name="k06"></a>6. `SharedFlow(replay = 1)` used as state — subtle semantic drift

**Symptom.** A `SharedFlow<UiState>` with `replay = 1` behaves almost but not exactly like `StateFlow` — and edge cases show it (no `value` property, no initial value required, different conflation semantics).

**Root cause.** `SharedFlow` and `StateFlow` are cousins. `replay = 1` gives the illusion of state without the contract. In particular, `SharedFlow` doesn't conflate emissions; fast producers overfill the buffer and either drop or suspend.

**Fix.** If it's state (single current value, initial required, conflated), use `StateFlow`. If it's events with a small replay for late subscribers (toast, snackbar), use `SharedFlow`. Don't reach for `SharedFlow(replay = 1)` as a lightweight `StateFlow`.

**Prevention rule.** Pick `StateFlow` vs `SharedFlow` by semantics, not by perceived simplicity. Document the choice in the declaration comment. Why: the two look interchangeable and diverge under load — a bug that only appears in production.

## <a name="k07"></a>7. `channelFlow` vs `flow` — wrong builder for the job

**Symptom.** A flow that collects from a callback API (e.g., a sensor) drops emissions under load, or doesn't emit at all.

**Root cause.** `flow { emit(x) }` has sequential semantics and can't be called from a different coroutine context. Callback-based bridges need `callbackFlow` (for API-style callbacks with explicit close) or `channelFlow` (for concurrent senders).

**Fix.** `callbackFlow { val listener = … ; awaitClose { unregister(listener) } }` — this correctly wires registration, emission from any thread, and cleanup. `channelFlow` for concurrent producers. Plain `flow` only for sequential computations.

**Prevention rule.** Builder choice is driven by the producer model: sequential → `flow`, callback API → `callbackFlow`, concurrent producers → `channelFlow`. Why: using `flow` for a callback yields "IllegalStateException: Flow invariant is violated" or silent drops — both mask as "my sensor doesn't work".

## <a name="k08"></a>8. `Dispatchers.Main` on JVM — "Module with the Main dispatcher had failed to initialize"

**Symptom.** Unit test that uses `Dispatchers.Main` throws `IllegalStateException: Module with the Main dispatcher had failed to initialize`.

**Root cause.** `Dispatchers.Main` needs a platform provider (`kotlinx-coroutines-android` for Android, `kotlinx-coroutines-javafx` or `kotlinx-coroutines-swing` for JVM desktop). In tests, no provider is available.

**Fix.** Use `kotlinx-coroutines-test` and set a test dispatcher via `Dispatchers.setMain(UnconfinedTestDispatcher())` (or `StandardTestDispatcher`) in a `@Before` / `@BeforeEach`, and `Dispatchers.resetMain()` in teardown. `runTest { … }` is the idiomatic test harness.

**Prevention rule.** Every test module that touches coroutines depends on `kotlinx-coroutines-test` and has a test-dispatcher rule / extension. Why: the error message is obscure; having the infra in place from day one avoids the archaeological hunt.

## <a name="k09"></a>9. `runBlocking` inside a suspend function

**Symptom.** A suspend function wraps a `runBlocking { … }` block. On UI thread, it deadlocks; in tests, it sometimes passes and sometimes hangs.

**Root cause.** `runBlocking` blocks the current thread until the coroutine finishes. Inside a suspend function that's already on a coroutine dispatcher, it can either deadlock (if the only thread in the dispatcher is this one) or waste throughput. Always wrong inside suspend.

**Fix.** Just use the suspend call directly: `val x = fetch()`, not `val x = runBlocking { fetch() }`. `runBlocking` is intended only for `main()` / JUnit tests that need to bridge from a blocking world.

**Prevention rule.** `runBlocking` appears only in `main()` entry points and tests — never in production suspend functions or Android components. A detekt rule forbids it in `src/main/`. Why: `runBlocking` misuse is the most common concurrency footgun in Kotlin code that compiles fine.

## <a name="k10"></a>10. `withContext(Dispatchers.IO)` wrapping CPU-bound work

**Symptom.** CPU-bound work (parsing, hashing, image decoding) runs `withContext(Dispatchers.IO)` and degrades under load — throughput caps at 64 operations even on a 16-core machine.

**Root cause.** `Dispatchers.IO` has a hard-coded 64-thread pool (by default). That's appropriate for blocking I/O (64 concurrent waiting sockets) but wrong for CPU work, which should use `Dispatchers.Default` (pool size = `max(2, availableProcessors)`).

**Fix.** CPU work goes on `Dispatchers.Default`. I/O work (blocking syscalls, disk, network) goes on `Dispatchers.IO`. When unsure: is the work blocking a thread without doing arithmetic? → IO. Is it crunching bytes? → Default.

**Prevention rule.** Dispatcher choice is semantic, not cargo-culted. `IO` for blocking, `Default` for CPU. Custom dispatchers for special pools. Why: the 64-thread cap is invisible in single-request benchmarks and brutal under concurrent load.

## <a name="k11"></a>11. kotlinx.serialization: `@Serializable` class missing default on a new field — old clients crash

**Symptom.** New field `email: String` added to a `@Serializable` class. Old clients (who don't yet send the field) crash on deserialization with `MissingFieldException: Field 'email' is required`.

**Root cause.** kotlinx.serialization requires every field either be provided by the payload *or* have a default value. A non-nullable, no-default field blows up on missing data.

**Fix.** Give the new field a default: `val email: String = ""`. Or make it nullable: `val email: String? = null`. For payloads that should strictly enforce presence, that's fine — but schema changes that break old clients should be a conscious decision.

**Prevention rule.** New fields in serialised types default to safe values (empty string, `null`, sensible zero) unless the field is genuinely required and the corresponding client is redeployed in lockstep. Why: missing-field crashes are runtime-only, happen only on the old-client side, and are invisible in local tests.

## <a name="k12"></a>12. kotlinx.serialization: polymorphism fails with "Class … is not registered"

**Symptom.** Deserialising a sealed-class JSON: `SerializationException: Class 'OtherVariant' is not registered for polymorphic serialization in the scope of 'Event'`.

**Root cause.** Runtime polymorphism requires either (a) the sealed-class hierarchy to be compile-time known and the plugin enables it automatically, or (b) a `SerializersModule` registering each subclass. Subclasses declared in separate modules sometimes aren't picked up.

**Fix.** For sealed classes in the same module, ensure the plugin version matches Kotlin's. For cross-module, register explicitly:
```kotlin
val module = SerializersModule {
    polymorphic(Event::class) {
        subclass(VariantA::class)
        subclass(VariantB::class)
    }
}
val json = Json { serializersModule = module; classDiscriminator = "type" }
```

**Prevention rule.** Polymorphic types live in a single module or are registered in an explicit `SerializersModule`. The `classDiscriminator` is documented. Why: the "not registered" error is intermittent across build configurations and surfaces only at runtime.

## <a name="k13"></a>13. Data class `copy()` breaks encapsulation of a private constructor

**Symptom.** A data class with a private constructor (meant to enforce invariants via a factory) can still be constructed externally via `.copy(...)` with arbitrary arguments.

**Root cause.** `copy()` is generated as a public function and doesn't respect constructor visibility. Since Kotlin 1.9 there's a warning; in earlier versions it was silent.

**Fix.** Either don't use a data class (regular `class` with `equals`/`hashCode` as needed), or make the class internal with no cross-module copy surface, or upgrade to 2.0+ where generated `copy` inherits the constructor visibility.

**Prevention rule.** Data classes expose the full shape of their fields via `copy`. If invariants need enforcement, the type isn't a data class — it's a regular class with a validating factory. Why: `copy()` has public-by-default semantics that silently undermine factory patterns.

## <a name="k14"></a>14. `equals()` / `hashCode()` on data class with mutable property

**Symptom.** A data class with a `var` property is used as a HashMap key. Mutating the property after insertion makes the entry unreachable (`map.containsKey(key)` returns false even though the key is there).

**Root cause.** `hashCode()` is computed from all properties. Mutating one changes the hash. HashMaps locate entries by hash bucket; a changed hash means the map looks in the wrong bucket.

**Fix.** Use `val`-only data classes as map keys. If mutation is required, use a non-data class with `equals`/`hashCode` based on a stable id.

**Prevention rule.** Data class fields are `val` by default. Any `var` on a data class is a design smell — reach for a regular class or a state-holder pattern. Why: the "missing key" bug is one of the most frustrating to trace.

## <a name="k15"></a>15. `val` property on a `var` backing field — unexpected nullability

**Symptom.** `val name: String? get() = _name` — reader sees a value; mutator then sets `_name = null`; next reader sees null even though "it was just there". Non-local reasoning fails.

**Root cause.** A `val` property with a custom getter is re-evaluated on every read. Readers who cache the value into a local and smart-cast to non-null still get the actual mutation on the next access — but only across code paths.

**Fix.** For values read multiple times in a single scope, take a snapshot: `val n = name ?: return`. For properties that should be stable after first read, use `by lazy` or `val`-with-init. Don't hide a `var` behind a `val` getter without thinking about observation.

**Prevention rule.** Public `val` means "same value every read" by convention. Computed `val`s that depend on mutable state are documented as such. Why: smart-cast-and-observe bugs are invisible in small functions and catastrophic across longer logic.

## <a name="k16"></a>16. Platform type (`T!`) from Java slips past null safety

**Symptom.** Kotlin code calls a Java method returning `String`. Kotlin treats it as `String!` (platform type). Passing the result to a Kotlin function expecting `String` works — then NPEs at runtime when the Java side returns null.

**Root cause.** Platform types are the compromise between Kotlin's strict nullability and Java's absent annotations. Kotlin doesn't force the developer to pick `String` vs `String?`; when the actual value is null, the NPE happens at the use site.

**Fix.** At the Java boundary, explicitly declare nullability: `val name: String? = javaObject.getName()`. If Java returns a collection, explicitly declare: `val items: List<Thing> = javaObject.getItems()` — and accept runtime NPE there, or handle via `?: emptyList()`. Annotate Java code with `@Nullable` / `@NonNull` / JSR-305 so Kotlin sees types correctly.

**Prevention rule.** Kotlin variables holding Java-returned values have explicit nullability declarations. Java APIs consumed heavily are annotated at source. Why: platform types punt the null check to runtime; making it explicit makes the contract reviewable.

## <a name="k17"></a>17. `lateinit` read before assignment — `UninitializedPropertyAccessException`

**Symptom.** `lateinit var config: Config` is used before being assigned; `UninitializedPropertyAccessException: lateinit property config has not been initialized`.

**Root cause.** `lateinit` skips null-safety. It works fine when lifecycle guarantees initialise-before-use (e.g., `@Inject` fields in Android). It breaks when a new code path reads the property earlier — a new entry point, a unit test, or a reorder of `onCreate`.

**Fix.** Default to `nullable + null` or `by lazy { … }`. Reach for `lateinit` only when (a) the framework guarantees init before first read (DI, Android lifecycle), and (b) you're willing to accept a crash on misuse. For testing, initialise explicitly in `@Before`.

**Prevention rule.** `lateinit` is a commitment about lifecycle. Every use includes a comment stating which lifecycle hook initialises it. Unit tests that exercise the property assign it. Why: the exception is obvious; the preventive habit is assigning initialisation to a known hook.

## <a name="k18"></a>18. `by lazy` with unsynchronised lock in multi-thread context

**Symptom.** `by lazy { expensiveInit() }` — `expensiveInit` runs multiple times under concurrent first-access on different threads.

**Root cause.** `by lazy` defaults to `LazyThreadSafetyMode.SYNCHRONIZED`, which is the safe default. But developers sometimes specify `PUBLICATION` or `NONE` without thinking; `PUBLICATION` allows racing initialisers, `NONE` is not thread-safe at all.

**Fix.** Leave the default unless you've profiled a lock-contention hot spot *and* can prove the initialiser is idempotent. If `NONE` is right, document the single-thread invariant.

**Prevention rule.** `by lazy` uses the default `SYNCHRONIZED` mode unless a named performance issue justifies otherwise. The alternative mode is annotated with why. Why: `SYNCHRONIZED` costs a cheap volatile read after first init; the race bugs from `PUBLICATION` cost weeks.

## <a name="k19"></a>19. Generic `List<out T>` and the "cannot add to it" surprise

**Symptom.** A method takes `List<Animal>` and tries `list.add(dog)`. Compile error: `Out-projected type 'List<Animal>' prohibits the use of 'public abstract fun add'`.

**Root cause.** `List` is covariant (`out`), meaning it's a producer of `T`. Mutating methods like `add` need `MutableList<T>` (invariant) or the receiver must be `MutableList<Animal>` specifically.

**Fix.** Accept `MutableList<Animal>` if you intend to mutate. Or return a new list: `list + dog`. Don't try to write through an immutable view.

**Prevention rule.** Parameter types are declared at the narrowest surface that supports the operation: `List<T>` for read-only, `MutableList<T>` for mutation, `Collection<T>` for size-and-iterate. Why: variance declarations encode read-vs-write intent; fighting them means the signature is wrong.

## <a name="k20"></a>20. Inline function with `noinline` / `crossinline` forgotten

**Symptom.** `inline fun run(block: () -> Unit)` — caller does `run { launch { } }`; compile error: `'launch' can't be called in this context by implicit receiver`. Or non-local return escapes unexpectedly.

**Root cause.** Lambdas passed to inline functions are inlined into the caller — which means `return` in them returns from the outer function (non-local). It also means they can't cross a lambda boundary (like `launch { }`) unless declared `crossinline`. Storing them in a variable requires `noinline`.

**Fix.** `crossinline` when the lambda will be invoked from another context (coroutine, thread, callback). `noinline` when the lambda is stored. Drop `inline` if the function's body doesn't benefit from inlining.

**Prevention rule.** `inline` is used when it gives a concrete benefit (reified generics, tight loops with lambda params). When the lambda crosses a boundary, the parameter is annotated `crossinline`. When it's stored, `noinline`. Why: "inline everything" was a pre-2.0 reflex and produces errors that look syntactic but are semantic.

## <a name="k21"></a>21. Sealed class exhaustive `when` stops being exhaustive after refactor

**Symptom.** A `when (event) { is A -> … ; is B -> … }` was exhaustive. Someone adds `class C : Event`. Code compiles fine; the unhandled case produces wrong behaviour at runtime.

**Root cause.** The `when` was used as a statement (not an expression) before Kotlin 1.7. Statement-form `when` is not required to be exhaustive, and the new case is silently ignored. The same code as an expression would fail to compile.

**Fix.** Use `when` as an expression: assign its result, or call `.also { }` on the `when`, or add a redundant `else -> error("unhandled $event")` explicitly. Since Kotlin 1.7 you can opt in to exhaustive-by-default with `-Xnon-local-break-continue` and related flags.

**Prevention rule.** `when` over a sealed hierarchy is always an expression or ends with `.also { }` so the compiler checks exhaustiveness. New subclasses become compile errors, not runtime surprises. Why: exhaustiveness is Kotlin's primary advantage over dispatch-by-string enums.

## <a name="k22"></a>22. `Result<T>` swallowed exceptions when returned from a suspend function

**Symptom.** A suspend function returns `Result<T>`. Inside, an exception is thrown. Outside, `Result.isFailure` is true — but cancellation exceptions were also captured, which breaks structured concurrency.

**Root cause.** `runCatching` catches `CancellationException` by default. In a coroutine, that's wrong — cancellation must propagate.

**Fix.** Rethrow cancellation: `runCatching { … }.onFailure { if (it is CancellationException) throw it }`. Or write a `coroutineRunCatching` extension that rethrows `CancellationException` automatically. kotlinx.coroutines 1.7+ has a built-in helper for this via `.getOrElse { }` idioms.

**Prevention rule.** `runCatching` in coroutine contexts rethrows `CancellationException`. Canonical pattern is in a shared extension. Why: silent cancellation-swallowing makes structured concurrency leak — tasks that should terminate continue on.
