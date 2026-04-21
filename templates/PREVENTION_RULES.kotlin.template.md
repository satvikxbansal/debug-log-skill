# PREVENTION_RULES — Kotlin

> Promoted rules at the Kotlin language / coroutines level, beyond any specific UI framework. Derived from `DEBUG_LOG.md`.
>
> Rules appear here when they have fired in **three or more** DL entries.

## How to read this

Each rule is one imperative sentence with a **Why** clause, a **Where** clause, and **DL refs**.

## Rules

<!-- Replace example rules below as your project accumulates its own. -->

### R-001 — Every `suspend` function must propagate cancellation

- **Why:** wrapping a suspend body in `runCatching { ... }` or a broad `try/catch (Throwable)` swallows `CancellationException`, breaking structured concurrency. Cancellations become silent leaks.
- **Where:** any `suspend fun`.
- **DL refs:** DL-004, DL-018, DL-035

### R-002 — Use `SupervisorJob` for scopes where child failures should not cancel siblings

- **Why:** a plain `Job` cancels all children when one fails. A screen with three parallel fetchers becomes "any failure kills everything" — a UX worse than the individual error.
- **Where:** feature-level `CoroutineScope` constructors.
- **DL refs:** DL-007, DL-021, DL-039

### R-003 — Expose `Flow` from repositories, never `suspend fun` that returns a one-shot value, for observable state

- **Why:** repeatedly calling a `suspend` fetcher to "refresh" means consumers miss mid-stream updates and often double-fetch. A cold `Flow` backed by a SharedFlow / StateFlow is the right shape.
- **Where:** all data layer repositories.
- **DL refs:** DL-011, DL-026, DL-044

### R-004 — Seal your domain errors; never throw from the domain layer for expected outcomes

- **Why:** `throw NotFoundException` reads naturally at the throw site but forces every caller up the stack to know about it. A sealed `Result<Error, T>` puts the error in the type signature where it can't be forgotten.
- **Where:** domain / use-case layer.
- **DL refs:** DL-006, DL-020, DL-042

---

## How to add a rule

1. Spot the rule in DL-XXX, DL-YYY, DL-ZZZ.
2. Add an R-NNN entry.
3. Encode as a Detekt rule if possible.
4. Update `CLAUDE.md` / `AGENTS.md`.

## Retiring a rule

Strike through and add `Retired: YYYY-MM-DD — <reason>`.
