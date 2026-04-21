# PREVENTION_RULES — web

> Promoted rules for web projects (React / Next.js / TypeScript / Node). Derived from `DEBUG_LOG.md`.
>
> Rules appear here when they have fired in **three or more** DL entries. Keep the file short — if it outgrows two screens, move rules into linters / ESLint rules / CI guards and remove them from here.

## How to read this

Each rule is one imperative sentence with:

- A **Why** clause — the class of bug it prevents.
- A **Where** clause — the files or modules it applies to.
- A **DL refs** list — the specific DEBUG_LOG entries that generated the rule.

## Rules

<!-- Replace example rules below as your project accumulates its own. -->

### R-001 — No globals during render in any component that can render on the server

- **Why:** reading `window`, `document`, `localStorage`, `Date.now()`, `Math.random()`, or `crypto.randomUUID()` during render corrupts SSR hydration and produces invisible data drift.
- **Where:** React component bodies in any file under a route that uses `getServerSideProps`, `getStaticProps`, or the `app/` directory. Anything marked `"use client"` that may also prerender.
- **DL refs:** DL-001, DL-014, DL-029

### R-002 — Never throw across a Server / Client component boundary without serialisation

- **Why:** RSC serialises props through a wire format that cannot carry Error instances, Date objects with extra properties, or functions. Throws on the server become opaque "Something went wrong" on the client.
- **Where:** any function exported from a `"use server"` module; any prop passed from an RSC to a client component.
- **DL refs:** DL-012, DL-033, DL-041

### R-003 — Effects that depend on identity must use a stable dependency

- **Why:** `useEffect([obj])` where `obj` is created inline each render fires every render, often silently firing mutations.
- **Where:** all `useEffect` / `useMemo` / `useCallback` calls whose deps array contains object or function references.
- **DL refs:** DL-007, DL-022, DL-036

### R-004 — Never read env vars at module scope in code shared between server and client

- **Why:** `process.env.FOO` read at module scope is captured at build time on the client; changing it at runtime on the server does nothing for the client bundle. Produces silent divergence between environments.
- **Where:** anything imported by both server and client files.
- **DL refs:** DL-004, DL-018, DL-047

---

## How to add a rule

1. Notice the same prevention rule appearing in DL-XXX, DL-YYY, DL-ZZZ (three minimum).
2. Write a new R-NNN entry above, with a Why / Where / DL refs block.
3. If possible, add an ESLint rule, a TypeScript strictness flag, or a Playwright check that enforces it.
4. Update `CLAUDE.md` / `.cursor/rules/` / `AGENTS.md` so the rule is ambient guidance for LLMs working in this repo.

## Retiring a rule

Strike through the rule and add a `Retired: YYYY-MM-DD — <reason>` line. Don't delete — the history matters.
