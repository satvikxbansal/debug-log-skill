# github-actions

CI helpers for projects using the debug-log-skill.

## Files

| File | Purpose |
|---|---|
| `validate-debug-log.yml` | GitHub Actions workflow that runs `validate_debug_log.py` on `DEBUG_LOG.md` changes. |
| `validate_debug_log.py` | Python script that parses `DEBUG_LOG.md` and checks sequence integrity + field completeness. |

## Install in your project

```bash
# from the repo root of the project you want to protect
mkdir -p .github/workflows .github/scripts
cp path/to/debug-log-skill/github-actions/validate-debug-log.yml .github/workflows/
cp path/to/debug-log-skill/github-actions/validate_debug_log.py   .github/scripts/
chmod +x .github/scripts/validate_debug_log.py
git add .github/workflows/validate-debug-log.yml .github/scripts/validate_debug_log.py
git commit -m "Add DEBUG_LOG validation workflow"
```

Next PR that touches `DEBUG_LOG.md` will see the check run.

## What it catches

- Gaps or duplicates in the `DL-NNN` sequence.
- Missing required fields (Date, Severity, Track, File(s), Symptom, Root Cause, Fix, Prevention Rule).
- Malformed dates (must be `YYYY-MM-DD`).
- Unknown Severity or Track labels.
- Prevention Rules missing the `Why:` marker.
- Prevention Rules that are suspiciously short (< 40 chars).

## What it does NOT catch

- Whether your bug fix actually has a `DL-NNN` entry paired with it. That's a social / PR-review concern, not something a linter can decide reliably.
- Whether the prevention rule is *good* (specific, checkable, imperative). That is a human judgment — see `CONTRIBUTING.md` for the rubric.

## Extending

- Change the list of accepted Severity / Track labels by editing the `VALID_SEVERITIES` and `VALID_TRACKS` sets at the top of `validate_debug_log.py`.
- Add stricter checks (e.g., require a commit SHA in the Fix field) by extending `validate_entry()`.

## Running locally

```bash
python3 github-actions/validate_debug_log.py DEBUG_LOG.md
```

Exit 0 = clean. Exit 1 = problems (printed to stderr). Exit 2 = script misuse.
