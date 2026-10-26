# BUGHUNT-FINDINGS — csl-devanagari — 26.10.2026

_Created: 26-10-2026 · Author: Dr. Mārcis Gasūns (DeepSeek Flash, `deepseek-flash`, via DSH) · Run: interactive day `/bughunt` (night driver blocked: `zai-coding-plan` cooled until 26.10 21:56, cursor not advanced)_

**Elapsed:** ~9 min (19:50 → 19:59 MSK). Budget 40 min; nothing failed three times.
**Scope:** the repo's CODE — `scripts/` (converters, guards, changelog tooling) and `.githooks/` — read-only static hunt plus live probes. Vendored dictionary text under `v02/` and `diff/` read, never written.

## Summary

| # | Sev | Finding | Where |
|---|-----|---------|-------|
| 1 | MEDIUM | Shared-main-tree commit guard is **inert on this machine**: it compares against a hardcoded Windows path only, so it never fires on macOS | [`.githooks/pre-commit:23-44`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/.githooks/pre-commit#L23-L44) |
| 2 | MEDIUM | Vendored pre-push stale-base checker is **1,854 lines / 7 weeks behind** its canonical copy; gate (1) runs the stale logic on every branch push | [`scripts/pre_push_stale_base_check.py`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/pre_push_stale_base_check.py), [`.githooks/pre-push:86,221`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/.githooks/pre-push#L86) |
| 3 | MEDIUM | `carry_changes_to_cslorig.sh` **blind-copies 40 converted dictionaries** into the canonical `csl-orig` clone — no diff gate, no freshness check — while `CLAUDE.md` forbids writing to csl-orig from here | [`scripts/carry_changes_to_cslorig.sh`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/carry_changes_to_cslorig.sh), [`CLAUDE.md:78-80`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/CLAUDE.md#L78-L80) |
| 4 | LOW | Metaline rebuild through a tag-keyed dict silently drops **duplicate tags** (forward direction only); recorded loss shape in `diff/mw.txt`, 0 live occurrences today | [`scripts/parseheadline.py:15-24`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/parseheadline.py#L15-L24), [`scripts/to_devanagari.py:53-65`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/to_devanagari.py#L53-L65) |
| 5 | LOW | `to_slp1.convert_partially_to_slp1` builds its split regex from **unescaped** start/end marks (the forward converter escapes them) | [`scripts/to_slp1.py:76-92`](https://github.com/sanskrit-lexicon/csl-devanagari/blob/main/scripts/to_slp1.py#L76-L92) |
| 6 | LOW | The repo's **14 converter unit tests never run in CI** — the only workflow gates are changelog lint + Dependabot auto-merge | [`.github/workflows/`](https://github.com/sanskrit-lexicon/csl-devanagari/tree/main/.github/workflows) |

**No HIGH finding.** The conversion path itself (the repo's product) is green: live round-trips are byte-identical on five dictionaries, including the accented (Vedic) scheme. All three MEDIUMs sit in the *guard* layer around the data, which is why they are worth fixing rather than merely noting: they create a false sense of protection around generated files that a proofreader trusts.

## 1. MEDIUM — main-tree commit guard is dead on macOS

`CANONICAL_MAIN_TREE` is hardcoded to the retired Windows checkout, and there is no `$HOME` twin and no environment override:

```bash
$ git -C ~/Documents/GitHub/csl-devanagari config core.hooksPath
.githooks
$ ls -l .githooks/pre-commit          # 0755 — the hook IS wired and executable
-rwxr-xr-x  1 mac  staff  2157 Aug 25 22:56 pre-commit
$ sed -n '23p' .githooks/pre-commit
CANONICAL_MAIN_TREE="C:/Users/user/Documents/GitHub/csl-devanagari"
$ cd ~/Documents/GitHub/csl-devanagari && bash .githooks/pre-commit; echo "exit=$?"
exit=0                                 # expected 1: this IS the shared main tree
```

`git rev-parse --show-toplevel` returns `/Users/mac/Documents/GitHub/csl-devanagari`, which can never equal the `c:/users/user/...` needle, so the block is unreachable on this box.

The estate already solved this exact shape twice: [Uprava's canonical hook](https://github.com/gasyoun/Uprava/blob/main/.githooks/pre-commit#L213-L237) added a crossbox `CANONICAL_MAIN_TREE_HOME="${HOME}/Documents/GitHub/Uprava"` twin plus an `UPRAVA_CANONICAL_TREE` override on 26-09-2026 after a bughunt, and [csl-observatory's copy](https://github.com/sanskrit-lexicon/csl-observatory/blob/main/.githooks/pre-commit#L40) defaults to `$HOME` directly. This repo's copy predates both.

**Impact:** commits made directly in the shared main tree are allowed here — the H214 / H685-close tree-intermix class the guard exists to prevent, where a concurrent session sweeps another session's staged changes into its own commit. It also reads as protection that is not there (§263/§333 "guard must emit" class).

**Class, not instance:** 21 checkouts under `~/Documents/GitHub` carry the same hardcoded-only shape (≈14 distinct repos: `SanskritLexicography`, `SanskritGrammar`, `SanskritKaraoke`, `SanskritSpellCheck`, `Systema-Sanscriticum`, `IndologyScholars`, `CommentaryStrategies`, `kosha`, `csl-atlas`, `csl-corrections`, `WhitneyRoots`, `SamudraManthanam`, `buhler-sanskrit-book`, `csl-devanagari`); only `csl-observatory` is portable. A one-repo fix cannot close it, so it is registered as a residual (below).

**Fix direction:** default to `$HOME/Documents/GitHub/csl-devanagari`, keep the Windows path as an alternative twin, honour `CANONICAL_MAIN_TREE`; pin with a test that runs the hook in a temp repo and expects exit 1 (fails on the pre-fix tree).

## 2. MEDIUM — the pre-push gate runs a stale vendored checker

`.githooks/pre-push:86` resolves `CHECKER="$TOPLEVEL/scripts/pre_push_stale_base_check.py"` and `:221` runs it for every push that is not a brand-new branch. The local copy is not the current rule set:

```bash
$ wc -l scripts/pre_push_stale_base_check.py ~/Documents/GitHub/Uprava/scripts/pre_push_stale_base_check.py
    2072 scripts/pre_push_stale_base_check.py
    3926 ~/Documents/GitHub/Uprava/scripts/pre_push_stale_base_check.py
$ git log -1 --format='%ad %s' -- scripts/pre_push_stale_base_check.py
Tue Sep 8 08:07:36 2026 +0300 ai-wip: add the pre-push silent-revert guard + CRLF-in-blob gate (H2280/H2289/H2301) (#63)
$ git -C ~/Documents/GitHub/Uprava log -1 --format='%ad %s' -- scripts/pre_push_stale_base_check.py
Mon Oct 26 19:16:38 2026 +0300 XZE+XZI: the guard and the drill suite read the run's own state, not the token/box's (#6057)
$ diff scripts/pre_push_stale_base_check.py ~/Documents/GitHub/Uprava/scripts/pre_push_stale_base_check.py | wc -l
2477
```

The canonical version has grown a rule/credit architecture this copy has never seen (`_credit_hunk_rewrite`, `_credit_mint_close`, `_exempt_expired_claim`, `_exempt_moved_not_lost`, `_forward_edit_ok`, `_git_timed_out`, …). Those exemptions exist because the un-exempted rule refused legitimate pushes — the documented failure mode that gets a guard switched off (the hook's own header recounts the demotion to WARN of 16-08-2026).

**Impact:** push-time refusals (or misses) computed by a seven-week-old rule set, on every branch push, including PR branches. A false refusal costs a session an `ALLOW_STALE_BASE_PUSH=1` escape — which is how the gate erodes.

**Fix direction:** re-sync the vendored copy from `Uprava/scripts/pre_push_stale_base_check.py` (or make the hook prefer a canonical path when present) and record the source sha in the file header so the next drift is detectable.

## 3. MEDIUM — the carry script overwrites canonical `csl-orig` with no gate

```bash
$ cat scripts/carry_changes_to_cslorig.sh
dicts=(wil yat gst ben mw72 lan lrv ap90 cae md mw shs mwe bor ae bur stc pwg gra pw ccs sch bop armh vcp skd abch acph acsj inm vei pui bhs acc krm ieg snp pe pgn mci)
echo "STARTED TAKING CORRECTIONS FROM CSL-DEVANAGARI TO CSL-ORIG";
for dict in ${dicts[@]}; do
  echo $dict
  python3 to_slp1.py $dict
  cp ../slp1/$dict.txt ../../csl-orig/v02/$dict/$dict.txt
done
```

It runs from `scripts/` with implicit cwd, has no `set -e`, no diff/`--dry-run`, no check that the local mirror is newer than csl-orig, and copies **all 40 dictionaries** in one pass. `CLAUDE.md:78-80` says the opposite: *"Do not hand-edit `v02/<dict>/<dict>.txt` … Do not commit or PR into csl-orig from here."*

The pipeline has not always been byte-lossless: the committed `diff/` tree still records non-zero round-trip differences for `skd` (1,862 B), `mw` (375 B) and `pwg` (222 B) — so any dict whose round trip is not clean would have those lines written into the canonical source, and a stale local mirror would silently revert newer upstream corrections (the silent-revert class gate (1) itself exists to stop).

**Impact:** one command can overwrite 40 files of canonical source in a sibling clone, unreviewably.

**Fix direction:** either retire the script (the monthly csl-orig correction queue is the sanctioned route) or make it refuse unless `ALLOW_CARRY=1`, `git -C ../../csl-orig status` is clean at the expected sha, and every affected `diff/<dict>.txt` is empty; print the plan before copying.

## 4. LOW — duplicate metaline tags are dropped by the dict-keyed rebuild

`parseheadline` returns `{tag: value}`; repeated tags overwrite, and `convert_metaline` then rebuilds the whole `<L>` line from that dict:

```python
result[splits[i]] = splits[i + 1]      # parseheadline.py:23 — last duplicate wins
devameta.append('<' + i + '>')          # to_devanagari.py:57 — one tag per key
```

`diff/mw.txt` (hunk `132461c132461`) records exactly this loss:

```
< <L>37448.1<pc>218,2<k1>ulapya<k2>ulapya^<e>2B          # round-trip output
> <L>37448.1<pc>218,2<k1>ulapya<k2>ulapya^<e>,ulapya/<e>2B  # csl-orig
```

Scanning today's `csl-orig/v02` gives **0 duplicate-tag metalines out of 1,506,456** — so this is latent, not live: upstream has since cleaned the one line, and the mirror file still carries the collapsed form. `to_slp1.convert_metaline` is immune (it transliterates the whole line and keeps tags), so only the forward direction can lose.

**Fix direction:** convert `k1`/`k2` in place instead of re-serialising through `parseheadline` (e.g. a tag-aware substitution), which removes the class rather than the line.

## 5. LOW — asymmetric regex escaping in the reverse converter

```python
reg = startMark + '.*?' + endMark                    # to_slp1.py:76 — raw
reg = re.escape(startMark) + '.*?' + re.escape(endMark)   # to_devanagari.py:97 — escaped
```

Today's marks (`<s>`/`</s>`, `{#`/`#}`) are regex-inert, so nothing is broken now; a mark containing `+`, `(`, `\` or `{` would silently mis-split or raise. `to_slp1.py:87-88` repeats the raw form in its `re.sub` anchor trimming.

**Fix direction:** mirror the forward converter (`re.escape` on both marks, and on the `^`/`$` anchors) before any new separator is introduced.

## 6. LOW — the converter unit tests have no CI home

`python -m unittest discover -s scripts -p "test*.py"` runs 14 tests. `.github/workflows/` contains only `changelog-lint.yml` (two changelog guards) and `dependabot-auto-merge.yml`; no workflow executes the tests, and no `Makefile`/pre-commit entry does either. A converter regression therefore lands with a green tick, and the first observer is a proofreader looking at wrong script.

**Fix direction:** add a `unit-tests` job (`setup-python` + `python -m unittest discover -s scripts -p "test*.py"` + `py_compile`) to `changelog-lint.yml` or its own workflow.

## What verified green (live, this run)

- `python3 -m unittest discover -s scripts -p "test*.py"` → **Ran 14 tests … OK**.
- `python3 -m py_compile scripts/*.py` → rc 0, no output.
- Live round-trip (`bash redo.sh <dict>` in a scratch copy with a real csl-orig sibling) → **byte-identical** for `acsj` (50 KB), `acph` (63 KB), `snp` (304 KB), `abch` (581 KB) and `gra` (6.6 MB — the accented `slp1_accented` path), 1–2 s each.
- `python3 scripts/eol_census.py --repo . --ref HEAD --changed-since origin/main` → "no paths changed", rc 0.
- `python3 scripts/pre_push_stale_base_check.py HEAD origin/main` → rc 0 on a clean tree.
- CI: **Changelog lint — success** on `6321ac2`; **Dependabot auto-merge — success** on the two bumped actions (`47e92ee`, `32eeef3`).

## Residual actions (not fixed here — a hunt reports; the fix lane executes)

1. **Main-tree guard sweep** — restore the crossbox detection in this repo *and* the ~13 siblings carrying the same dead shape (finding 1, class).
2. **Re-sync the vendored pre-push checker** from `Uprava/scripts/pre_push_stale_base_check.py` (finding 2).
3. **Decide `carry_changes_to_cslorig.sh`**: retire it or gate it (`ALLOW_CARRY`, clean/fresh csl-orig, empty diffs) (finding 3).
4. **Converter hardening** — in-place `k1`/`k2` conversion, `re.escape` in `to_slp1`, plus a CI job running the 14 tests (findings 4–6).

Per the skill's fix-lane contract these are minted as GTD `@DO` rows rather than silently left in this file.

_Dr. Mārcis Gasūns_
