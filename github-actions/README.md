# github-actions

CI helpers for projects using the debug-log-skill. v2.1 (active knowledge graph + placeholder-sentinel guard).

## Files

| File | Purpose |
|---|---|
| `validate-debug-log.yml` | GitHub Actions workflow that runs `validate_debug_log.py` on `DEBUG_LOG.md` changes. |
| `validate_debug_log.py` | Python script that parses `DEBUG_LOG.md` and checks the v2.0 contract (plus v2.1 placeholder-sentinel rejection). Imports from `debug_log_schema.py` AND `debug_log_parser.py`. |
| `../scripts/debug_log_schema.py` | Single source of truth for the vocabulary (required fields, severities, Root Cause Categories, track tags, semantic-tag taxonomy, placeholder sentinels). The validator, the parser, the `dls` CLI, and the test fixtures all import this file. |
| `../scripts/debug_log_parser.py` | Shared entry-parsing module used by the validator and the `dls` CLI. Imports the schema; extracted so the validator and the CLI cannot drift on how entries are tokenised. |

## Install in your project

```bash
# from the repo root of the project you want to protect
mkdir -p .github/workflows .github/scripts
cp path/to/debug-log-skill/github-actions/validate-debug-log.yml .github/workflows/
cp path/to/debug-log-skill/github-actions/validate_debug_log.py   .github/scripts/
cp path/to/debug-log-skill/scripts/debug_log_schema.py            .github/scripts/
cp path/to/debug-log-skill/scripts/debug_log_parser.py            .github/scripts/
chmod +x .github/scripts/validate_debug_log.py
git add .github/workflows/validate-debug-log.yml \
        .github/scripts/validate_debug_log.py \
        .github/scripts/debug_log_schema.py \
        .github/scripts/debug_log_parser.py
git commit -m "Add DEBUG_LOG v2.1 validation workflow"
```

All three Python files must land side-by-side in `.github/scripts/` — the validator imports the schema and the parser at startup. Any missing file raises `ModuleNotFoundError` and breaks CI before the first entry is checked.

The next PR that touches `DEBUG_LOG.md` (or either script) will trigger the check.

## What it catches (v2.0)

- **Sequence.** Gaps or duplicates in the `DL-NNN` sequence. `[OBSOLETE]` entries still count — they hold their slot, they just don't participate in active rule retrieval.
- **HTML-commented entries are skipped.** The template ships with a commented DL-001 example; without this, a freshly-initialised log would report "2 entries" on its first run. The validator strips HTML comments before parsing.
- **Required fields.** Every entry must carry all 11 v2.0 fields: `Date`, `Tags`, `Severity`, `Environment`, `File(s)`, `Symptom`, `Root Cause Category`, `Root Cause Context`, `Fix`, `Iterations`, `Prevention Rule`.
- **Date format.** Must be `YYYY-MM-DD`. The literal placeholder `YYYY-MM-DD` is tolerated only on the seed entry.
- **Severity vocabulary.** Must be one of the 8 core severities (`Build Error`, `Runtime Crash`, `ANR`, `Logic Bug`, `Flaky Test`, `Warning-as-Error`, `Perf Regression`, `Incident`) or one of the 4 extended ones (`Informational`, `Runtime Warning`, `UX Regression`, `Security`).
- **Tags.** Every entry needs **1–2 track tags** (`#web #ios #android #macos #kotlin #swift #cross-cutting`) and **at least one semantic tag** beyond the track set. Track tags are deduplicated case-insensitively; three or more track tags fails. Tags that don't match the `#[A-Za-z][A-Za-z0-9_-]*` shape are flagged.
- **Root Cause Category.** Must be one of the 14 canonical categories: `API Change`, `API Deprecation`, `Race Condition`, `Scope Leak`, `Main Thread Block`, `Hydration Mismatch`, `Null or Unchecked Access`, `Type Coercion`, `Off-By-One`, `Syntax Error`, `Config or Build`, `Test Infrastructure`, `LLM Hallucination or Assumption`, `Other`. Using `Other` is allowed but the script expects a noun-phrase category in the Root Cause Context so future entries can promote it.
- **Iterations.** Must be a non-negative integer. `0` is first-try. The script accepts `3 (actor race)` — anything starting with an integer.
- **Prevention Rule strength.** For active (non-`[OBSOLETE]`) entries, the rule must contain a `Why:` marker (looks for `**Why:**`, `Why:`, or `why:`) and be at least 40 characters. `[OBSOLETE]` entries are exempt — their rule was retired by a newer entry, and the old rule may legitimately be short.
- **`[OBSOLETE]` / supersede discipline (both directions).**
  - If an entry's title starts with `[OBSOLETE]`, at least one **later** entry's body must contain `Supersedes DL-XXX` pointing back — orphaned tombstones fail.
  - If any entry's body contains `Supersedes DL-XXX`, the referenced entry must exist **and** its title must start with `[OBSOLETE]` — dangling or mis-targeted references fail.
- **Placeholder-sentinel rejection (v2.1).** Active entries are rejected if any required narrative field (`Environment`, `File(s)`, `Symptom`, `Root Cause Context`, `Fix`, `Prevention Rule`) still contains `TODO:`, `FIXME:`, `XXX:`, or `PLACEHOLDER`. This closes the "`dls stub --write` commits scaffolding that passes lint" gap — a validator-clean fake entry is worse than no entry, because it creates the illusion of rigor. `[OBSOLETE]` entries are exempt (their fields were authored under an earlier contract).
- **Artifact link soft-check (v2.1).** If an entry has an optional `Artifact` field, the validator resolves the path relative to the log's repo. Missing paths fail — *except* the canonical `.debug-log/incidents/DL-NNN.md` sidecar, which is soft-allowed because the sidecar is usually authored in the same PR.

### `--strict` mode

```bash
python3 .github/scripts/validate_debug_log.py --strict DEBUG_LOG.md
```

In strict mode, semantic tags must come from `references/tag-taxonomy.md`. This is useful once the project's taxonomy has stabilised — turn it on in CI when you're ready to say "new tags must be added to the taxonomy first." Default mode keeps the semantic-tag list open so first-time users aren't blocked by tag discipline.

### Summary counts

At the end of a successful run the script prints
`DEBUG_LOG.md (v2.0): N entries (X active, Y obsolete), all valid.`
so CI logs and the PR-check output give you a quick pulse on the log's shape.

## What it does NOT catch

- Whether your bug fix actually has a `DL-NNN` entry paired with it. That's a social / PR-review concern; enforce it via a PR template checkbox or a `DEBUG_LOG touched?` label rather than a linter.
- Whether the Prevention Rule is *good* (specific, checkable, imperative, carries *why*). That's a human judgement — see `CONTRIBUTING.md` for the rubric.
- Whether the chosen `Root Cause Category` is the *right* one for the described symptom. Category fit is a judgement call; the validator only enforces that the label is one of the fourteen.

## Extending

Because the schema is centralised in `scripts/debug_log_schema.py`, extending vocabularies is a one-file change:

- **Add a new track** (e.g., Rust): append `#rust` to `TRACK_TAGS` in `debug_log_schema.py` and ship a new `references/rust.md`.
- **Add a new severity**: append to `SEVERITIES_CORE` or `SEVERITIES_EXTENDED`. Bump the CHANGELOG.
- **Add a new Root Cause Category**: append to `ROOT_CAUSE_CATEGORIES`. Do this rarely — the closed vocabulary is the *point* of the taxonomy, and adding a category without retiring an old one weakens the countable signal.
- **Add a new semantic tag**: append to `SEMANTIC_TAGS_TAXONOMY` in the schema, and add it to the matching section of `references/tag-taxonomy.md` in the same commit.

Each of these changes is picked up automatically by the validator, the fixture test suite, and the forthcoming CLI — no duplicate-constant hunt required.

## Running locally

```bash
python3 github-actions/validate_debug_log.py DEBUG_LOG.md
python3 github-actions/validate_debug_log.py --strict DEBUG_LOG.md
```

Exit 0 = clean (prints the summary counts). Exit 1 = problems (printed to stderr). Exit 2 = script misuse (wrong number of args, unreadable file, missing schema module).

## Hooking it up as a pre-commit hook

```bash
# .git/hooks/pre-commit — make executable with chmod +x
#!/usr/bin/env bash
if git diff --cached --name-only | grep -q '^DEBUG_LOG\.md$'; then
  python3 .github/scripts/validate_debug_log.py DEBUG_LOG.md || exit 1
fi
```

Fails the commit when an invalid DL entry is staged, keeping broken entries out of the history entirely.
