#!/usr/bin/env bash
# Carry proofreader corrections from the Devanagari mirror back into csl-orig.
#
# WHY THIS SCRIPT IS GATED (bughunt 26-10-2026, finding 3)
# -------------------------------------------------------
# It writes GENERATED, round-tripped text into the CANONICAL source repository.
# Three ways that destroys work:
#   * a stale mirror (csl-orig pulled since the last `redo.sh`) reverts upstream
#     corrections — the silent-revert class the pre-push guard exists to stop;
#   * a lossy round trip injects conversion artefacts into the source (the
#     committed diff/ files record exactly such episodes for skd/mw/pwg);
#   * a dirty csl-orig checkout mixes the 40-file copy into another session's
#     work, and `cp` leaves no diff to review.
# Until 26-10-2026 the script was nine unconditional lines: it ran `to_slp1.py`
# and `cp` for every dictionary, with no diff, freshness or cleanliness check,
# while CLAUDE.md forbids writing to csl-orig from this repo.
#
# So it now refuses unless ALL hold:
#   1. ALLOW_CARRY=1                      deliberate intent, never an accident
#   2. run from scripts/ with ../v02      the documented invocation site
#   3. ../../csl-orig is a git checkout, CLEAN, and at origin/main
#   4. every ../diff/<dict>.txt is EMPTY  the round trip is lossless for it
#   5. mirror v02/<dict>/<dict>.txt is NOT older than csl-orig's source
# It prints the full plan before touching anything; --dry-run stops there.
#
# Usage:
#   cd scripts && ALLOW_CARRY=1 bash carry_changes_to_cslorig.sh --dry-run
#   cd scripts && ALLOW_CARRY=1 bash carry_changes_to_cslorig.sh
#
# Retiring the script outright remains an option: the monthly csl-orig
# correction queue is the sanctioned route for ordinary corrections.

set -euo pipefail

dry_run=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) dry_run=1 ;;
        -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
        *) echo "carry: unknown argument: $arg" >&2; exit 2 ;;
    esac
done

refuse() {
    echo "carry: REFUSED — $*" >&2
    echo "carry: nothing was written." >&2
    exit 2
}

# ---- 1. deliberate intent -------------------------------------------------
if [ "${ALLOW_CARRY:-}" != "1" ]; then
    refuse "set ALLOW_CARRY=1 to run this (it overwrites canonical csl-orig source)."
fi

# ---- 2. invocation site ---------------------------------------------------
if [ ! -d ../v02 ] || [ ! -d ../diff ]; then
    refuse "run from csl-devanagari/scripts/ (../v02 and ../diff must exist)."
fi

dicts=(wil yat gst ben mw72 lan lrv ap90 cae md mw shs mwe bor ae bur stc pwg gra pw ccs sch bop armh vcp skd abch acph acsj inm vei pui bhs acc krm ieg snp pe pgn mci)

# ---- 3. the target repository --------------------------------------------
cslorig="../../csl-orig"
if [ ! -d "$cslorig/v02" ]; then
    refuse "$cslorig/v02 is missing — clone csl-orig beside csl-devanagari first."
fi
git -C "$cslorig" rev-parse --git-dir >/dev/null 2>&1 \
    || refuse "$cslorig is not a git checkout."
if [ -n "$(git -C "$cslorig" status --porcelain)" ]; then
    refuse "$cslorig has uncommitted changes — commit or stash them first."
fi
cslorig_head="$(git -C "$cslorig" rev-parse HEAD)"
origin_main="$(git -C "$cslorig" rev-parse origin/main 2>/dev/null || true)"
if [ -z "$origin_main" ]; then
    refuse "$cslorig has no origin/main ref — fetch it first."
fi
if [ "$cslorig_head" != "$origin_main" ]; then
    refuse "$cslorig is not at origin/main ($(printf '%.9s' "$cslorig_head") vs $(printf '%.9s' "$origin_main")) — pull first."
fi

# ---- 4./5. per-dictionary preflight --------------------------------------
mkdir -p ../slp1
stale=()
lossy=()
for d in "${dicts[@]}"; do
    mirror="../v02/$d/$d.txt"
    source="$cslorig/v02/$d/$d.txt"
    [ -f "$mirror" ] || refuse "mirror $mirror is missing."
    [ -f "$source" ] || refuse "source $source is missing."
    if [ -s "../diff/$d.txt" ]; then
        lossy+=("$d")
    fi
    if [ "$source" -nt "$mirror" ]; then
        stale+=("$d")
    fi
done
if [ ${#lossy[@]} -gt 0 ]; then
    refuse "round-trip diff is not empty for: ${lossy[*]} — regenerate (redo.sh) and read diff/<dict>.txt before carrying."
fi
if [ ${#stale[@]} -gt 0 ]; then
    refuse "mirror is older than csl-orig source for: ${stale[*]} — rerun redo.sh against the current csl-orig first."
fi

# ---- plan ----------------------------------------------------------------
echo "carry: plan — ${#dicts[@]} dictionaries from $(pwd)/../v02 into $cslorig/v02"
for d in "${dicts[@]}"; do
    printf '  %-6s %s -> %s\n' "$d" "../v02/$d/$d.txt" "$cslorig/v02/$d/$d.txt"
done
if [ "$dry_run" -eq 1 ]; then
    echo "carry: dry run — nothing written."
    exit 0
fi

# ---- execute -------------------------------------------------------------
for d in "${dicts[@]}"; do
    echo "carry: $d"
    python3 to_slp1.py "$d"
    cp "../slp1/$d.txt" "$cslorig/v02/$d/$d.txt"
done

echo "carry: done — review with: git -C $cslorig status --short && git -C $cslorig diff"
