# PREVENTION_RULES — macOS

> Promoted rules for macOS projects (Swift / AppKit / SwiftUI on Mac). Derived from `DEBUG_LOG.md`.
>
> Rules appear here when they have fired in **three or more** DL entries.

## How to read this

Each rule is one imperative sentence with a **Why** clause, a **Where** clause, and **DL refs**.

## Rules

<!-- Replace example rules below as your project accumulates its own. -->

### R-001 — Always check current TCC status at launch; never cache the last known value

- **Why:** the user can revoke Screen Recording, Accessibility, Automation, or Input Monitoring permissions at any time from System Settings. Features that assume yesterday's approval silently do nothing or crash.
- **Where:** app delegate launch, and every entry point for a feature that requires a TCC-gated API.
- **DL refs:** DL-002, DL-017, DL-034

### R-002 — Run accessibility queries on a background queue; UI thread will hang on unresponsive targets

- **Why:** `AXUIElementCopyAttributeValue` on an unresponsive app can block the caller for minutes. On the main queue, the whole app becomes unresponsive — including beachball on every click.
- **Where:** every call site of the AX APIs (`AXUIElement*`).
- **DL refs:** DL-006, DL-019, DL-038

### R-003 — Hardened Runtime + Notarisation must be tested on a *clean* VM before shipping

- **Why:** the local dev machine has dev certificates + debugger exceptions that mask "not notarised" / "Gatekeeper blocked" failures. The first user download reveals them.
- **Where:** release pipeline, before any DMG/PKG is published.
- **DL refs:** DL-010, DL-024, DL-041

### R-004 — `NSWindow` level + `.canBecomeKey` must be explicitly set for floating panels

- **Why:** default `NSWindow.Level.normal` panels lose focus unpredictably behind other app windows; debug-only test builds often hide the problem because the debugger puts our app at the front.
- **Where:** all subclasses of `NSWindow` / `NSPanel` used for HUD / floating UI.
- **DL refs:** DL-004, DL-016, DL-029

---

## How to add a rule

1. Spot the rule in DL-XXX, DL-YYY, DL-ZZZ.
2. Add an R-NNN entry with Why / Where / DL refs.
3. Where possible, encode as a SwiftLint rule or a release-pipeline check.
4. Update `CLAUDE.md` / `AGENTS.md`.

## Retiring a rule

Strike through and add `Retired: YYYY-MM-DD — <reason>`.
