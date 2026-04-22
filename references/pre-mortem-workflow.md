# Pre-mortem workflow

> When to use this file: before starting **new feature work**, not bug fixes. For bug fixes, the relevant `references/<track>.md` and `DEBUG_LOG.md` are the primary reading.
>
> A pre-mortem is an inversion of the post-mortem. Instead of asking "why did this fail?" after the fact, you ask it before the fact — out loud, in writing, before you've written any code that anchors your thinking.

## Why pre-mortem?

Most bugs that ship are not code mistakes. They are *assumption* mistakes — the developer believed X about the platform, the data, the user, or the system, and X turned out to be wrong. The bug is an echo of the false assumption.

Post-mortems fix the echo. Pre-mortems surface the assumption while it's still cheap to change.

Three reliable data points from shipping teams:

- An hour spent pre-morteming a feature prevents, on average, 3–5 hours of later debugging per feature.
- The bugs caught by pre-mortems are systematically worse (data corruption, race conditions, UX regressions) than bugs caught by code review.
- LLM-produced code has the same failure mode, amplified: the model will confidently produce code that embeds false assumptions, because it cannot tell the false ones from the true ones without evidence. Pre-morteming makes the evidence explicit.

## The four-phase workflow

### Phase 1 — Frame the feature (5 minutes)

Write one paragraph covering:

1. The user-visible behaviour after this ships. Not the implementation — the *behaviour*. "Users can save a draft" is behaviour; "add a POST /drafts endpoint" is implementation.
2. Who triggers it, how often, under what conditions (mobile / web / offline / authed / anon).
3. What success looks like — specifically, a sentence that could be turned into an acceptance test.
4. What is explicitly out of scope for this iteration.

If you cannot write this paragraph cleanly, stop. The spec is not ready. Any code you write now will be rework.

### Phase 2 — Identify the track(s), load the catalog, and run the active pre-flight

For each track the feature touches (web, ios, android, macos, kotlin, swift, cross-cutting), open `references/<track>.md` and skim the section titles. Read in full any entry whose name touches the feature area. For example:

- Starting Compose work? Read the "Recomposition loop" and "State hoisting" and "Lifecycle in Compose" entries.
- Touching network? Read the cross-cutting "HTTP retries", "Idempotency", and "Timeout stacking" entries.
- Adding a form? Read the "Uncontrolled / controlled" (web) or "TextField focus" (iOS) entries.

Then run the **active pre-flight** on the project's own `DEBUG_LOG.md` — do not read the log end-to-end. Grep for the files, tags, or Root Cause Categories this feature is likely to touch:

```bash
# By file path (strongest signal)
grep -niE "MessageRow|ReactionBar|Thread\.tsx" DEBUG_LOG.md

# By tag (see references/tag-taxonomy.md)
grep -niE "#Optimistic|#Idempotency|#RateLimit|#Compose|#LazyColumn" DEBUG_LOG.md

# By Root Cause Category
grep -niE "Race Condition|Hydration Mismatch|LLM Hallucination" DEBUG_LOG.md
```

Record the DL numbers that come back plus any entries they cross-reference (`Supersedes DL-XXX` / `See DL-XXX`). Those are the project-specific prevention rules you must honour on top of the generic catalog rules.

You are looking for the entries — from both the reference catalogs and the pre-flight grep hits — whose *prevention rule* would apply if this feature existed in the form you're imagining. Flag them.

### Phase 3 — Work the preempt checklist

Open `references/preempt-checklist.md`. For each track in scope, answer the 10–12 questions. Do not skip questions; write the answer even if it's "not applicable here — feature is read-only". The discipline is forcing yourself to look.

Each question in the checklist maps to a category of bug that has burned real projects. You're not answering for the checklist's sake; you're answering because "I don't know" on any of these is a flashing-red-light predictor of a later bug.

Pay special attention to:

- Any question you answer "I'm not sure" or "I'll figure it out later." That is the bug, usually.
- Any question where your answer implies a platform contract you haven't personally verified. (E.g., "The callback fires on the main thread." Does it? How do you know?)

### Phase 4 — Write the plan

A one-page plan that names:

1. **Goal** — the one-paragraph behaviour from Phase 1.
2. **Files touched** — ideally no more than 5 files changed + 2 files added. If more, is the feature really one piece of work?
3. **Interfaces preserved** — the public contracts you will not change. Naming them proves you understand the blast radius.
4. **Applicable prevention rules** — the DL numbers your Phase-2 pre-flight grep surfaced, plus any rules from the reference catalogs. Each quoted, with a one-line note on how it applies here. If zero pre-flight hits came back and the feature is non-trivial, say so explicitly — that's a signal to widen the grep before proceeding.
5. **Unknowns** — any Phase-3 answer that was "not sure" or needs verification. For each, a note on how you will resolve it *before* writing the code that depends on it.
6. **Verification** — how you will know the feature works. Ideally: an automated test, a manual check, and a log line that fires on the happy path.

Post this plan to the chat / PR description / design doc before you write code. The plan is cheap; the code commits you to an approach.

## Common objections

> "This is overhead. I'd rather just start coding."

The assumption behind this objection is that the typing is the hard part. For most features, the typing is the easy part — the thinking is the hard part. Pre-mortem forces the thinking up front, when it is still shapeable. Debugging after the fact is ten times more expensive because now the thinking happens under constraint (the code exists, other work depends on it, the user is waiting).

> "I don't know enough yet to pre-mortem."

Then the answer to Phase 3 is a lot of "I don't know" — which is exactly the signal you need. The pre-mortem isn't asking you to have answers; it's asking you to have *questions*. Questions with names attached are 10x cheaper to investigate than surprises that surface later.

> "The feature is small. A pre-mortem is overkill."

For a genuinely small feature (< 50 lines, < 1 hour), you can compress the workflow. For anything larger, the question is not "is a pre-mortem worth the time" but "how much scar tissue have I accumulated on this codebase, and how much of it is about this area?" The former is time you spend; the latter is time the next person pays for.

## Working with an LLM

When an LLM is executing a feature under this workflow:

- Feed the LLM the Phase-1 paragraph first, before asking for code.
- Ask the LLM to identify tracks and list the reference entries it plans to read. Confirm the list before proceeding.
- Ask the LLM to produce the Phase-3 answers in writing. Don't accept "yes I checked" — you want the written answers so a reviewer (human or LLM) can spot the flawed assumption.
- Ask for the Phase-4 plan before any file is edited. The discipline is identical to the one you'd use with a junior engineer; LLMs benefit from the same structure.

The LLM will occasionally push back with "I can just start coding" framing. Resist. The plan costs thirty seconds of tokens and saves thirty minutes of debugging per feature, and it compounds across the project.

## Worked example

**Feature:** "Users can react with an emoji to a message in a thread."

Phase 1 — framing:

> From the message row (mobile + web), the user taps a reaction affordance and picks an emoji. The emoji appears next to the message, grouped with any other users who reacted the same way. The feature works offline (queues, retries), works for anon users with rate limits, and is observable in analytics.

Phase 2 — tracks: web, ios, android, cross-cutting. Active pre-flight grep on DEBUG_LOG.md:

```bash
grep -niE "MessageRow|Thread\.tsx|ReactionBar" DEBUG_LOG.md
# → DL-003 (LazyColumn recomposition on unkeyed rows)
grep -niE "#Optimistic|#Idempotency|#RateLimit" DEBUG_LOG.md
# → DL-004 (optimistic-update rollback on 429), DL-006 (double-tap dedupe)
```

Three DL numbers flagged before a line of code is written.

Phase 3 — a selection of the questions that matter here:

- *cross-cutting / Idempotency*: what happens if the user taps twice, or the app retries a failed request? Answer: we use a client-generated reaction ID; the server is idempotent on that ID.
- *web / Optimistic updates*: the UI updates before the server confirms. Do we reconcile on failure? Answer: we roll back on any non-2xx, with a toast.
- *android / Compose recomposition*: does adding a reaction to a long list cause all rows to recompose? Answer: use `key = message.id` in `LazyColumn`, memoise the reaction bar composable.
- *ios / List identity*: same question, SwiftUI. Answer: use `.id(message.id)` and `Equatable` on the row model.
- *cross-cutting / Rate limiting*: what is the rate limit for anon users? Answer: 10 reactions per minute per IP, enforced server-side, with a `Retry-After` response.

Phase 4 — plan: one page, five files changed, two added, two prevention rules from DL cited.

Time spent on pre-mortem: 35 minutes. Bugs prevented, based on team's pattern-recognition: at least three we would have hit in review or in production, specifically around double-tapping, Compose recomposition, and rate-limit UX.

## When NOT to pre-mortem

- The feature is a true one-line change, like renaming a variable or fixing a typo.
- The feature is exploratory and you will throw away the code. (But write down the questions you answered "I don't know" — they're the learning.)
- You're in incident response. Different mode: triage, then post-mortem, then the prevention rule for next time.

Everything else pre-mortems. Every single time.
