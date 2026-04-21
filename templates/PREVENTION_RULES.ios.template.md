# PREVENTION_RULES — iOS

> Promoted rules for iOS projects (Swift / SwiftUI / UIKit). Derived from `DEBUG_LOG.md`.
>
> Rules appear here when they have fired in **three or more** DL entries. Keep this file short — if it grows past two screens, move rules into SwiftLint configuration, build-phase scripts, or Xcode test plans.

## How to read this

Each rule is one imperative sentence with a **Why** clause, a **Where** clause, and **DL refs**.

## Rules

<!-- Replace example rules below as your project accumulates its own. -->

### R-001 — Annotate observable objects with `@MainActor`, never bounce to main manually

- **Why:** `DispatchQueue.main.async { self.value = ... }` sprinkled through a view model invites races against SwiftUI's diffing and produces invisible UI drift when an update arrives mid-body.
- **Where:** any class conforming to `ObservableObject`, or any `@Observable` class consumed from a `View`.
- **DL refs:** DL-003, DL-019, DL-030

### R-002 — Never capture strong `self` inside a `Task { }` that outlives the view

- **Why:** SwiftUI views are value types; the `Task { }` captures the *view* (which is fine) but if it touches `self.viewModel`, that ObservableObject leaks past the view's lifetime and keeps fetching / observing.
- **Where:** all `Task { }` and `Task.detached { }` blocks created inside `.onAppear`, `.task`, `.onReceive`.
- **DL refs:** DL-008, DL-022, DL-045

### R-003 — Use a stable `id` on every `ForEach` over a mutable collection

- **Why:** `ForEach(items)` without an `id:` keypath (when `Item` is not `Identifiable`) falls back to position-based identity, producing visual glitches when items are inserted or removed from the middle.
- **Where:** all `ForEach` usages in `List`, `LazyVGrid`, `LazyVStack`.
- **DL refs:** DL-011, DL-024, DL-039

### R-004 — Any dependency read inside `body` must be a `@State`, `@StateObject`, `@Binding`, or `@Environment`

- **Why:** reading a plain property during render means SwiftUI has no way to observe it; the view won't recompute when the value changes.
- **Where:** every `View.body` in the project.
- **DL refs:** DL-002, DL-016, DL-051

---

## How to add a rule

1. Notice the same rule in DL-XXX, DL-YYY, DL-ZZZ.
2. Add an R-NNN entry with Why / Where / DL refs.
3. Where possible, add a SwiftLint custom rule or a build-phase `grep` that enforces it.
4. Update `CLAUDE.md` / `AGENTS.md` so LLM sessions pick up the rule.

## Retiring a rule

Strike through and add `Retired: YYYY-MM-DD — <reason>`. Don't delete.
