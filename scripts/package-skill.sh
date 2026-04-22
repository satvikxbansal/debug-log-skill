#!/usr/bin/env bash
# package-skill.sh — build a clean, upload-ready `.skill` archive.
#
# The Claude skill upload pipeline expects a zip whose *single top-level
# directory* matches the `name` field in SKILL.md's frontmatter, and that does
# not contain editor / VCS cruft (`.git/`, `.DS_Store`, `.gitignore`, etc.).
# Zipping the checkout as-is produces an archive with your whole `.git/` tree
# inside, which both bloats the upload and can push it over Anthropic's
# file-count and size limits. This script does it properly.
#
# Usage:
#   ./scripts/package-skill.sh                # writes ./dist/debug-log-skill.skill
#   ./scripts/package-skill.sh /tmp/out       # writes /tmp/out/debug-log-skill.skill
#
# Requirements: bash, zip, awk. (All standard on macOS + Linux.)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SKILL_ROOT="$(dirname -- "$SCRIPT_DIR")"
OUT_DIR="${1:-$SKILL_ROOT/dist}"

# Read the `name:` field from SKILL.md. We deliberately don't depend on Python
# or yq so this script stays runnable on a vanilla shell.
SKILL_NAME="$(awk '
  /^---[[:space:]]*$/ { sep++; next }
  sep == 1 && /^name:/ {
    sub(/^name:[[:space:]]*/, "")
    gsub(/["'\'']/, "")
    print
    exit
  }
' "$SKILL_ROOT/SKILL.md")"

if [[ -z "$SKILL_NAME" ]]; then
  echo "error: could not read 'name' from SKILL.md frontmatter" >&2
  exit 1
fi

# Sanity-check kebab-case (matches Anthropic's validator).
if ! [[ "$SKILL_NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
  echo "error: skill name '$SKILL_NAME' is not kebab-case (a-z, 0-9, -)" >&2
  exit 1
fi

# Anthropic requires the zip's single top-level directory to match the skill
# name. If this folder on disk is called something else (common — e.g., the
# GitHub repo is 'debug-log-skill' but the skill name is also 'debug-log-skill';
# or the repo is 'debug-log' and the skill is 'debug-log-skill'), we stage into
# a correctly-named directory before zipping.
STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT

STAGED="$STAGE_DIR/$SKILL_NAME"
mkdir -p "$STAGED"

# --- Exclude list (shared between rsync and fallback branches) ---------
# Patterns are kept in two parallel shapes:
#   * rsync style (one per --exclude; trailing slash for directories)
#   * find style (basenames for the pathwise prune; prefix-anchored
#     top-level dirs handled separately below)
#
# Keeping both branches in sync is critical — drift here means a file
# shows up in archives built on machines without rsync but not on CI
# (or vice-versa).

RSYNC_EXCLUDES=(
  --exclude='.git/'
  --exclude='.gitignore'
  --exclude='.gitattributes'
  --exclude='.DS_Store'
  --exclude='Thumbs.db'
  --exclude='.vscode/'
  --exclude='.idea/'
  --exclude='*.swp'
  --exclude='node_modules/'
  --exclude='__pycache__/'
  --exclude='*.pyc'
  --exclude='dist/'
  --exclude='tests/'
  # Top-level working folders we never want in a published skill:
  --exclude='/scratch/'
  --exclude='/local-notes/'
  --exclude='/drafts/'
  --exclude='/sandbox/'
)

# find-style basenames that should be pruned anywhere in the tree.
FIND_EXCLUDE_NAMES=(
  '.git' '.gitignore' '.gitattributes' '.DS_Store' 'Thumbs.db'
  '.vscode' '.idea' 'node_modules' '__pycache__' 'dist' 'tests'
)

# Top-level-only exclusions — things like `scratch/` should only match at
# the root, not `references/scratch/`.
TOP_LEVEL_EXCLUDE_DIRS=(
  'scratch' 'local-notes' 'drafts' 'sandbox'
)

if command -v rsync >/dev/null 2>&1; then
  rsync -a "${RSYNC_EXCLUDES[@]}" "$SKILL_ROOT"/ "$STAGED"/
else
  # Fallback: copy everything, then prune.
  cp -R "$SKILL_ROOT"/. "$STAGED"/

  # Prune basenames anywhere in the tree.
  for name in "${FIND_EXCLUDE_NAMES[@]}"; do
    find "$STAGED" -name "$name" -exec rm -rf {} + 2>/dev/null || true
  done

  # Prune `*.swp` and `*.pyc` anywhere.
  find "$STAGED" \( -name '*.swp' -o -name '*.pyc' \) -exec rm -f {} + \
    2>/dev/null || true

  # Prune the top-level-only working folders.
  for d in "${TOP_LEVEL_EXCLUDE_DIRS[@]}"; do
    rm -rf "$STAGED/$d" 2>/dev/null || true
  done
fi

# Confirm SKILL.md survived the copy.
if [[ ! -f "$STAGED/SKILL.md" ]]; then
  echo "error: staging copy is missing SKILL.md — copy failed?" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/$SKILL_NAME.skill"
rm -f "$OUT_FILE"

# The `.skill` format is a zip. We cd into the staging dir's parent so the
# archive's top-level entry is exactly `$SKILL_NAME/`, matching the frontmatter.
( cd "$STAGE_DIR" && zip -qr "$OUT_FILE" "$SKILL_NAME" )

FILE_COUNT="$(unzip -Z -1 "$OUT_FILE" | wc -l | tr -d ' ')"
SIZE="$(du -h "$OUT_FILE" | cut -f1)"

echo ""
echo "packaged: $OUT_FILE"
echo "  skill name : $SKILL_NAME"
echo "  size       : $SIZE"
echo "  files      : $FILE_COUNT"
echo ""
echo "upload this file to claude.ai / console.anthropic.com → Skills → Upload."
echo ""
