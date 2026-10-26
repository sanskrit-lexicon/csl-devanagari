_Created: 03-07-2026 · Last updated: 26-10-2026_

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Bug hunt [BUGHUNT-FINDINGS-csl-devanagari-26.10.2026.md](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/BUGHUNT-FINDINGS-csl-devanagari-26.10.2026.md): no HIGH; 3 MEDIUM + 3 LOW — the shared-main-tree commit guard is inert on macOS (hardcoded Windows path only), the vendored pre-push stale-base checker is 1,854 lines behind its canonical copy, and `carry_changes_to_cslorig.sh` overwrites canonical `csl-orig` with no diff/freshness gate. Converter round-trip re-verified byte-identical on 5 dictionaries (`acsj`, `acph`, `snp`, `abch`, `gra`).
- New `Unit tests` workflow runs the converter suite on every push/PR (no CI job ran the 14 tests before).

### Fixed

- Shared-main-tree commit guard now also matches the `$HOME` canonical checkout (`CANONICAL_MAIN_TREE` / `CANONICAL_MAIN_TREE_HOME` overridable): until now only the retired `C:/Users/user/...` path was compared, so on every macOS/Linux clone the guard passed silently (bughunt finding 1, pinned by `scripts/test_pre_commit_guard.py`).
- Metaline `<k1>`/`<k2>` are converted in place instead of being reserialised through the tag-keyed `parseheadline` dict, so a metaline that repeats a tag no longer loses all but the last value, and trailing whitespace survives (bughunt finding 4; identical output on all 1,506,456 current metalines except the 22 lines whose trailing blank the old `.strip()` deleted).
- `to_slp1.convert_partially_to_slp1` regex-escapes its start/end marks like the forward converter does (bughunt finding 5).
- Pre-push gate (1) runs the canonical stale-base checker again: `scripts/pre_push_stale_base_check.py` re-vendored from Uprava `1c8bd84` (2,072 → 3,983 lines) together with its `_msk.py` helper; the local copy was seven weeks and the whole rule/credit exemption layer behind (bughunt finding 2).
- `scripts/carry_changes_to_cslorig.sh` refuses by default: needs `ALLOW_CARRY=1`, a clean `csl-orig` at `origin/main`, an empty round-trip diff per dictionary, and a mirror not older than the source; prints its plan and supports `--dry-run` (bughunt finding 3). Pinned by `scripts/test_carry_gate.py`.

## [0.1.2] - 2026-08-30
### Changed

- [CLAUDE.md](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/CLAUDE.md): dated header (`_Created: 15-05-2026 · Last updated: 20-08-2026_`), How to run (`redo.sh` / unit tests), and what-not-to-touch for generated `v02/` (H3041).

## [0.1.1] - 2026-08-04

### Fixed

- **`scripts/corrections_issue_92/Filling.the.missed.places.txt` was stored with CRLF line
  endings while `.gitattributes` mandates `text eol=lf`** — the one file in this repo whose
  blob contradicted the LF policy added in [#50](https://github.com/sanskrit-lexicon/csl-devanagari/pull/50).
  Adding `.gitattributes` sets the policy for *future* writes but does not rewrite blobs
  already committed, so this file was left behind by that change. The effect is not
  cosmetic: git's clean filter makes every line of such a blob differ against `HEAD`
  **permanently**, and `git checkout` cannot repair it because the defect lives in the
  stored object rather than the working file. Worse, the damage is normally **invisible** —
  git's stat cache skips re-hashing a file whose mtime and size are unchanged, so the
  phantom modification only surfaces once something touches the file, at which point a
  routine tidy-up can read it as uncommitted work and discard it. Fixed with
  `git add --renormalize`; `git diff --cached --ignore-cr-at-eol` is **empty**, i.e. the
  945 changed lines are line-terminator-only and the content is provably identical.
  Detect the class anywhere with
  `git ls-files --eol | grep -E 'i/(crlf|mixed)' | grep 'eol=lf'` — a clean `git status` is
  not evidence of absence.

## [0.1.0] - 2026-06-30

### Added

- Initial release of csl-devanagari
- Devanagari transcoding and text processing utilities
- Support for SLP1 and Devanagari script conversion
- Accent-aware processing for Vedic dictionaries (acc, gra)
- Plain SLP1 fallback for non-Vedic dictionaries
- License information (dual-license: CC-BY-SA-4.0 for data, GPL-3.0 for source code)
- Dependabot configuration for automated dependency updates

### Changed

- XML tag preservation in Devanagari processing
- Improved handling of Devanagari formatting in dictionary entries

### Fixed

- Devanagari XML tag handling for dictionary compatibility
- Code license link correction (RH1 dual-license approved 2026-06-18)

### Deprecated

- None

### Removed

- None

### Security

- None

[0.1.0]: https://github.com/sanskrit-lexicon/csl-devanagari/releases/tag/v0.1.0

_Dr. Mārcis Gasūns_
