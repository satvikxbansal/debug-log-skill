"""
lint.py — `dls lint` subcommand.

A thin wrapper over the same validator CI runs. Keeping the CLI
invocation identical to the workflow's means: the pass/fail verdict you
see locally matches the one that will gate your PR.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Validator sits at ../github-actions/validate_debug_log.py from this
# package. We import it as a module, so the shared parsing stays shared.
_VALIDATOR_DIR = Path(__file__).resolve().parent.parent.parent / "github-actions"
if str(_VALIDATOR_DIR) not in sys.path:
    sys.path.insert(0, str(_VALIDATOR_DIR))

import validate_debug_log  # noqa: E402

from dls._paths import resolve_log_path  # noqa: E402


DESCRIPTION = (
    "Run the same checks GitHub Actions runs. Exits 0 when the log is "
    "valid, 1 when there are problems (details on stderr), 2 on misuse."
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Require semantic tags to come from "
            "references/tag-taxonomy.md. Off by default."
        ),
    )


def run(args: argparse.Namespace) -> int:
    path = resolve_log_path(args.log)
    validator_argv = [str(path)]
    if args.strict:
        validator_argv.insert(0, "--strict")
    return validate_debug_log.main(validator_argv)
