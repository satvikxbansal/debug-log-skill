#!/usr/bin/env bash
# init.sh — set up debug-log-skill in the current project.
#
# Usage:
#   From inside the debug-log-skill folder:
#     ./scripts/init.sh /path/to/your/project [track ...]
#
#   From anywhere, if the skill is installed as a submodule or cloned sibling:
#     bash /path/to/debug-log-skill/scripts/init.sh /path/to/your/project web ios
#
# If tracks are omitted, init.sh detects them from the target project's
# files (package.json -> web, *.xcodeproj -> ios, build.gradle.kts -> android,
# etc.). Pass explicit tracks to override.
#
# What it does:
#   1. Copies DEBUG_LOG.template.md  -> <project>/DEBUG_LOG.md     (if absent).
#   2. For each detected track, copies the matching PREVENTION_RULES
#      template; if no track matches, falls back to the generic one.
#   3. Drops stub CLAUDE.md, AGENTS.md, and .cursor/rules/debug-log.mdc into
#      the project root — each one pointing at the four rules + the v2.0
#      template + the grep patterns. Never overwrites.
#   4. Prints clear next steps.
#
# The script is idempotent: re-running it on an initialised project prints
# "skip" lines but never clobbers an existing file.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SKILL_ROOT="$(dirname -- "$SCRIPT_DIR")"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <path-to-your-project> [track ...]" >&2
  echo "" >&2
  echo "example:" >&2
  echo "  $0 ~/code/my-app" >&2
  echo "  $0 ~/code/my-app web ios android" >&2
  exit 1
fi

PROJECT="$1"
shift
EXPLICIT_TRACKS=("$@")

if [[ ! -d "$PROJECT" ]]; then
  echo "error: $PROJECT is not a directory" >&2
  exit 1
fi

DEBUG_LOG_SRC="$SKILL_ROOT/templates/DEBUG_LOG.template.md"
if [[ ! -f "$DEBUG_LOG_SRC" ]]; then
  echo "error: could not find $DEBUG_LOG_SRC. Is the skill folder intact?" >&2
  exit 1
fi

DEBUG_LOG_DST="$PROJECT/DEBUG_LOG.md"
PREVENTION_DST="$PROJECT/PREVENTION_RULES.md"
CLAUDE_DST="$PROJECT/CLAUDE.md"
AGENTS_DST="$PROJECT/AGENTS.md"
CURSOR_DST_DIR="$PROJECT/.cursor/rules"
CURSOR_DST="$CURSOR_DST_DIR/debug-log.mdc"

installed=0
skipped=0

echo ""
echo "debug-log-skill — initialising in $PROJECT"
echo ""

# ----------------------------------------------------------------------------
# Track detection
# ----------------------------------------------------------------------------
detect_tracks() {
  local tracks=()
  [[ -f "$PROJECT/package.json" ]] && tracks+=("web")
  # Any .xcodeproj or .xcworkspace => ios (good heuristic; macOS projects
  # tend to have both but also .entitlements / AppKit references).
  if compgen -G "$PROJECT/*.xcodeproj" > /dev/null \
     || compgen -G "$PROJECT/*.xcworkspace" > /dev/null; then
    tracks+=("ios")
  fi
  # Android.
  [[ -f "$PROJECT/build.gradle.kts" || -f "$PROJECT/build.gradle" ]] \
    && tracks+=("android")
  # macOS entitlements file in the root (not a hard signal, but common).
  if compgen -G "$PROJECT/*.entitlements" > /dev/null; then
    tracks+=("macos")
  fi
  # Kotlin-as-language if a top-level build file is present and the project
  # isn't already flagged android (catches KMP / server Kotlin).
  if [[ -f "$PROJECT/settings.gradle.kts" ]] \
     && [[ ! " ${tracks[*]:-} " =~ " android " ]]; then
    tracks+=("kotlin")
  fi
  # Swift-as-language.
  if [[ -f "$PROJECT/Package.swift" ]] \
     && [[ ! " ${tracks[*]:-} " =~ " ios " ]] \
     && [[ ! " ${tracks[*]:-} " =~ " macos " ]]; then
    tracks+=("swift")
  fi

  if (( ${#tracks[@]} == 0 )); then
    tracks+=("cross-cutting")
  fi
  printf '%s\n' "${tracks[@]}"
}

if (( ${#EXPLICIT_TRACKS[@]} > 0 )); then
  mapfile -t TRACKS < <(printf '%s\n' "${EXPLICIT_TRACKS[@]}")
  echo "  tracks (explicit): ${TRACKS[*]}"
else
  mapfile -t TRACKS < <(detect_tracks)
  echo "  tracks (detected): ${TRACKS[*]}"
fi
echo ""

# ----------------------------------------------------------------------------
# Copy helpers
# ----------------------------------------------------------------------------
copy_if_absent() {
  local src="$1"
  local dst="$2"
  local label="$3"

  if [[ -f "$dst" ]]; then
    echo "  skip  $label — already exists at $dst"
    skipped=$((skipped + 1))
  else
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "  wrote $label -> $dst"
    installed=$((installed + 1))
  fi
}

# ----------------------------------------------------------------------------
# 1. DEBUG_LOG.md
# ----------------------------------------------------------------------------
copy_if_absent "$DEBUG_LOG_SRC" "$DEBUG_LOG_DST" "DEBUG_LOG.md"

# ----------------------------------------------------------------------------
# 2. PREVENTION_RULES.md
#
# Prefer a per-track template if exactly one track is selected. For multi-
# track projects fall back to the generic template so authors concatenate
# their own rules rather than scaffolding a misleading single-track file.
# ----------------------------------------------------------------------------
PREVENTION_SRC=""
if (( ${#TRACKS[@]} == 1 )); then
  single="${TRACKS[0]}"
  CANDIDATE="$SKILL_ROOT/templates/PREVENTION_RULES.${single}.template.md"
  if [[ -f "$CANDIDATE" ]]; then
    PREVENTION_SRC="$CANDIDATE"
  fi
fi
if [[ -z "$PREVENTION_SRC" ]]; then
  PREVENTION_SRC="$SKILL_ROOT/templates/PREVENTION_RULES.template.md"
fi
copy_if_absent "$PREVENTION_SRC" "$PREVENTION_DST" "PREVENTION_RULES.md"

# ----------------------------------------------------------------------------
# 3. Editor integration stubs — CLAUDE.md, AGENTS.md, .cursor/rules/debug-log.mdc
#
# Each one is self-contained and points at the four rules + the grep patterns
# + the v2.0 entry template. They never overwrite an existing file; if one
# exists, init.sh prints the section the user should merge in by hand.
# ----------------------------------------------------------------------------

STUB_ADVICE_CLAUDE=$(cat <<'TXT'
## DEBUG_LOG discipline (v2.0)
This project follows the debug-log-skill protocol.
- Active pre-flight: before editing, grep DEBUG_LOG.md by file / tag / Root Cause Category.
- After any bug fix, append a DL-NNN entry in the same commit, using the v2.0 11-field template.
- Retired rules get [OBSOLETE] prepended to the title; supersede with a new entry.
- Rules that appear in 3+ active entries get promoted to PREVENTION_RULES.md.
TXT
)

if [[ -f "$CLAUDE_DST" ]]; then
  echo "  skip  CLAUDE.md — already exists. Merge this section in by hand:"
  echo ""
  printf "    %s\n" "$STUB_ADVICE_CLAUDE" | sed 's/^    /    /'
  echo ""
  skipped=$((skipped + 1))
else
  cat > "$CLAUDE_DST" <<'EOF'
# CLAUDE.md

Project-level instructions for Claude / Claude Code / Cowork.

## DEBUG_LOG discipline (v2.0)

This project follows the [debug-log-skill](https://github.com/YOUR_ORG/debug-log-skill) protocol v2.0 — an active knowledge graph for bug history.

### The four non-negotiable rules

1. **Sequence.** Entries in `DEBUG_LOG.md` are numbered `DL-001`, `DL-002`, `DL-003`, … Never skip. Never reuse.
2. **Never skip.** Every bug fix — build error, runtime crash, logic bug, flaky test, perf regression, incident — gets a `DL-NNN` entry in the same commit as the fix.
3. **Active pre-flight, not passive skim.** Before editing any file, grep `DEBUG_LOG.md` for the filename, relevant tags, or Root Cause Category. Read only the entries that match.
4. **Append-only.** Never delete or edit an existing entry. When one becomes obsolete, prepend `[OBSOLETE]` to its title (the only permitted mutation) and supersede with a new entry whose body starts with `> Supersedes DL-XXX. Reason: ...`.

### Active pre-flight — grep patterns

```bash
# By file path (strongest signal)
grep -niE "path/to/File\.ext" DEBUG_LOG.md

# By tag (see references/tag-taxonomy.md in the skill)
grep -niE "#Compose|#StateFlow|#Hydration" DEBUG_LOG.md

# By Root Cause Category
grep -niE "Race Condition|Scope Leak|LLM Hallucination" DEBUG_LOG.md
```

### Entry template (v2.0)

```markdown
### DL-XXX — [Short Title]

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Tags** | `#track-tag #semantic-tag [#more]` — 1-2 track tags + at least one semantic tag |
| **Severity** | Build Error / Runtime Crash / ANR / Logic Bug / Flaky Test / Warning-as-Error / Perf Regression / Incident (or extended: Informational, Runtime Warning, UX Regression, Security) |
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

if [[ -f "$AGENTS_DST" ]]; then
  echo "  skip  AGENTS.md — already exists. Merge the DEBUG_LOG discipline section in by hand."
  skipped=$((skipped + 1))
else
  cat > "$AGENTS_DST" <<'EOF'
# AGENTS.md

Project-level instructions for Aider / Codex CLI / OpenAI Agents SDK / any harness that reads AGENTS.md.

## DEBUG_LOG discipline (v2.0)

When you begin any non-trivial task in this repository:

1. Grep `DEBUG_LOG.md` by filename / tag / Root Cause Category before editing. Do not read end-to-end.
2. Read `references/<track>.md` in the skill folder for each track this project uses, plus `references/cross-cutting.md` and `references/tag-taxonomy.md`.
3. For new features, also read `references/pre-mortem-workflow.md` and `references/preempt-checklist.md`.
4. Name the DL numbers your grep surfaced in your plan before writing code.

After fixing any bug, append a `DL-NNN` entry in `DEBUG_LOG.md` in the same commit as the fix, using the v2.0 11-field template. Retire obsolete rules with `[OBSOLETE]` and a superseding entry whose body starts with `> Supersedes DL-XXX. Reason: ...`.

The four non-negotiable rules are: (1) contiguous sequence, (2) never skip, (3) active pre-flight not passive skim, (4) append-only.
EOF
  echo "  wrote AGENTS.md -> $AGENTS_DST"
  installed=$((installed + 1))
fi

if [[ -f "$CURSOR_DST" ]]; then
  echo "  skip  .cursor/rules/debug-log.mdc — already exists."
  skipped=$((skipped + 1))
else
  mkdir -p "$CURSOR_DST_DIR"
  cat > "$CURSOR_DST" <<'EOF'
---
description: DEBUG_LOG discipline v2.0 — grep DEBUG_LOG.md before coding (do not read end-to-end), append a DL-NNN entry after every bug fix with Tags / Environment / Root Cause Category / Iterations, never skip an entry, mark retired entries [OBSOLETE]. Loads catalog references for the project's track(s).
globs:
  - "**/*"
alwaysApply: true
---

# DEBUG_LOG discipline (v2.0)

Before writing any non-trivial code: grep `DEBUG_LOG.md` for the file, tag, or Root Cause Category that applies. Read only matching entries. After fixing any bug: append a `DL-NNN` entry in the same commit as the fix, using the 11-field v2.0 template. Retire obsolete rules with `[OBSOLETE]` + a superseding entry. Never skip, never delete.
EOF
  echo "  wrote .cursor/rules/debug-log.mdc -> $CURSOR_DST"
  installed=$((installed + 1))
fi

# ----------------------------------------------------------------------------
# Done
# ----------------------------------------------------------------------------
echo ""
echo "done — $installed file(s) created, $skipped file(s) skipped."
echo ""
echo "next steps:"
echo "  1. Open $PROJECT/DEBUG_LOG.md and fill in the 'Tracks active' checklist."
echo "  2. Commit DEBUG_LOG.md, PREVENTION_RULES.md, CLAUDE.md, AGENTS.md, .cursor/rules/."
echo "  3. Next time you fix a bug, append DL-001 using the v2.0 11-field template."
echo "  4. (Optional) copy github-actions/validate-debug-log.yml + the two .py scripts"
echo "     into .github/ for CI validation on PRs."
echo ""
