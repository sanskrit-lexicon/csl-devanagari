# csl-devanagari

_Created: 02-09-2021 · Last updated: 11-07-2026_

## Why this repo exists

The canonical CDSL source text in [csl-orig](https://github.com/sanskrit-lexicon/csl-orig)
is stored in SLP1 transliteration — compact and unambiguous for machine
processing, but hard for a human proofreader to sanity-check at a glance.
**csl-devanagari mirrors every dictionary's source text into Devanagari script**,
so an editor can visually confirm a correction reads correctly in the native
script, without needing to mentally decode SLP1.

## How it works

1. This repository generates files in which Devanagari script is used instead of SLP1 (as in csl-orig).
2. The data from the csl-orig repository is processed via [to_devanagari.py](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/to_devanagari.py) and stored in a `v02/<dict>/<dict>.txt` file in this repository — e.g. [v02/mw/mw.txt](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/v02/mw/mw.txt).
3. To ensure the conversion is reversible, [to_slp1.py](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/to_slp1.py) converts the Devanagari output back to SLP1.
4. After one round-trip through `to_devanagari.py` and `to_slp1.py`, the result is stored in a `slp1/<dict>.txt` file.
5. `slp1/<dict>.txt` is compared with the original [csl-orig/v02/<dict>/<dict>.txt](https://github.com/sanskrit-lexicon/csl-orig/blob/master/v02/mw/mw.txt).
6. The `slp1/` folder is not tracked in this repository — it only holds intermediate files for comparison.
7. If any differences are found, they're written to a `diff/<dict>.txt` file — e.g. [diff/mw.txt](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/diff/mw.txt).
8. The ideal outcome is that there is no difference between the two files — a clean round-trip proves the Devanagari mirror is faithful to the SLP1 source.

## Usage example

Regenerating the Devanagari mirror for one dictionary:

```bash
cd scripts
bash redo.sh mw
```

This is the real, documented invocation — not re-run live here since it needs
the `indic-transliteration` package and rewrites already-committed tracked
files. What it produces, verified by directly reading the already-committed
output rather than re-running the script:

```
$ wc -l v02/mw/mw.txt
880516 v02/mw/mw.txt
```

`v02/mw/mw.txt` (880,516 lines) is the Devanagari mirror of Monier-Williams'
dictionary, one line per line of the SLP1 source — a proofreader can open this
file directly and read real Devanagari script instead of SLP1 codes.

To regenerate all dictionaries at once:

```bash
cd scripts
bash redo_all.sh
```

## Dependencies

[indic-transliteration](https://pypi.org/project/indic-transliteration/)

---

_Dr. Mārcis Gasūns_
