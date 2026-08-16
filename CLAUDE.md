# CLAUDE.md

_Created: 15-05-2026 · Last updated: 16-08-2026_

`csl-devanagari` is a **converter** that mirrors every CDSL dictionary source
from SLP1 ([`csl-orig`](https://github.com/sanskrit-lexicon/csl-orig)) into
Devanagari so a proofreader can read the native script instead of mentally
decoding SLP1. It is not a place to correct dictionary text.

Org conventions live in [`../CLAUDE.md`](https://github.com/gasyoun/github-spine/blob/main/CLAUDE.md).
Before encodings or corpus data, read the
[Sanskrit context primer](https://github.com/gasyoun/github-spine/blob/main/SANSKRIT_CONTEXT_PRIMER.md).

## How to run

One dictionary (needs `indic-transliteration`):

```bash
cd scripts
bash redo.sh mw
```

All dictionaries:

```bash
cd scripts
bash redo_all.sh
```

Pipeline (do not invent a second one):

1. [`scripts/to_devanagari.py`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/to_devanagari.py)
   writes `v02/<dict>/<dict>.txt` (Devanagari mirror, one line per source line).
2. [`scripts/to_slp1.py`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/to_slp1.py)
   round-trips that file back to SLP1 under untracked `slp1/<dict>.txt`.
3. Compare `slp1/<dict>.txt` with
   [`csl-orig/v02/<dict>/<dict>.txt`](https://github.com/sanskrit-lexicon/csl-orig/blob/main/v02/mw/mw.txt).
   Differences land in `diff/<dict>.txt`. A clean round-trip is the success
   criterion.

Example committed output: `v02/mw/mw.txt` is 880,516 lines.

CI is Dependabot auto-merge only. There is no test suite; the gate is a clean
round-trip.

## Do not touch

- Do **not** hand-edit `v02/<dict>/<dict>.txt` — regenerate from `csl-orig`
  via `redo.sh`.
- Do **not** commit `slp1/` (intermediate comparison files).
- Do **not** correct dictionary wording here. Corrections belong in
  [`csl-corrections`](https://github.com/sanskrit-lexicon/csl-corrections)
  and ship to `csl-orig` via `/cologne-correction-queue` +
  `/cologne-batch-pr`.
- **Never commit or push to `csl-orig`.**
- `sanskrit-util iast_to_devanagari` is broken — this repo's `to_devanagari.py`
  is the converter; do not replace it with the broken helper.

Issues use the Cologne tooling taxonomy — see
[`/cologne-issue-runbook`](https://github.com/gasyoun/claude-config/blob/main/commands/cologne-issue-runbook.md).
Do not recopy type/severity/milestone tables into this file.

Danger facts:
[Uprava DANGER_FACTS.md](https://github.com/gasyoun/Uprava/blob/main/DANGER_FACTS.md)
and the generated block of
[AGENTS.md](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/AGENTS.md).

_Dr. Mārcis Gasūns_
