"""
dls — the `DEBUG_LOG` swiss-army CLI.

The package ships alongside the skill in `scripts/dls/`. Invoke it with:

    python3 scripts/dls <subcommand> [args]

Subcommands:
  lint        Validate DEBUG_LOG.md against the v2.0 contract.
  stats       Frequency counts, distributions, and promotion candidates.
  query       Filter entries by tag / category / severity / file / id.
  relevant    Phase 4 primitive: surface entries touching given paths.
  doctor      Deeper health checks (stale rules, Artifact resolution, …).
  supersede   Tombstone DL-OLD and append a stub superseder.
  stub        Append an entry skeleton with explicit TODO: markers.

The package is stdlib-only. It imports `debug_log_schema` and
`debug_log_parser` from its parent `scripts/` directory — `__main__.py`
adds that directory to `sys.path` at startup.

Every subcommand takes `--log PATH` to point at a specific DEBUG_LOG.md.
Without it the CLI searches upwards from the current directory (so you can
run `python3 scripts/dls lint` from anywhere inside a project).
"""

__version__ = "2.1.0"
