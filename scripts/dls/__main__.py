"""
__main__.py — argparse dispatcher for `python3 scripts/dls`.

Subcommands are discovered from this file's constant table so adding one is
a single edit. Each handler module exposes two things:

  * `add_arguments(parser: argparse.ArgumentParser) -> None` — register the
    subcommand's CLI flags.
  * `run(args: argparse.Namespace) -> int` — execute and return an exit code.

Shared flags (`--log`) are attached to every subcommand uniformly.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make sibling modules (debug_log_schema, debug_log_parser) importable when
# run as `python3 scripts/dls`. The scripts/ dir is this file's grandparent.
_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from dls import __version__  # noqa: E402
from dls import (  # noqa: E402
    doctor,
    lint,
    query,
    relevant,
    stats,
    stub,
    supersede,
)


_SUBCOMMANDS = (
    ("lint", lint, "Validate DEBUG_LOG.md against the v2.0 contract."),
    ("stats", stats, "Frequency counts, distributions, promotion hints."),
    ("query", query, "Filter entries by tag / category / severity / file."),
    ("relevant", relevant, "Surface entries touching given file paths."),
    ("doctor", doctor, "Deeper health checks (stale rules, Artifact paths)."),
    ("supersede", supersede, "Tombstone an old entry and append a superseder."),
    ("stub", stub, "Emit a skeleton entry with explicit TODO: markers."),
)


def _add_shared(parser: argparse.ArgumentParser) -> None:
    """Flags every subcommand honours."""
    parser.add_argument(
        "--log",
        metavar="PATH",
        default=None,
        help=(
            "Path to DEBUG_LOG.md. Defaults to an upward search from the "
            "current directory."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dls",
        description=(
            "DEBUG_LOG Swiss-army CLI. Lint, query, and safely extend your "
            "project's DEBUG_LOG.md. The skill's discipline is that humans "
            "write entries; this CLI helps you *find* and *verify* them, "
            "never author them end-to-end."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"dls {__version__}",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="command",
        metavar="{subcommand}",
    )
    subparsers.required = True

    for name, module, help_text in _SUBCOMMANDS:
        sub = subparsers.add_parser(
            name,
            help=help_text,
            description=getattr(module, "DESCRIPTION", help_text),
        )
        _add_shared(sub)
        module.add_arguments(sub)
        sub.set_defaults(_handler=module.run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "_handler", None)
    if handler is None:  # pragma: no cover — argparse enforces `required`
        parser.print_help(file=sys.stderr)
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
