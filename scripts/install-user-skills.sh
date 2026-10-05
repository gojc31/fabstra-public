#!/usr/bin/env bash
# Install or update the user skills and agents shipped in user-skills/ into ~/.claude.
#
# Copies user-skills/skills/<name> to <home>/.claude/skills/<name> and
# user-skills/agents/*.md to <home>/.claude/agents/ (their LICENSE goes along as
# user-skills-agents-LICENSE, a non-.md name Claude Code ignores), replacing the
# {{SKILLS_DIR}} placeholder with the real skills folder (Windows form under
# Git Bash, so the result matches install-user-skills.ps1). A skill folder or
# agent file that already exists and differs is backed up first to
# <home>/.claude/backups/user-skills-<timestamp>/ and then replaced. Skills and
# agents that are not in the repo are never touched.
#
# Usage: scripts/install-user-skills.sh [--dry-run] [--home DIR]
#   --dry-run   print what would change; write nothing
#   --home DIR  install under DIR instead of $HOME (for testing)
# Needs: bash, perl, diff, cmp (all in Git for Windows, macOS, Linux).
set -euo pipefail

DRY=0
TARGET_HOME="${HOME}"
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --home) [ $# -ge 2 ] || { echo "--home needs a folder" >&2; exit 2; }; TARGET_HOME="$2"; shift ;;
    --home=*) TARGET_HOME="${1#--home=}" ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

command -v perl >/dev/null 2>&1 || { echo "perl is required (it ships with Git for Windows, macOS and Linux)" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_SKILLS="$REPO_ROOT/user-skills/skills"
SRC_AGENTS="$REPO_ROOT/user-skills/agents"
[ -d "$SRC_SKILLS" ] || { echo "no user-skills/skills folder at $SRC_SKILLS - run this from a clone of the repo" >&2; exit 1; }

WINDOWS=0
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WINDOWS=1 ;; esac
if [ "$WINDOWS" = 1 ]; then TARGET_HOME="$(cygpath -u "$TARGET_HOME")"; fi
case "$TARGET_HOME" in /*) ;; *) TARGET_HOME="$PWD/$TARGET_HOME" ;; esac
TARGET_HOME="${TARGET_HOME%/}"

CLAUDE_DIR="$TARGET_HOME/.claude"
DST_SKILLS="$CLAUDE_DIR/skills"
DST_AGENTS="$CLAUDE_DIR/agents"
BACKUP_ROOT="$CLAUDE_DIR/backups/user-skills-$(date +%Y%m%d-%H%M%S)"
if [ "$WINDOWS" = 1 ]; then SKILLS_DIR_VALUE="$(cygpath -w "$DST_SKILLS")"; else SKILLS_DIR_VALUE="$DST_SKILLS"; fi
export SKILLS_DIR_VALUE WINDOWS

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

substitute() {
  # Replace the placeholder in every text file under $1 that contains it.
  # Off Windows, the backslashes in the path tail after the placeholder become slashes.
  { grep -rlIF '{{SKILLS_DIR}}' "$1" 2>/dev/null || true; } | while IFS= read -r f; do
    perl -pi -e '
      if ($ENV{WINDOWS} ne "1") {
        s{\{\{SKILLS_DIR\}\}((?:\\[\w.\-]+)+)}{ my $t = $1; $t =~ tr{\\}{/}; $ENV{SKILLS_DIR_VALUE} . $t }ge;
      }
      s{\{\{SKILLS_DIR\}\}}{$ENV{SKILLS_DIR_VALUE}}g;
    ' "$f"
  done
}

BACKED_UP=0
backup() {  # backup <path> <sub-path under the backup folder>
  mkdir -p "$(dirname "$BACKUP_ROOT/$2")"
  cp -a "$1" "$BACKUP_ROOT/$2"
  BACKED_UP=$((BACKED_UP + 1))
}

if [ "$DRY" = 1 ]; then MODE="DRY RUN - nothing is written"; else MODE="install"; fi
echo "user-skills $MODE"
echo "  from   $REPO_ROOT/user-skills"
echo "  skills $DST_SKILLS"
echo "  agents $DST_AGENTS"

N_NEW=0; N_UPD=0; N_SAME=0
for src in "$SRC_SKILLS"/*/; do
  name="$(basename "$src")"
  stage="$STAGE/skills/$name"
  mkdir -p "$STAGE/skills"
  cp -a "$src" "$stage"
  find "$stage" \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
  substitute "$stage"
  dst="$DST_SKILLS/$name"
  if [ ! -d "$dst" ]; then
    status=new; detail="($(find "$stage" -type f | wc -l | tr -d ' ') files)"
  else
    report="$(diff -rq -x __pycache__ -x .pytest_cache "$stage" "$dst" || true)"
    if [ -z "$report" ]; then
      status=unchanged; detail=""
    else
      changed=$(printf '%s\n' "$report" | grep -c '^Files .* differ$' || true)
      added=$(printf '%s\n' "$report" | grep -cF "Only in $stage" || true)
      removed=$(printf '%s\n' "$report" | grep -cF "Only in $dst" || true)
      status=updated; detail="($changed changed, $added added, $removed removed; backup first)"
    fi
  fi
  case "$status" in new) N_NEW=$((N_NEW+1)) ;; updated) N_UPD=$((N_UPD+1)) ;; *) N_SAME=$((N_SAME+1)) ;; esac
  printf '  skill  %-10s %s %s\n' "$status" "$name" "$detail"
  if [ "$DRY" = 1 ] || [ "$status" = unchanged ]; then continue; fi
  if [ -d "$dst" ]; then
    backup "$dst" "skills/$name"
    rm -rf "$dst"
  fi
  mkdir -p "$DST_SKILLS"
  cp -a "$stage" "$dst"
done

install_agent() {  # install_agent <source file> <installed name>
  local src="$1" name="$2" dst status
  cp "$src" "$STAGE/agents/$name"
  substitute "$STAGE/agents"
  dst="$DST_AGENTS/$name"
  if [ ! -f "$dst" ]; then status=new
  elif cmp -s "$STAGE/agents/$name" "$dst"; then status=unchanged
  else status=updated
  fi
  case "$status" in new) N_NEW=$((N_NEW+1)) ;; updated) N_UPD=$((N_UPD+1)) ;; *) N_SAME=$((N_SAME+1)) ;; esac
  printf '  agent  %-10s %s\n' "$status" "$name"
  if [ "$DRY" = 1 ] || [ "$status" = unchanged ]; then return 0; fi
  if [ "$status" = updated ]; then backup "$dst" "agents/$name"; fi
  mkdir -p "$DST_AGENTS"
  cp "$STAGE/agents/$name" "$dst"
}

if [ -d "$SRC_AGENTS" ]; then
  mkdir -p "$STAGE/agents"
  for src in "$SRC_AGENTS"/*.md; do
    [ -f "$src" ] || continue
    install_agent "$src" "$(basename "$src")"
  done
  # The agents' licence travels with them under a non-.md name, so Claude Code never loads it as an agent.
  if [ -f "$SRC_AGENTS/LICENSE" ]; then install_agent "$SRC_AGENTS/LICENSE" user-skills-agents-LICENSE; fi
fi

echo "Summary: $N_NEW new, $N_UPD updated, $N_SAME unchanged."
if [ "$DRY" = 1 ]; then
  echo "Dry run: nothing was written."
elif [ "$BACKED_UP" -gt 0 ]; then
  echo "Backup of what was replaced: $BACKUP_ROOT"
else
  echo "Nothing existing was replaced, so no backup was needed."
fi
echo "Skills and agents that are not in the repo were left alone."
