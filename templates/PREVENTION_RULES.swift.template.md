# PREVENTION_RULES — Swift

> Promoted rules at the Swift language / concurrency level, independent of iOS or macOS UI specifics. Derived from `DEBUG_LOG.md`.
>
> Rules appear here when they have fired in **three or more** DL entries.

## How to read this

Each rule is one imperative sentence with a **Why** clause, a **Where** clause, and **DL refs**.

## Rules

<!-- Replace example rules below as your project accumulates its own. -->

### R-001 — Turn on Strict Concurrency Checking early, not at the Swift 6 cliff

- **Why:** "Minimal" concurrency checking hides hundreds of Sendable violations that blow up the first time you flip to "Complete". Fixing them in small batches beats a one-shot 300-diagnostic afternoon.
- **Where:** every SwiftPM target and Xcode target in the project.
- **DL refs:** DL-002, DL-015, DL-031

### R-002 — Every `actor` method that returns data must assume re-entrancy between `await` points

- **Why:** actors serialise single calls but *not* across awaits. State you read before `await` may be mutated by another entry by the time the continuation resumes. Treat an actor function body as a sequence of atomic stanzas.
- **Where:** all `actor` declarations.
- **DL refs:** DL-005, DL-019, DL-034

### R-003 — `@unchecked Sendable` is a hazard comment; require a written justification

- **Why:** `@unchecked Sendable` silences the compiler but moves the safety burden to you. Without a comment explaining the locking discipline, the next reader will touch the type and introduce a race.
- **Where:** every use of `@unchecked Sendable` in the codebase.
- **DL refs:** DL-008, DL-022, DL-037

### R-004 — Never throw a non-`Error` value across an async boundary

- **Why:** wrapping arbitrary strings or enums as "errors" without conforming to `Error` produces brittle casts at the boundary. Use a typed, sealed `enum Error: Swift.Error` per module.
- **Where:** any async function that throws.
- **DL refs:** DL-011, DL-026, DL-043

---

## How to add a rule

1. Spot the rule in DL-XXX, DL-YYY, DL-ZZZ.
2. Add an R-NNN entry.
3. Encode as a SwiftLint custom rule if possible.
4. Update `CLAUDE.md` / `AGENTS.md`.

## Retiring a rule

Strike through and add `Retired: YYYY-MM-DD — <reason>`.
