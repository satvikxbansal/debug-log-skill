# PREVENTION_RULES — Android

> Promoted rules for Android projects (Kotlin / Jetpack Compose / coroutines). Derived from `DEBUG_LOG.md`.
>
> Rules appear here when they have fired in **three or more** DL entries. Keep this file short — if it grows past two screens, promote rules into Lint rules, Detekt configuration, or CI checks.

## How to read this

Each rule is one imperative sentence with a **Why** clause, a **Where** clause, and **DL refs**.

## Rules

<!-- Replace example rules below as your project accumulates its own. -->

### R-001 — Every foreground service must declare its `foregroundServiceType` in the manifest *and* in `startForeground()`

- **Why:** Android 14+ throws `MissingForegroundServiceTypeException` if the runtime type is not present in both places. The crash is immediate on start and is silent on older OS versions.
- **Where:** every `Service` class that calls `startForeground`. Manifest `<service>` entries.
- **DL refs:** DL-006, DL-021, DL-038

### R-002 — Never launch coroutines in `GlobalScope`

- **Why:** `GlobalScope` has no cancellation, no structured concurrency, and no parent. Work continues past the screen, the user, and sometimes the process — leaking observers, holding databases open, racing lifecycle.
- **Where:** all `.kt` files under `app/` and feature modules.
- **DL refs:** DL-009, DL-025, DL-047

### R-003 — Compose side effects go in `LaunchedEffect`, `DisposableEffect`, or `rememberCoroutineScope()`

- **Why:** calling `viewModel.load()` directly in a composable body fires on every recomposition, producing duplicate network calls and missed state updates.
- **Where:** all `@Composable` functions.
- **DL refs:** DL-013, DL-027, DL-042

### R-004 — Every `Flow.collect` must be bound to a scope that cancels with the view

- **Why:** collecting a Flow in `onCreate` or at activity scope outlives configuration changes and leaks the observer; duplicate collectors race to update the same state.
- **Where:** `Fragment`, `Activity`, `@Composable` — anywhere `Flow.collect` or `collectAsStateWithLifecycle` is used.
- **DL refs:** DL-005, DL-020, DL-033

---

## How to add a rule

1. Spot the rule firing in DL-XXX, DL-YYY, DL-ZZZ.
2. Write an R-NNN entry with Why / Where / DL refs.
3. Where feasible, encode the rule in Detekt, Android Lint, or a Gradle check.
4. Update `CLAUDE.md` / `AGENTS.md` for LLM awareness.

## Retiring a rule

Strike through and add `Retired: YYYY-MM-DD — <reason>`.
