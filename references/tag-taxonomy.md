# Tag taxonomy + Root Cause Categories

> This file defines the **controlled vocabulary** used by `DEBUG_LOG.md` entries.
>
> Tags are how `DEBUG_LOG.md` becomes searchable. The canonical list lives here — extend this file in the same commit that introduces a new tag, and grep will keep working across the project's history.

## Why controlled vocabulary

Free-text scanning falls over past ~20 entries. Tags give you semantic grouping that is cheap to grep:

```bash
grep -niE "#Compose|#StateFlow" DEBUG_LOG.md
```

A one-off tag that appears once in DL-017 and never again helps nobody. If you must introduce a new tag, add it here first with a one-line definition. Prefer an existing tag over inventing a new one.

---

## Track tags (required — pick at least one)

Every entry needs exactly one or two of these. They anchor the entry to a stack.

| Tag | Applies to |
|---|---|
| `#web` | React, Next.js, Vite, Node, browser runtime, CSS/layout, TypeScript on the web side |
| `#ios` | iOS-specific Swift / SwiftUI / UIKit work |
| `#android` | Android-specific Kotlin / Compose / services / lifecycle |
| `#macos` | macOS-specific AppKit / SwiftUI / menu-bar / hardened runtime |
| `#kotlin` | Kotlin language / coroutines / Flow / KMP / server Kotlin — not Android-specific |
| `#swift` | Swift language / async-await / Sendable / SwiftPM — not iOS/macOS-specific |
| `#cross-cutting` | Bugs that span stacks (HTTP, timezones, encoding, floats) |

## Semantic tags (required — pick at least one)

These classify the *subject matter* of the bug. Use as many as genuinely apply; two or three is typical.

### UI & rendering

`#UI` · `#Layout` · `#Rendering` · `#Animation` · `#A11y` (accessibility) · `#Focus` · `#KeyboardInput` · `#Gestures` · `#Theme` · `#DarkMode` · `#DynamicType` · `#RTL`

### Framework-specific

`#Compose` · `#SwiftUI` · `#UIKit` · `#AppKit` · `#React` · `#NextJS` · `#RSC` (React Server Components) · `#Hydration` · `#SSR` · `#ViewModel` · `#LiveData` · `#StateFlow` · `#SharedFlow` · `#Observable`

### Concurrency & lifecycle

`#Coroutines` · `#Threading` · `#MainActor` · `#Sendable` · `#AsyncAwait` · `#Combine` · `#RxJava` · `#Lifecycle` · `#ScopeLeak` · `#Cancellation` · `#Reentrancy`

### Data & storage

`#Room` · `#CoreData` · `#Realm` · `#Firestore` · `#SQLite` · `#Cache` · `#Serialization` · `#JSON` · `#Codable` · `#Migration` · `#DataRace`

### Network & I/O

`#Network` · `#HTTP` · `#URLSession` · `#Fetch` · `#Retry` · `#Idempotency` · `#CORS` · `#CSP` · `#WebSocket` · `#Offline` · `#Auth` · `#OAuth` · `#Token`

### Navigation

`#Navigation` · `#DeepLink` · `#Routing` · `#BackStack`

### Platform & permissions

`#Permissions` · `#TCC` · `#Entitlements` · `#Sandbox` · `#ForegroundService` · `#Notifications` · `#Background` · `#Overlay` · `#FlagSecure` · `#Screenshot` · `#ScreenRecording` · `#Accessibility` · `#InputMonitoring`

### Build, tooling & packaging

`#Build` · `#Gradle` · `#Xcode` · `#SwiftPM` · `#CocoaPods` · `#Vite` · `#Webpack` · `#Bundler` · `#Lint` · `#TypeCheck` · `#CI` · `#Release` · `#Notarisation` · `#Signing` · `#ProGuard` · `#R8`

### Testing

`#Test` · `#FlakyTest` · `#UnitTest` · `#UITest` · `#SnapshotTest` · `#E2E` · `#Playwright` · `#XCTest` · `#Espresso`

### Perf & profiling

`#Perf` · `#Memory` · `#Leak` · `#Startup` · `#JankFrame` · `#Battery`

### Security

`#Security` · `#Secrets` · `#CVE` · `#PII` · `#CSP`

### Observability

`#Logging` · `#Telemetry` · `#Crashlytics` · `#Analytics`

---

## Root Cause Categories (required — pick exactly one)

This is a **closed** vocabulary. Every entry picks one of these for its `Root Cause Category` field. The free-text `Root Cause Context` field carries the nuance.

Counting categories across the log is the fastest diagnostic you have: if 40% of your entries are `Race Condition`, you have a concurrency story to fix; if 30% are `LLM Hallucination or Assumption`, your agent setup needs stronger grounding.

| Category | What it means | Example |
|---|---|---|
| `API Change` | An API's behaviour changed between versions — contract drift, not a deprecation. | Compose 1.7 changed the default `LazyColumn` key-stability behaviour. |
| `API Deprecation` | Code called an API that has been formally deprecated or removed. | Android 14 deprecated `startForeground()` without `foregroundServiceType`. |
| `Race Condition` | Two or more executions observed each other in an order the code did not account for. | Two collectors on the same Flow raced to update a field. |
| `Scope Leak` | Work outlived the entity that started it (coroutine, Task, subscription, observer). | `GlobalScope.launch` kept polling after the screen closed. |
| `Main Thread Block` | The UI thread was blocked or a main-thread-only API was called off-main. | AX API call on the main queue caused beachball. |
| `Hydration Mismatch` | Server-rendered output and client-rendered output diverged. | `Date.now()` in a component body caused React hydration error. |
| `Null or Unchecked Access` | Code assumed a value was present or a cast would succeed; it wasn't. | `user?.profile!!` crashed when profile was null for guest users. |
| `Type Coercion` | Implicit or incorrect type conversion produced wrong data. | `"2" + 2 = "22"` in JS; Swift `Int(someString) ?? 0` masking a real parse failure. |
| `Off-By-One` | Index / range / count arithmetic was off by one. | Paging queried `page * pageSize` instead of `(page-1) * pageSize`. |
| `Syntax Error` | The code did not parse / compile for a trivial syntactic reason. | Missing closing brace; mis-typed keyword. |
| `Config or Build` | Failure was in build / dependency / env config, not in product code. | Gradle version bump silently broke R8; missing env var in CI. |
| `Test Infrastructure` | Test itself was wrong / flaky / depended on outside state. | Test relied on system timezone; passed in CI only. |
| `LLM Hallucination or Assumption` | An agent (including you) generated code based on a confident-but-false belief about an API, file, or structure. | Agent called `Array.findLast()` without checking Node version; used a non-existent Compose modifier. |
| `Other` | Truly doesn't fit. Must also describe the category in one noun phrase in `Root Cause Context` so future contributors can promote it. | — |

### Choosing between categories

When a bug fits more than one (e.g., an API deprecation that also caused a crash), pick the **root** category — the one that answers "if I had known X, the whole chain wouldn't have started." API Change / API Deprecation / LLM Hallucination usually win ties because they are the upstream mistake.

### Why `LLM Hallucination or Assumption` is a first-class category

Agent-generated code has a distinct failure mode: the model confidently emits code that references APIs, files, or invariants that don't exist in *this* codebase. This is not a syntax error (the code compiles for the model's fictional world) and not a race condition (there's no concurrency). It's a grounding failure. Naming it explicitly is how you learn to recognise it in the prevention rules: "Before using a less-common API, grep the codebase for prior usage; if none, read the library docs and cite a version."

---

## Extending the taxonomy

1. Prefer an existing tag. Most "new" tags are existing ones with slightly different phrasing.
2. If you genuinely need a new tag, add it here **in the same commit** as the DL entry that uses it, under the most appropriate section.
3. New Root Cause Categories are a bigger change — they should go through a PR discussion, because adding one changes the semantics of every historical count.

## How to grep with the taxonomy

```bash
# Everything involving a specific UI framework
grep -niE "#Compose|#SwiftUI|#React" DEBUG_LOG.md

# Everything that was ever attributed to a race condition
grep -niE "Race Condition" DEBUG_LOG.md

# Everything in a specific file
grep -niE "ProfileScreen\.kt" DEBUG_LOG.md

# Everything an agent got wrong
grep -niE "LLM Hallucination" DEBUG_LOG.md

# A specific library / dependency
grep -niE "#Room|startForeground|useEffect" DEBUG_LOG.md

# High-iteration entries (the ones you should learn most from)
grep -niE "Iterations.*\| [5-9]|\| [0-9]{2,}" DEBUG_LOG.md
```
