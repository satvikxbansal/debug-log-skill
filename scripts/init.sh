#!/usr/bin/env bash
# init.sh — set up debug-log-skill in the current project.
#
# Usage:
#   From inside the debug-log-skill folder:
#     ./scripts/init.sh /path/to/your/project
#
#   From anywhere, if the skill is installed as a submodule or cloned sibling:
#     bash /path/to/debug-log-skill/scripts/init.sh /path/to/your/project
#
# What it does:
#   1. Copies DEBUG_LOG.template.md to <project>/DEBUG_LOG.md (won't overwrite).
#   2. Copies PREVENTION_RULES.template.md to <project>/PREVENTION_RULES.md.
#   3. Drops a stub CLAUDE.md into the project root that points at both files
#      and instructs Claude / Claude Code to follow the DEBUG_LOG protocol.
#   4. Prints clear next steps.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SKILL_ROOT="$(dirname -- "$SCRIPT_DIR")"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <path-to-your-project>" >&2
  echo "" >&2
  echo "example:" >&2
  echo "  $0 ~/code/my-app" >&2
  exit 1
fi

PROJECT="$1"

if [[ ! -d "$PROJECT" ]]; then
  echo "error: $PROJECT is not a directory" >&2
  exit 1
fi

DEBUG_LOG_SRC="$SKILL_ROOT/templates/DEBUG_LOG.template.md"
PREVENTION_SRC="$SKILL_ROOT/templates/PREVENTION_RULES.template.md"

if [[ ! -f "$DEBUG_LOG_SRC" ]]; then
  echo "error: could not find $DEBUG_LOG_SRC. Is the skill folder intact?" >&2
  exit 1
fi

DEBUG_LOG_DST="$PROJECT/DEBUG_LOG.md"
PREVENTION_DST="$PROJECT/PREVENTION_RULES.md"
CLAUDE_DST="$PROJECT/CLAUDE.md"

installed=0
skipped=0

copy_if_absent() {
  local src="$1"
  local dst="$2"
  local label="$3"

  if [[ -f "$dst" ]]; then
    echo "  skip  $label — already exists at $dst"
    skipped=$((skipped + 1))
  else
    cp "$src" "$dst"
    echo "  wrote $label -> $dst"
    installed=$((installed + 1))
  fi
}

echo ""
echo "debug-log-skill — initialising in $PROJECT"
echo ""

copy_if_absent "$DEBUG_LOG_SRC"  "$DEBUG_LOG_DST"  "DEBUG_LOG.md"
copy_if_absent "$PREVENTION_SRC" "$PREVENTION_DST" "PREVENTION_RULES.md"

# Stub CLAUDE.md — only created if absent. Does NOT overwrite an existing one.
if [[ -f "$CLAUDE_DST" ]]; then
  echo "  skip  CLAUDE.md — already exists. Append these lines manually:"
  echo ""
  echo "    ## DEBUG_LOG discipline (v2.0)"
  echo "    This project follows the debug-log-skill protocol."
  echo "    - Active pre-flight: before editing, grep DEBUG_LOG.md by file/tag/Root Cause Category."
  echo "    - After any bug fix, append a DL-NNN entry in the same commit, using the v2.0 template"
  echo "      (Tags, Environment, Root Cause Category, Iterations, Prevention Rule)."
  echo "    - Retired rules get [OBSOLETE] prepended to the title; supersede with a new entry."
  echo "    - Rules that fire in 3+ active entries get promoted to PREVENTION_RULES.md."
  echo "    See: https://github.com/<you>/debug-log-skill"
  echo ""
  skipped=$((skipped + 1))
else
  cat > "$CLAUDE_DST" <<'EOF'
# CLAUDE.md

Project-level instructions for Claude / Claude Code.

## DEBUG_LOG discipline (v2.0)

This project follows the [debug-log-skill](https://github.com/<you>/debug-log-skill) protocol v2.0.

### The four non-negotiable rules

1. **Sequence.** Entries are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip, never reuse.
2. **Never skip.** Every bug fix — build error, runtime crash, logic bug, flaky test, perf regression, incident — gets a `DL-NNN` entry in `DEBUG_LOG.md`, in the same commit as the fix.
3. **Active pre-flight, not passive skim.** Before editing any file, grep `DEBUG_LOG.md` for the filename, relevant tag, or Root Cause Category. Read only the entries that match.
4. **Append-only.** Never delete or edit an existing entry. When one becomes obsolete, prepend `[OBSOLETE]` to its title (the only permitted mutation) and supersede with a new entry.

### Active pre-flight — grep patterns

Run at least one before editing:

```bash
# By file path (strongest signal)
grep -niE "path/to/File\.ext" DEBUG_LOG.md

# By tag (see tag-taxonomy.md in the skill)
grep -niE "#Compose|#StateFlow|#Hydration" DEBUG_LOG.md

# By Root Cause Category
grep -niE "Race Condition|Scope Leak|LLM Hallucination" DEBUG_LOG.md
```

### Where things live

- `DEBUG_LOG.md` — the append-only log, numbered `DL-NNN`.
- `PREVENTION_RULES.md` — promoted rules (any rule appearing in ≥ 3 active entries).

### Entry template (v2.0)

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Tags** | `#track-tag #semantic-tag [#more]` — at least one track tag + one semantic tag |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident |
| **Environment** | Relevant SDK / library / OS versions |
| **File(s)** | `path/to/file.ext` |
| **Symptom** | What failed. Quote the error. |
| **Root Cause Category** | API Change / API Deprecation / Race Condition / Scope Leak / Main Thread Block / Hydration Mismatch / Null or Unchecked Access / Type Coercion / Off-By-One / Syntax Error / Config or Build / Test Infrastructure / LLM Hallucination or Assumption / Other |
| **Root Cause Context** | Why. 1–3 sentences. Name the misconception. |
| **Fix** | What changed. Commit SHA if available. |
| **Iterations** | Integer. `0` = first try. `5+` = investigate the loop. |
| **Prevention Rule** | Imperative, specific, checkable. **Why:** one-liner. |
```
EOF
  echo "  wrote CLAUDE.md -> $CLAUDE_DST"
  installed=$((installed + 1))
fi

echo ""
echo "done — $installed file(s) created, $skipped file(s) skipped."
echo ""
echo "next steps:"
echo "  1. Open $PROJECT/DEBUG_LOG.md and fill in the 'Tracks active' checklist."
echo "  2. Commit DEBUG_LOG.md, PREVENTION_RULES.md, and CLAUDE.md."
echo "  3. Next time you fix a bug, append DL-001 — read SKILL.md in this skill folder for the exact format."
echo ""
