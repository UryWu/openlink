#!/bin/bash
# scripts/sync_skill_copies.sh — keep the openlink-version-bump skill's bundled
# copies in sync with the project canonical files.
#
# The skill at .claude/skills/openlink-version-bump/ bundles copies of three
# project files (the two bump scripts and the long-form docs) for self-
# containment. The project copies at <project>/scripts/ and <project>/docs/
# remain the single source of truth; this script pushes project → skill in
# one direction.
#
# Usage:
#   ./scripts/sync_skill_copies.sh             # sync (idempotent, exit 0)
#   ./scripts/sync_skill_copies.sh --check     # exit 1 if any drift detected
#   ./scripts/sync_skill_copies.sh --verbose   # log 'identical' for every file
#
# Always idempotent. Re-run after every edit that touches the project copies.

set -e

# ── Locate dirs ──────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
SKILL_DIR="$ROOT_DIR/.claude/skills/openlink-version-bump"

# ── Parse args ───────────────────────────────────────────────
CHECK_ONLY=false
VERBOSE=false
for arg in "$@"; do
  case "$arg" in
    --check)       CHECK_ONLY=true ;;
    --verbose|-v)  VERBOSE=true ;;
    -h|--help)
      sed -n '3,16p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "unknown arg: $arg (use --help)" >&2
      exit 1
      ;;
  esac
done

# ── Logging helpers ──────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Verify skill skeleton ───────────────────────────────────
if [[ ! -d "$SKILL_DIR" ]]; then
  log_error "skill directory not found: $SKILL_DIR (initialize the skill first)"
  exit 1
fi

# ── Sync map (three parallel arrays, index-aligned) ────────
# Add a new file by appending to all three arrays on the same index.
SOURCES=(
  "$ROOT_DIR/scripts/bump_version.sh"
  "$ROOT_DIR/scripts/bump_version.ps1"
  "$ROOT_DIR/docs/version-bumping.md"
)
TARGETS=(
  "$SKILL_DIR/scripts/bump_version.sh"
  "$SKILL_DIR/scripts/bump_version.ps1"
  "$SKILL_DIR/references/version-bumping.md"
)
DESCS=(
  "bash bump script"
  "ps1 bump script"
  "long-form docs"
)

# ── Compare by content hash (CR-stripped, cross-OS safe) ───
file_hash() {
  tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1
}

# ── Iterate ─────────────────────────────────────────────────
ALREADY=0
SYNCED=0
DRIFT=0
MISSING=0

for i in "${!SOURCES[@]}"; do
  src="${SOURCES[$i]}"
  dst="${TARGETS[$i]}"
  desc="${DESCS[$i]}"

  if [[ ! -f "$src" ]]; then
    log_error "source missing: $src ($desc)"
    MISSING=$((MISSING + 1))
    continue
  fi

  dst_dir="$(dirname "$dst")"
  if [[ ! -d "$dst_dir" ]]; then
    log_warn "destination dir missing: $dst_dir (creating)"
    mkdir -p "$dst_dir"
  fi

  if [[ ! -f "$dst" ]]; then
    if $CHECK_ONLY; then
      log_warn "  $desc: target missing (drift)"
      DRIFT=$((DRIFT + 1))
    else
      log_info "  $desc: target missing, creating"
      cp -p "$src" "$dst"
      SYNCED=$((SYNCED + 1))
      log_success "  $desc: created"
    fi
    continue
  fi

  if [[ "$(file_hash "$src")" == "$(file_hash "$dst")" ]]; then
    if $VERBOSE; then
      log_success "  $desc: identical"
    fi
    ALREADY=$((ALREADY + 1))
  else
    if $CHECK_ONLY; then
      log_warn "  $desc: drift detected"
      DRIFT=$((DRIFT + 1))
    else
      log_info "  $desc: drift detected, syncing"
      cp -p "$src" "$dst"
      SYNCED=$((SYNCED + 1))
      log_success "  $desc: synced"
    fi
  fi
done

# ── Summary ────────────────────────────────────────────────
echo
log_info "summary:"
echo "    already in sync: $ALREADY"
echo "    synced:          $SYNCED"
if $CHECK_ONLY; then
  echo "    drift detected:  $DRIFT"
fi
if [[ $MISSING -gt 0 ]]; then
  log_error "  source missing:  $MISSING"
  exit 1
fi

if $CHECK_ONLY && [[ $DRIFT -gt 0 ]]; then
  log_error "--check failed: skill copies are out of sync"
  log_error "  run without --check to sync, or commit a fresh skill snapshot first"
  exit 1
fi

if $CHECK_ONLY; then
  log_success "--check passed"
fi

exit 0
