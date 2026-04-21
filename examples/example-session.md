# Example session

> A narrated walkthrough of an LLM-driven debugging session that uses the `debug-log-skill`. The fictional project is a hybrid iOS + Android chat app with a Next.js admin dashboard.

## Setup

The repo has adopted the skill:

- `DEBUG_LOG.md` at the root, with six entries (see [`example-DEBUG_LOG.md`](example-DEBUG_LOG.md)).
- `PREVENTION_RULES.md` with two rules promoted.
- `CLAUDE.md` / `.cursor/rules/debug-log.md` / `AGENTS.md` pointing the LLM at the skill.

The LLM is Claude, running in an IDE with file tools.

---

## Turn 1 — user request

> User: "Add a 'react with emoji' feature to the chat. Users tap a message, pick an emoji, and the reaction shows up for everyone in the conversation. Needs to work on iOS, Android, and the dashboard. Make sure it's real-time."

## Turn 2 — LLM applies the skill

Before writing any code, the LLM:

1. **Reads `DEBUG_LOG.md`** to look for prevention rules and entries that touch emoji, real-time, or chat features. It finds DL-001 (hydration) and DL-004 (idempotency on side-effectful endpoints).
2. **Reads `PREVENTION_RULES.md`** for promoted rules.
3. **Opens `references/preempt-checklist.md`** and copies the cross-cutting, web, iOS, android checklists.
4. **Looks at `CLAUDE.md`** for project-level guardrails (e.g., "All mobile state lives in a shared Kotlin Multiplatform module", hypothetically).

## Turn 3 — LLM writes the plan

The LLM produces this as a response, *before* writing any code:

> **Plan: react-with-emoji feature**
>
> **DL-derived prevention rules to apply:**
> - DL-001: the dashboard displays reactions with timestamps; reading `Date.now()` in a React component body would re-trigger the hydration bug. Timestamps format inside a client-only component.
> - DL-004: the `POST /api/v1/messages/:id/reactions` endpoint creates a side effect (reaction row + websocket broadcast). It must accept an `Idempotency-Key` header; the mobile clients generate one per tap.
>
> **Pre-mortem — cross-cutting:**
> - Emoji length: a single emoji with ZWJ sequences (👨‍👩‍👧) is multiple code points but one grapheme. Our validation must count graphemes, not `String.length`. (See [`cross-cutting.md#x03`](../references/cross-cutting.md#x03).)
> - Real-time via websocket: two users react at the same instant — do we have last-write-wins? Design: reactions are additive (user + emoji + message = unique tuple); deduped at insert. No LWW conflict possible.
> - Timezone: the "created at" on a reaction is stored UTC; rendered in user's zone at display.
>
> **Pre-mortem — iOS:**
> - `List` / `ForEach` over messages — reactions attached to each message. Reactions need a stable `Identifiable` (the tuple, or an id from the backend). Don't mint `UUID()` on decode. (DL-003's rule.)
> - Reaction picker is a sheet — `.sheet(item:)` not `isPresented:` + state (avoids the DL-007-style race — flagged as "not yet in log but covered by [`ios.md#i07`](../references/ios.md#i07)").
> - `@MainActor` on the `ChatViewModel`; websocket events from background thread go through `await MainActor.run` or `receive(on:)`. (ios rule i11.)
>
> **Pre-mortem — Android:**
> - Compose reaction picker inside a bottom sheet — `rememberSaveable` for the picker's state so rotation doesn't close it. (android rule a03.)
> - Websocket runs inside a foreground service (chat sync) — we already declared `foregroundServiceType="dataSync"` in DL-002, check the manifest. Done.
> - Reactions list keyed by `reactionId` (stable from backend), `LazyColumn` handles recomposition.
>
> **Pre-mortem — web (dashboard):**
> - Reactions list in a React Server Component? No — it's client-side because of real-time updates via websocket. Mark `'use client'`. No `useState` / `useEffect` in RSC context.
> - Hydration: the reactions list initial state is fetched server-side, serialised, and the client takes over. Ensure decoded shape is identical between SSR and CSR.
>
> **Files I'll touch:**
> - `shared-kotlin/src/.../Reaction.kt` (new)
> - `shared-kotlin/src/.../ChatRepository.kt` (add `react()` method)
> - `ios/Chat/ReactionPicker.swift` (new)
> - `ios/Chat/MessageRow.swift` (wire up long-press + reaction display)
> - `android/chat/ReactionPickerBottomSheet.kt` (new)
> - `android/chat/MessageItem.kt` (wire up)
> - `web/app/messages/[id]/reactions.tsx` (new, client component)
> - `backend/handlers/reactions.go` (new, with idempotency)
> - `DEBUG_LOG.md` — reserved DL-007 if I find a bug during implementation.
>
> Shall I proceed?

## Turn 4 — user confirms

> User: "Yes, go."

## Turn 5 — LLM writes code

The LLM implements the feature, following the plan. Along the way:

- Writes the iOS reaction picker using `.sheet(item: $selectedMessage)` (from `i07`).
- Makes `Reaction` `Identifiable` with the backend-provided reaction id.
- On Android, uses `rememberSaveable` for the picker open-state.
- On the dashboard, puts the reactions list in a client component with `'use client'`. Timestamp formatting is in a nested `<TimeAgo>` with `useEffect` (applying the DL-001 rule).
- On the backend, adds the idempotency-key middleware and a `(message_id, user_id, emoji)` unique index on `reactions` to dedupe at the DB level too.

## Turn 6 — LLM hits a bug

While testing on Android, the LLM sees:

> `IllegalStateException: LazyColumn recomposition loop` when the reactions list updates via websocket.

This is a bug. Per the skill, the LLM must log it.

## Turn 7 — LLM diagnoses

The LLM reads [`android.md#a02`](../references/android.md#a02) (recomposition loop from unstable state reads). The cause: the websocket handler was producing a new `List<Reaction>` on every event, which the `LazyColumn` diffed; the items were keyed by object identity not stable id.

## Turn 8 — LLM fixes and logs

Fix: items keyed by `reaction.id` explicitly in `LazyColumn`:
```kotlin
items(reactions, key = { it.id }) { reaction -> … }
```

LLM appends DL-007 to the log:

```markdown
### DL-007 — Compose LazyColumn recomposition loop with websocket updates

| Field | Value |
|-------|-------|
| **Date** | 2026-04-20 |
| **Severity** | Logic Bug |
| **Track** | android |
| **File(s)** | `android/chat/MessageItem.kt` |
| **Symptom** | `IllegalStateException: LazyColumn recomposition loop` when reactions updated via websocket. CPU spiked to 100% while loop was running. |
| **Root Cause** | `LazyColumn(items = reactions)` used positional keys by default. Every websocket event produced a new list (via `copy()`), and positional diffing treated every item as new, producing cascading recomposition. |
| **Fix** | Pass `key = { it.id }` explicitly to `items(...)`. Commit `[hash]`. |
| **Prevention Rule** | Every `LazyColumn` / `LazyRow` over a list that can update from a stream uses `key = { stableId(it) }` explicitly. Why: positional keying + stream updates produce silent recomposition loops (DL-007). |
```

## Turn 9 — LLM updates the plan

The LLM notes the learning in the session summary and, if this is the third instance of a similar "stable key" rule, promotes it to `PREVENTION_RULES.md` as `R-00N — Every streaming list uses explicit, stable keys`.

---

## What the skill bought here

- **Avoided re-shipping DL-004.** The emoji-react endpoint had idempotency by design. Without the log, the LLM might have skipped it and re-created the double-charge-style bug.
- **Avoided stale timestamps.** The dashboard timestamp formatting was client-only from the first draft.
- **Caught a new bug (DL-007) and recorded it.** The *next* time any feature uses `LazyColumn` over a streaming list, the LLM (or a human) will find the prevention rule and write the code right the first time.

The `DEBUG_LOG.md` just got ~5% more valuable for every future feature. That's the compounding.
