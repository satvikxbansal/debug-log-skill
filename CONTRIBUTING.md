# Contributing to debug-log-skill

Thanks for considering a contribution. This skill is only as good as the real-world bugs it captures, so PRs that add battle-tested prevention rules are the most valuable.

## What's most useful

In rough order of impact:

1. **A new reference entry** — a real bug you shipped and fixed, documented in the catalog format.
2. **A new track** — e.g., Rust, Go, Flutter, React Native, Unity. Follow the shape of existing `references/*.md`.
3. **A tighter prevention rule** on an existing entry — the rule is the output that matters; sharpening one benefits every future adopter.
4. **A new worked example** — an annotated `DEBUG_LOG.md` excerpt from a real project (anonymised).
5. **Tag taxonomy extensions** in `references/tag-taxonomy.md` — if a commonly-recurring pattern has no tag, add one. Come with two DL entries where you'd use it.

## Format for a new reference entry

Every entry in `references/<track>.md` follows the same four-field shape. Copy this:

```markdown
## <a name="{track-prefix}{nn}"></a>{N}. {Short symptom title}

**Symptom.** What the user or developer saw. Quote the error message verbatim if you have it. One or two sentences.

**Root cause.** *Why* it happened — the misconception, the platform contract that was violated, the assumption that turned out to be wrong. Not "the line was wrong"; rather, "I believed X about this API, and it turned out Y."

**Fix.** What was changed. A small code snippet is welcome when it clarifies. Reference the file path pattern if it's stack-specific.

**Prevention rule.** The imperative, checkable rule that would have stopped this bug. Ends with a **Why:** one-liner — the reason, often a past incident. The why is what makes the rule usable in edge cases.
```

**Numbering.** Use the track's prefix: `w` for web, `i` for iOS, `a` for Android, `m` for macOS, `k` for Kotlin, `s` for Swift, `x` for cross-cutting. Example: `a33` for the 33rd Android entry. Add the entry to the table of contents at the top of the file in number order.

## Format for a project `DEBUG_LOG.md` entry (v2.0)

This is what the skill tells end users to write in their own projects. If you're submitting an example log or a new walkthrough, match this shape:

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Tags** | `#track-tag #semantic-tag [#more]` (at least one track tag + one semantic tag; see references/tag-taxonomy.md) |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident |
| **Environment** | Relevant SDK / library / OS versions |
| **File(s)** | `path/to/file.ext` |
| **Symptom** | What failed. Quote the error. |
| **Root Cause Category** | One of the 14 canonical categories (see below) |
| **Root Cause Context** | Why. 1–3 sentences. Name the misconception. |
| **Fix** | What changed. Commit SHA if available. |
| **Iterations** | Integer. `0` = first try. `5+` = investigate the loop. |
| **Prevention Rule** | Imperative, specific, checkable. **Why:** one-liner. |
```

### The 14 canonical Root Cause Categories

`API Change` · `API Deprecation` · `Race Condition` · `Scope Leak` · `Main Thread Block` · `Hydration Mismatch` · `Null or Unchecked Access` · `Type Coercion` · `Off-By-One` · `Syntax Error` · `Config or Build` · `Test Infrastructure` · `LLM Hallucination or Assumption` · `Other`

Full definitions with examples: `references/tag-taxonomy.md`.

### The tag rules

- At least one **track tag** from `#web #ios #android #macos #kotlin #swift #cross-cutting`.
- At least one **semantic tag** from `references/tag-taxonomy.md`.
- Inventing a new tag? Add it to the taxonomy file **in the same commit**.

## What a *good* entry looks like

**Strong**

> **Prevention rule.** Never read `window`, `document`, `localStorage`, `Date.now()`, or `Math.random()` during React render in any component that can render on the server. These belong in `useEffect` or client-only modules. **Why:** SSR/CSR mismatch corrupts the hydration tree — downstream state can be subtly wrong in ways that don't warn (DL-001 in the example log).

Specific (names the APIs), checkable (a grep finds violations), imperative (says what to do), carries *why*.

**Weak**

> **Prevention rule.** Be careful with SSR.

Generic, unverifiable, no *why*.

If the weak version is what comes out of your first draft, do one more pass.

## Review criteria

A PR will be merged if:

- The bug is real (you shipped and fixed it, or have strong evidence from someone who did).
- The required fields are present and cleanly separated.
- The prevention rule passes the "specific / checkable / imperative / carries why" test.
- Tags include at least one track + one semantic tag from the taxonomy.
- Root Cause Category is one of the 14 canonical values (or `Other` with a category name in the Root Cause Context).
- The entry is added to the track file's table of contents in number order.
- The writing is professional without being florid. This is technical documentation, not a blog post.

A PR will be rejected (with thanks) if:

- The bug is speculative ("I read in a blog post that…").
- The prevention rule is generic or hand-wavy.
- The entry duplicates an existing one without sharpening it.
- Tags use a made-up vocabulary that doesn't align with the taxonomy.

## New track

If you're adding a whole new track (say, Rust):

1. Create `references/rust.md` following the structure of `references/web.md`.
2. Update `SKILL.md`'s track list and reference list.
3. Update `README.md`'s track table.
4. Add `#rust` to the track tags in `references/tag-taxonomy.md` and add semantic tags relevant to Rust (e.g., `#Ownership`, `#Lifetime`, `#Cargo`, `#Tokio`).
5. Add track-specific questions to `references/preempt-checklist.md`.
6. Add a `templates/PREVENTION_RULES.rust.template.md` empty skeleton.
7. Update `github-actions/validate_debug_log.py`'s `VALID_TRACK_TAGS` set to include the new tag.

Aim for 15–25 entries to start. You can grow from there.

## Other welcome contributions

- Bug reports on the skill itself (broken links, frontmatter issues, typos).
- Editor integrations for other LLM harnesses (Aider variants, Continue, Zed, Windsurf, etc.) — add to `editor-integrations/`.
- Tests / CI helpers for validating the DEBUG_LOG format — add to `github-actions/` or `scripts/`.

## How to submit

1. Fork the repo.
2. Branch: `add-<track>-<nn>-<short-slug>` for a new entry; `new-track-<track>` for a new track.
3. One entry per PR, if possible. Stacked PRs for a track batch are fine.
4. Self-review against the "Review criteria" above before requesting review.

## Code of conduct

Be kind. We're all here because we've shipped bugs and want the next person to ship fewer. Debate the rule, not the author.
