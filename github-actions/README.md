# github-actions

CI helpers for projects using the debug-log-skill. Upgraded for v2.0 (active knowledge graph).

## Files

| File | Purpose |
|---|---|
| `validate-debug-log.yml` | GitHub Actions workflow that runs `validate_debug_log.py` on `DEBUG_LOG.md` changes. |
| `validate_debug_log.py` | Python script that parses `DEBUG_LOG.md` and checks sequence, required fields, tag structure, Root Cause Category membership, Iterations integer, and Prevention Rule strength. |

## Install in your project

```bash
# from the repo root of the project you want to protect
mkdir -p .github/workflows .github/scripts
cp path/to/debug-log-skill/github-actions/validate-debug-log.yml .github/workflows/
cp path/to/debug-log-skill/github-actions/validate_debug_log.py   .github/scripts/
chmod +x .github/scripts/validate_debug_log.py
git add .github/workflows/validate-debug-log.yml .github/scripts/validate_debug_log.py
git commit -m "Add DEBUG_LOG v2.0 validation workflow"
```

The next PR that touches `DEBUG_LOG.md` will trigger the check.

## What it catches (v2.0)

- **Sequence.** Gaps or duplicates in the `DL-NNN` sequence. `[OBSOLETE]` entries still count — they hold their slot, they just don't participate in active rule retrieval.
- **Required fields.** Every entry must carry: `Date`, `Tags`, `Severity`, `Environment`, `File(s)`, `Symptom`, `Root Cause Category`, `Root Cause Context`, `Fix`, `Iterations`, `Prevention Rule`.
- **Date format.** Must be `YYYY-MM-DD`. The literal placeholder `YYYY-MM-DD` is tolerated only when surrounded by an HTML comment (used by the template).
- **Severity vocabulary.** Must be one of: `Build Error`, `Runtime Crash`, `ANR`, `Logic Bug`, `Flaky Test`, `Warning-as-Error`, `Perf Regression`, `Incident`, `Informational`, `Runtime Warning`, `UX Regression`, `Security`.
- **Tags.** Every entry needs **at least one track tag** (`#web #ios #android #macos #kotlin #swift #cross-cutting`) **and at least one semantic tag** (any `#Foo` beyond the track set). Tags that don't match the `#[A-Za-z][A-Za-z0-9_-]*` shape are flagged.
- **Root Cause Category.** Must be one of the 14 canonical categories: `API Change`, `API Deprecation`, `Race Condition`, `Scope Leak`, `Main Thread Block`, `Hydration Mismatch`, `Null or Unchecked Access`, `Type Coercion`, `Off-By-One`, `Syntax Error`, `Config or Build`, `Test Infrastructure`, `LLM Hallucination or Assumption`, `Other`. Using `Other` is allowed but the script expects a noun-phrase category in the Root Cause Context so future entries can promote it.
- **Iterations.** Must be a non-negative integer. `0` is first-try; `5+` in a non-`[OBSOLETE]` entry triggers a warning because it is almost always a signal of a deep hallucination loop or a missing piece of context.
- **Prevention Rule strength.** For active (non-`[OBSOLETE]`) entries, the rule must contain the literal token `**Why:**` and be at least ~40 characters. `[OBSOLETE]` entries are exempt (their rule was retired by a newer entry, and the old rule may legitimately be short).
- **`[OBSOLETE]` / supersede discipline.** When an entry's title starts with `[OBSOLETE]`, the validator expects that at least one later entry's body contains `Supersedes DL-XXX` pointing back — surfacing orphaned tombstones.

### Summary counts

At the end of a successful run the script prints `N entries (X active, Y obsolete), all valid.` so CI logs and the PR-check output give you a quick pulse on the log's shape.

## What it does NOT catch

- Whether your bug fix actually has a `DL-NNN` entry paired with it. That's a social / PR-review concern; enforce it via a PR template checkbox or a `DEBUG_LOG touched?` label rather than a linter.
- Whether the Prevention Rule is *good* (specific, checkable, imperative, carries *why*). That's a human judgement — see `CONTRIBUTING.md` for the rubric.
- Whether the chosen `Root Cause Category` is the *right* one for the described symptom. Category fit is a judgement call; the validator only enforces that the label is one of the fourteen.

## Extending

- Add a new **track** (e.g., Rust): append its tag (`#rust`) to `VALID_TRACK_TAGS` in `validate_debug_log.py` and ship a new `references/rust.md`.
- Add a new **Severity** label: append to `VALID_SEVERITIES`.
- Add a new **Root Cause Category**: append to `VALID_ROOT_CAUSE_CATEGORIES`. Do this rarely — the closed vocabulary is the *point* of the taxonomy, and adding a category without retiring an old one weakens the countable signal.
- Require a commit SHA in the Fix field, or a `[spec-tests]` token for features that are test-gated, by extending `validate_entry()`.

## Running locally

```bash
python3 github-actions/validate_debug_log.py DEBUG_LOG.md
```

Exit 0 = clean (prints the summary counts). Exit 1 = problems (printed to stderr). Exit 2 = script misuse (wrong number of args, unreadable file).

## Hooking it up as a pre-commit hook

```bash
# .git/hooks/pre-commit — make executable with chmod +x
#!/usr/bin/env bash
if git diff --cached --name-only | grep -q '^DEBUG_LOG\.md$'; then
  python3 .github/scripts/validate_debug_log.py DEBUG_LOG.md || exit 1
fi
```

Fails the commit when an invalid DL entry is staged, keeping broken entries out of the history entirely.
