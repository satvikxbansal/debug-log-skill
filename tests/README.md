# tests

Fixture-based test suite for the DEBUG_LOG v2.0 validator.

Each fixture in `fixtures/` is a complete `DEBUG_LOG.md` file designed to exercise exactly one check in the validator. The runner shells out to `github-actions/validate_debug_log.py` on each fixture and asserts the expected exit code (0 = valid, 1 = problem).

## Run

```bash
python3 tests/run_tests.py
```

Exit 0 if every fixture produces the expected result; exit 1 otherwise, with a diff of expected vs. actual printed to stderr.

## Adding a fixture

1. Create `fixtures/<short_name>.md` — a complete DEBUG_LOG.md whose header matches `templates/DEBUG_LOG.template.md` (so the validator's table-parsing regex sees the entries).
2. Add an entry to `EXPECTED` in `run_tests.py` with the exit code you want and, for `expected_exit=1`, a substring the failure message must contain. This is how we verify that the validator failed *for the right reason*, not just that it failed.
3. Re-run `python3 tests/run_tests.py`.

The test suite is excluded from packaged `.skill` archives (see `scripts/package-skill.sh`).
