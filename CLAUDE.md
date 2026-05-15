# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**csl-devanagari** converts the CDSL dictionary source files from SLP1 transliteration (as in `csl-orig`) to Devanagari script. It stores the Devanagari versions alongside diff files to verify that the conversion is fully invertible.

## Architecture

| Directory/File | Purpose |
|---|---|
| `v02/` | Devanagari-encoded dictionary text files, mirroring `csl-orig/v02/` structure |
| `scripts/` | Conversion scripts: `to_devanagari.py`, `to_slp1.py`, `redo.sh`, `redo_all.sh` |
| `diff/` | Diff output comparing round-tripped SLP1 against `csl-orig` (should be empty/zero lines) |

### Conversion pipeline

```
csl-orig/v02/<dict>/<dict>.txt  →  to_devanagari.py  →  v02/<dict>/<dict>.txt
v02/<dict>/<dict>.txt           →  to_slp1.py         →  slp1/<dict>.txt (not tracked)
slp1/<dict>.txt vs csl-orig/v02/<dict>/<dict>.txt     →  diff/<dict>.txt
```

The `slp1/` directory is **not tracked** by git (intermediate verification only). The ideal state is that `diff/<dict>.txt` is empty for all dictionaries.

### Invertibility requirement

Every change to `csl-orig` source must survive the `to_devanagari.py` → `to_slp1.py` round-trip with zero diff. Non-zero diff entries in `diff/` indicate encoding issues in the source file.

## Common Commands

### Regenerate Devanagari for one dictionary (from `scripts/`)
```bash
bash redo.sh <dict>
# e.g.: bash redo.sh mw
```

### Regenerate all dictionaries (from `scripts/`)
```bash
bash redo_all.sh
```

## Dependencies

- **Python 3**
- `pip install indic-transliteration` — the `indic_transliteration` package
- **csl-orig** sibling repo — SLP1 source files
