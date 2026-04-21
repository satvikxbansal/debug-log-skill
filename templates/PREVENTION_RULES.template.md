# PREVENTION_RULES

> A summary index of the prevention rules we have learned the hard way.
>
> This file is **derived** from `DEBUG_LOG.md` — when a rule appears in three or more DL entries, it is promoted here and (usually) into automated tooling as well.
>
> Maintainers: keep this file short. If it grows past two screens, promote rules into ambient tooling (linters, code review checklists, CI guards) and remove them from here.

## How to read this

Each rule is one imperative sentence with:

- A **Why** clause — the class of bug it prevents.
- A **Where** clause — the files or modules it applies to.
- A **DL refs** list — the specific DEBUG_LOG entries that generated the rule.

## Rules

<!-- Promote rules here when they have fired three or more times in DEBUG_LOG.md. Example entries below; replace as you accumulate your own. -->

### R-001 — Never call platform UI APIs from a worker thread

- **Why:** SwiftUI `@Published` properties, Compose `MutableState`, and React state setters are all documented as main-thread-only. Violations produce silent data corruption or crashes.
- **Where:** anywhere you observe a background result and write it back to UI state.
- **DL refs:** DL-015, DL-023, DL-031

### R-002 — Bump platform BOMs in isolated commits

- **Why:** version bundles (Compose BOM, React, Next) move many packages at once. Bundling a BOM bump with other changes makes the breakage hard to attribute.
- **Where:** `build.gradle.kts`, `package.json`, `Package.swift`.
- **DL refs:** DL-001, DL-017, DL-044

### R-003 — Read before render; side effects belong in effects

- **Why:** SSR/CSR hydration and SwiftUI view-body purity both require that render be deterministic. Reading `Date.now()`, `Math.random()`, or environment objects during render introduces invisible state.
- **Where:** all React component bodies; SwiftUI `body` property.
- **DL refs:** DL-014, DL-022, DL-060

---

## How to add a rule

1. Notice the same prevention rule appearing in DL-XXX, DL-YYY, DL-ZZZ.
2. Write a new R-NNN entry above, with a Why / Where / DL refs block.
3. If possible, add a linter or CI check that enforces the rule automatically, and link it in the Where clause.
4. Update `CLAUDE.md` or `.cursor/rules/` or `AGENTS.md` (whichever your team uses) so the rule becomes ambient LLM guidance.

## Retiring a rule

Rules retire when one of the following is true:

- The underlying problem has been made impossible by tooling (e.g., the linter catches it before the human does).
- The platform has changed and the bug no longer exists.
- The rule turned out to be wrong on reflection.

Mark the rule as retired in place (strike through, add a "Retired: YYYY-MM-DD — reason" line) rather than deleting it. The history matters; future readers will want to know why the rule existed.
