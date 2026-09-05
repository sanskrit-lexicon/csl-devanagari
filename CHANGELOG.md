_Created: 03-07-2026 · Last updated: 05-09-2026_

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
