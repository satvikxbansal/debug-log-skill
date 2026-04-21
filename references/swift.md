# Swift — language-level error catalog

Covers: Swift language features that trip up engineers independent of platform — `async`/`await` & structured concurrency, actors (`@MainActor`, custom actors), `Sendable` under strict concurrency, generics & variance, `Codable`, property wrappers, `@escaping` closures, optionals, result builders (`@resultBuilder`), SwiftUI Previews.

Each entry follows the same shape: **Symptom → Root cause → Fix → Prevention rule.**

Platform-specific Swift bugs (SwiftUI state ownership, UIKit memory cycles, AVAudioSession, navigation, keyboard) are in [`ios.md`](ios.md); macOS-specific bugs in [`macos.md`](macos.md).

## Table of contents

1. [`async` function called synchronously — "cannot be called in a function that does not support concurrency"](#s01)
2. [`await` on a non-async expression — "no 'async' operations occur"](#s02)
3. [`@MainActor` isolation inferred incorrectly on a closure](#s03)
4. [`Sendable` warnings after enabling complete concurrency](#s04)
5. [Actor re-entrancy — state assumed invariant across `await`](#s05)
6. [`Task { }` captures `self` strongly](#s06)
7. [`async let` without `await` — doesn't run concurrently](#s07)
8. [`TaskGroup` swallows child-task errors silently](#s08)
9. [`Codable` decoding silently drops optional keys with wrong name](#s09)
10. [`Codable` + `@propertyWrapper` — wrapper type leaks into JSON](#s10)
11. [`Date` decoded with wrong strategy — off by zone](#s11)
12. [`Decimal` vs `Double` — silent precision loss in financial code](#s12)
13. [Implicitly-unwrapped optional from Objective-C (`NSString!`) NPEs](#s13)
14. [Force-unwrap in guard-let's `else` branch](#s14)
15. [Value type holding a reference type — shared mutation surprise](#s15)
16. [Protocol with associated type — "can only be used as a generic constraint"](#s16)
17. [Generic constraint forgotten — unexpected "generic parameter could not be inferred"](#s17)
18. [`@escaping` closure captures `self` — retain cycle](#s18)
19. [`@resultBuilder` (SwiftUI `body`) — type-check times balloon](#s19)
20. [Preview crashes with "Cannot preview in this file"](#s20)

---

## <a name="s01"></a>1. `async` function called synchronously — "cannot be called in a function that does not support concurrency"

**Symptom.** Compile error: `'async' call in a function that does not support concurrency`.

**Root cause.** Swift concurrency is cooperative — `async` functions must be called from another `async` function, a `Task { }`, or an async-accepting API (SwiftUI `.task`, `.refreshable`).

**Fix.** Bridge with `Task { await asyncFn() }`. For main-actor contexts: `Task { @MainActor in await fn() }`. Don't try to `DispatchQueue.main.sync { await … }` — that deadlocks.

**Prevention rule.** Sync-to-async bridges use `Task { }`; async-to-sync bridges don't exist. If a synchronous API needs a value from async code, redesign the synchronous side as async. Why: the sync/async boundary is one-way cooperative; forcing it the wrong direction locks up the dispatch queue.

## <a name="s02"></a>2. `await` on a non-async expression — "no 'async' operations occur"

**Symptom.** Warning: `no 'async' operations occur within 'await' expression`. Or: a value doesn't update the way you'd expect after an `await`.

**Root cause.** The expression being awaited isn't actually async — you wrote `await foo()` on a synchronous function, or used `await` on an already-fetched property.

**Fix.** Remove the `await`. If the intent was to yield (let other tasks run), use `await Task.yield()`. If the value was meant to be async but isn't, audit the API — you may be calling a sync overload.

**Prevention rule.** `await` precedes a genuine suspension. Stray awaits are compiler warnings, not stylistic; fix them. Why: they hide bugs where the developer thought they were awaiting something they weren't.

## <a name="s03"></a>3. `@MainActor` isolation inferred incorrectly on a closure

**Symptom.** `Button { viewModel.load() }` — warning or error: `call to main actor-isolated instance method '…' in a synchronous nonisolated context`.

**Root cause.** The closure's isolation doesn't match the called method's. Swift's closure-isolation inference is context-dependent and conservative. Closures passed to `Button` are nonisolated unless the API says otherwise.

**Fix.** Make the closure call the method inside a `Task`: `Button { Task { await viewModel.load() } }`. Or mark the closure `@MainActor`: `Button { @MainActor in viewModel.load() }` (only valid in some APIs). Or make the method nonisolated if it genuinely doesn't need main-actor.

**Prevention rule.** UI callbacks that invoke main-actor methods wrap in `Task { … }` when the method is async, or inline-call when the method is marked `@MainActor` and the closure inherits isolation. When adding a method to a view model, think about its isolation before its signature. Why: actor-isolation inference is subtle; explicit hints beat fighting the compiler.

## <a name="s04"></a>4. `Sendable` warnings after enabling complete concurrency

**Symptom.** `Non-sendable type 'Foo' returned by implicitly asynchronous call` — dozens of warnings after switching the build setting to `Strict Concurrency Checking = Complete`.

**Root cause.** Passing values across actor boundaries requires `Sendable`. Classes aren't sendable by default; closures capturing non-sendable state aren't sendable.

**Fix.** Prefer value types (`struct`, `enum`) with sendable stored properties — they're sendable automatically. For reference types that genuinely need identity: use `actor`. For legacy classes you've verified are thread-safe: `final class Foo: @unchecked Sendable`. Each `@unchecked` is a promise — don't spray them.

**Prevention rule.** New types default to `struct`. `class` is reserved for identity semantics; when used, consider whether `actor` is a better fit. `@unchecked Sendable` requires a comment explaining the thread-safety argument. Why: sendable is load-bearing in Swift 6; promiscuous `@unchecked` kills the benefit.

## <a name="s05"></a>5. Actor re-entrancy — state assumed invariant across `await`

**Symptom.** An actor method reads `self.value`, awaits a network call, then writes `self.otherValue` based on the first read. In production, the logic gets wrong answers under concurrent load.

**Root cause.** Actors allow re-entrancy. While task A is suspended at an `await`, task B can enter and mutate state. The value read before `await` is no longer guaranteed to match after.

**Fix.** Re-read state after `await` if it was modified: don't trust stored results across suspensions. For atomicity needs, model the critical section differently — a private serial queue (inside the actor, no awaits), or a transaction-style method that doesn't await in the middle.

**Prevention rule.** Every `await` inside an actor method is a re-entry point; any state read before must be considered potentially stale after. Critical-section logic is either await-free or uses an explicit state-machine pattern. Why: actor re-entrancy is the most common Swift-6 bug, and it doesn't produce warnings — just wrong answers.

## <a name="s06"></a>6. `Task { }` captures `self` strongly

**Symptom.** Instruments shows a view controller / view model that outlives its screen, anchored on a `Task`. Memory grows with navigation.

**Root cause.** `Task { await self.work() }` captures `self` strongly and keeps it alive until the task finishes. Structured concurrency doesn't save you from unstructured `Task { }` escape hatches.

**Fix.** Capture weakly: `Task { [weak self] in await self?.work() }`. For SwiftUI, prefer `.task { … }` on a view — the framework ties lifetime to the view. For UIKit or long-running classes, store the `Task` and cancel in `deinit`.

**Prevention rule.** `Task { }` inside a class captures `[weak self]` by default, or the class has a stored `Task` that's cancelled on deinit. Why: the #1 Swift concurrency leak is unstructured `Task { }` holding an owner.

## <a name="s07"></a>7. `async let` without `await` — doesn't run concurrently

**Symptom.** `async let a = fetchA()` + `async let b = fetchB()` + `let result = try await a + (try await b)`. Runs serially instead of concurrently.

**Root cause.** `async let` starts a child task at the declaration. But if you also await one before declaring the next (e.g., `let a = try await fetchA(); async let b = …`), concurrency is lost.

**Fix.** Declare all the `async let` bindings up front, then await together at the end. For many tasks, use `TaskGroup` / `withThrowingTaskGroup`.

**Prevention rule.** Concurrent fetches use `async let` declared in a group at the top, with awaits at the bottom. Or explicit `TaskGroup`. Why: accidental serialisation kills the whole point of async-let.

## <a name="s08"></a>8. `TaskGroup` swallows child-task errors silently

**Symptom.** A `TaskGroup` is used to run N child tasks. One child throws. Parent appears to complete normally; the error is gone.

**Root cause.** `TaskGroup` (the non-throwing variant) returns `Void` on child error without propagating. The throwing variant `withThrowingTaskGroup` cancels all siblings on first throw.

**Fix.** Use `withThrowingTaskGroup` if any child can throw and the error matters. If you want "best effort" fan-out, use `withTaskGroup` and have each child return a `Result`, which the parent reduces.

**Prevention rule.** Task-group choice is explicit: throwing for "one error = whole op fails", non-throwing with `Result` for "collect errors and keep going". Why: using the non-throwing variant with a throwing child silently drops the error.

## <a name="s09"></a>9. `Codable` decoding silently drops optional keys with wrong name

**Symptom.** JSON contains `user_name`; struct has `var userName: String?`; field is always `nil`. No error.

**Root cause.** `Codable` matches keys literally. An `Optional` that fails to decode becomes `nil` — no error thrown.

**Fix.** Configure the decoder: `decoder.keyDecodingStrategy = .convertFromSnakeCase`. Or declare `CodingKeys`: `enum CodingKeys: String, CodingKey { case userName = "user_name" }`.

**Prevention rule.** Each decoder is configured once (snake-case, date strategy) and shared. DTOs have round-trip tests with fixtures. Why: silent-nil-on-optional is the single worst Codable failure mode — it ships.

## <a name="s10"></a>10. `Codable` + `@propertyWrapper` — wrapper type leaks into JSON

**Symptom.** A property wrapper around a value is used on a `Codable` struct. JSON output contains `{ "value": { "wrappedValue": "foo" } }` instead of `{ "value": "foo" }`.

**Root cause.** The property wrapper type doesn't customise its own `Codable` conformance, so the default synthesised version encodes the wrapper's stored properties.

**Fix.** Implement `Codable` on the wrapper, delegating to `wrappedValue`:
```swift
@propertyWrapper struct Clamped<T: Comparable & Codable>: Codable {
    var wrappedValue: T
    // … init, range, etc.
    init(from decoder: Decoder) throws {
        wrappedValue = try T(from: decoder)
    }
    func encode(to encoder: Encoder) throws {
        try wrappedValue.encode(to: encoder)
    }
}
```

**Prevention rule.** Property wrappers used on `Codable` types have explicit `init(from:)` / `encode(to:)` that delegate to `wrappedValue`. Why: the leaked-wrapper JSON schema mismatches backends silently.

## <a name="s11"></a>11. `Date` decoded with wrong strategy — off by zone

**Symptom.** Backend sends ISO8601 strings; client displays them N hours off, and the offset varies per user.

**Root cause.** `JSONDecoder().dateDecodingStrategy = .iso8601` expects zone information in the string. If the backend sends a naïve `2026-04-21T09:00:00` (no zone), `.iso8601` fails; some teams fall back to a custom formatter interpreted in device-local time, which varies.

**Fix.** Fix the contract: all timestamps are UTC with `Z` or an explicit offset. Decode with `.iso8601` or the fractional-seconds variant. Apply user's timezone only at display time.

**Prevention rule.** Date wire format is UTC with an explicit zone marker. Device local time is computed from that at display; never stored or transmitted. Why: "off by hours" bugs are impossible to reproduce without knowing the user's current zone.

## <a name="s12"></a>12. `Decimal` vs `Double` — silent precision loss in financial code

**Symptom.** Sum of prices is off by a cent. `0.1 + 0.2 != 0.3`.

**Root cause.** `Double` is IEEE 754 binary floating point; many decimal fractions (0.1, 0.2) are not exactly representable. For money, this is unacceptable.

**Fix.** Use `Decimal` for money (or `NSDecimalNumber` interop). Integer cents (`Int`) also works and is faster. Never `Double`.

**Prevention rule.** Money is `Decimal` (or integer minor units). A type alias `typealias Money = Decimal` makes it visible. No `Double` for money, percentages-of-money, or tax math. Why: floating-point in finance is a compliance issue; rounding mismatches with backend calculations surface as reconciliation bugs.

## <a name="s13"></a>13. Implicitly-unwrapped optional from Objective-C (`NSString!`) NPEs

**Symptom.** Objective-C API returns `NSString *` without nullability annotation. Swift treats as `String!`. When the API returns nil, Swift NPEs at the first use.

**Root cause.** Implicitly-unwrapped optionals skip the null-check. The NPE is at use site, not declaration site — hard to diagnose.

**Fix.** At the boundary, explicitly declare nullability: `guard let name = objcObj.getName() else { return }`. Or modify the Objective-C header to add `_Nullable` / `_Nonnull` annotations. For heavily-consumed C / ObjC APIs, add a Swift wrapper layer that normalises types.

**Prevention rule.** ObjC / C interop crosses into Swift through a thin wrapper layer where nullability is declared. IUOs from imported code are converted to proper optionals at the boundary. Why: IUOs are spring-loaded NPEs — they bite far from the API they came from.

## <a name="s14"></a>14. Force-unwrap in guard-let's `else` branch

**Symptom.** `guard let x = optional else { print("error: \(optional!)") }`. If `optional` was `nil`, the print crashes instead of logging.

**Root cause.** Inside the `else`, `optional` is not narrowed to non-nil (it's narrowed to the *guard failed* case — i.e., nil). The force-unwrap hits `nil`.

**Fix.** Don't reference the optional in the else — it's nil. Log a constant or a message: `print("error: value was nil")`.

**Prevention rule.** Inside a `guard let x = optional else { … }`, the else branch never refers to `optional` via force-unwrap. If the original optional is needed (rare), use a different binding name in the guard. Why: this mistake is subtle — the author meant "log the bad value" but the bad value is nil.

## <a name="s15"></a>15. Value type holding a reference type — shared mutation surprise

**Symptom.** `struct Foo { var items: UIView }` — copying `Foo` should be a value-type copy, but mutating the copy's `items` visibly affects the original. Or vice versa.

**Root cause.** Structs are values by default, but a reference-type property (class, `NSObject`, view) is shared by reference when the struct is copied. Mutating the reference's state affects all copies.

**Fix.** If the struct should be deeply immutable, don't embed mutable reference types. If shared reference is intended (e.g., caches, big objects), `class` is the right container, not `struct`. For an intermediate case, use copy-on-write wrappers or a `CustomReflection` that deep-copies.

**Prevention rule.** `struct` composition is evaluated for deep value semantics. Embedded reference types are documented as shared. If copy-on-write is needed, it's explicit and tested. Why: the "why did my copy change?" bug is one of Swift's classic surprises and silently breaks invariants.

## <a name="s16"></a>16. Protocol with associated type — "can only be used as a generic constraint"

**Symptom.** `protocol Fetcher { associatedtype T; func fetch() -> T }` — writing `let x: Fetcher` fails: `Protocol 'Fetcher' can only be used as a generic constraint because it has Self or associated type requirements`.

**Root cause.** Protocols with associated types (PATs) don't have a concrete type until the associated type is specified. You can't store them directly without "some" (opaque) or "any" (existential) qualifiers.

**Fix.** Swift 5.7+: `let x: any Fetcher` (existential, boxed) or `func process<F: Fetcher>(fetcher: F)` (generic). For returning: `func make() -> some Fetcher` (opaque). For properties in a struct: `let x: any Fetcher` or make the struct generic.

**Prevention rule.** PATs are used with `any`, `some`, or as generic constraints. The choice is informed by the cost: `any` is boxed and dynamically dispatched; `some` is static but type-identity-preserving; generic is static and flexible. Why: "can only be used as a generic constraint" is an old error; modern Swift has explicit tools.

## <a name="s17"></a>17. Generic constraint forgotten — unexpected "generic parameter could not be inferred"

**Symptom.** `func process<T>(_ x: T)` — caller `process(42)` works, but `process([1, 2, 3].first)` fails with "generic parameter 'T' could not be inferred".

**Root cause.** The caller's expression is ambiguous — multiple overloads match, the compiler can't pick. Usually triggered by `Optional` auto-lifting.

**Fix.** Add constraints to narrow: `func process<T: Numeric>(_ x: T)`. Or specify at the call site: `process(Int(42))`. For optional shenanigans: unwrap before calling.

**Prevention rule.** Generic functions carry the narrowest constraint that expresses intent. Too-generic signatures produce inference failures that look like the caller's fault. Why: good constraints are documentation; they also drive inference.

## <a name="s18"></a>18. `@escaping` closure captures `self` — retain cycle

**Symptom.** Instruments leak graph shows a class holding a closure that holds the class. Classic cycle.

**Root cause.** Closures stored on a class property implicitly capture `self` strongly. The class holds the closure; the closure holds the class.

**Fix.** `self.onDone = { [weak self] in self?.doThing() }`. For unstructured tasks within methods, same treatment: `Task { [weak self] in await self?.load() }`.

**Prevention rule.** Any stored `@escaping` closure property on a class captures `[weak self]` by default. `[unowned self]` is allowed when you can prove the lifetime, with a comment. Strong `self` requires justification. Why: Swift doesn't warn on retain cycles through closures; they surface only under memory profiling.

## <a name="s19"></a>19. `@resultBuilder` (SwiftUI `body`) — type-check times balloon

**Symptom.** A SwiftUI `body` with a deeply-nested view hierarchy takes 30+ seconds to type-check, or fails with "the compiler is unable to type-check this expression in reasonable time".

**Root cause.** SwiftUI's `ViewBuilder` produces a nested generic type (`TupleView<A, B, C, …>`) that the compiler has to solve. Long bodies with inline arithmetic and conditionals make the search exponential.

**Fix.** Extract subviews into properties (`var header: some View { … }`) or small structs. Pull arithmetic out of the closure into `let`s above. Use `@ViewBuilder` on your own helper methods so they return `some View`. Avoid ternary-heavy inline conditions; use `if` branches instead.

**Prevention rule.** SwiftUI bodies are decomposed aggressively. Any expression over a handful of lines moves to a computed property or helper. Type-check timeouts trigger refactor, not bigger timeouts. Why: the compiler can solve a 30-line body; it can't solve a 300-line one, and adding `@inline(__always)` doesn't help.

## <a name="s20"></a>20. Preview crashes with "Cannot preview in this file"

**Symptom.** `#Preview { ContentView() }` — canvas shows "Cannot preview in this file" with no useful stack.

**Root cause.** Previews run in a process that doesn't initialise the app's main actor the same way as a real launch. Missing environment objects, missing mocks, `@AppStorage` with unset defaults, or a crash in a dependency's `init` on the preview thread all produce the opaque message.

**Fix.** Inject everything the preview needs: `.environmentObject(AppState.preview).environment(\.modelContext, .preview)`. Gate side-effectful init with `if ProcessInfo.processInfo.environment["XCODE_RUNNING_FOR_PREVIEWS"] != "1"`. Check the `Diagnostics` button on the preview canvas for the underlying error — the short message is misleading.

**Prevention rule.** Every view that has an `@EnvironmentObject` / `@Environment` dependency has a `#Preview` block that provides it, with a `.preview` static factory on each model. Preview failures are first-class bugs. Why: broken previews destroy the tight-loop development experience; teams stop trusting the canvas and catch regressions later.
