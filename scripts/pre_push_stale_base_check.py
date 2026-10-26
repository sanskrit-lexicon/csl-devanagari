"""Refuse a push that deletes lines another session added upstream moments ago —
the silent-revert class of Uprava#1516.

WHY THE OBVIOUS DESIGN DOES NOT WORK
------------------------------------
The guard proposed on #1516 was "refuse a push whose tree contains a path modified
upstream after the local HEAD's merge-base". Implemented and measured 04-08-2026, it
is **redundant with git itself**: ``merge-base != remote_tip`` is the definition of a
non-fast-forward push, which git already rejects; and a fast-forward push always has
``merge-base == remote_tip``, so the check is vacuous exactly when it is needed. Both
#1516 incidents were clean fast-forwards. A ref-level test cannot see them.

What both incidents *do* share is visible at the line level: the push **deletes lines
that an upstream commit added very recently**, because the author's file content was a
pre-image copy — a stale index (29-07) or a stale checkout (04-08). Nobody edits a line
that landed ninety seconds ago on purpose without knowing it; when it happens it is
almost always a copy written before that line existed.

THE CHECK
---------
For each path the push changes, take the lines it removes relative to the remote tip,
``git blame`` them at the remote tip, and flag any whose introducing commit is

* **recent** — within ``--recent-days`` (default 3), and
* **not part of this push** — so rewriting your own just-pushed line is fine.

That pair is the whole rule. Old lines are ordinary edits. Your own lines are yours.
Someone else's line from an hour ago, deleted by a commit that never mentions it, is
the defect.

FAST PATH: THE MINT CLAIM COMMIT (GTD WC7, H7216 residual, 22-10-2026)
------------------------------------------------------------------------
One commit shape is provably outside this class, and it is the shape that pays
this guard most often: the MINT CLAIM. `tools/mint_push.py` builds it with git
plumbing as ONE commit whose parent IS the freshly fetched remote tip, adding a
`handoffs/H###-*.md` stub and rewriting only the registry's DERIVED lines
(the Next-free-ID marker, `**Counts:**`, the 🟡 header count; for a child, one
appended epic bullet). There is no older base to be a pre-image of, every other
path is byte-identical to the tip, and every deletion is a line the mint itself
computes. `mint_claim_proof` checks exactly that (parent == tip, the three mint
subjects, the changed-path set, derived-only deletions) and `main` exits 0 with
a journaled ``mint-claim-exempt`` verdict when it holds. ANY doubt — another
path, an existing body rewritten, a non-derived deletion, a non-mint subject —
declines the proof and runs the full scan unchanged. The measured cost of the
sweep on the mac was 338 s against a claim push's 900 s ceiling (H7216), i.e.
the verdict was both structurally unanswerable and expensive enough to consume
the push. ``--no-mint-exempt`` forces the old path.

BLOCKS BY DEFAULT — DEMOTED, THEN RE-PROMOTED
---------------------------------------------
**Current behaviour: this hook REFUSES the push.** Override per-push with
``ALLOW_STALE_BASE_PUSH=1``. ``STALE_BASE_PUSH_STRICT=1`` is now the default and is
accepted as a no-op.

Re-promoted 16-08-2026 on MG's ruling, reversing the demotion described below. The
history is kept because it is the argument against this decision, and a future session
weighing another flip should read it rather than rediscover it:

This started as a **blocking** hook, which is what #1516 asked for. It was demoted to a
warning on the day it shipped, on measured evidence: while landing its own handoff it
refused three pushes, all of them legitimate, all of them this repo's standard workflow —

1. resolving a ``CHANGELOG`` version collision by renumbering a concurrent session's
   section (their rows deleted at the old line numbers, re-added lower);
2. filling a ``mint_handoff.py`` stub that had been pushed to ``main`` seconds earlier;
3. ``handoff_close.py`` archiving a handoff, which repoints ``handoffs/X`` links to
   ``handoffs/archive/X`` **inside rows added minutes ago**.

**All three are now exempted below**, plus a fourth found by measurement afterwards.
(3) was the open cost of re-promoting this to a blocker and was closed the same day
(MG 16-08-2026) rather than left to bite: see ``archive_normalized``. It normalizes the
``handoffs/X.md`` → ``handoffs/archive/X.md`` repoint on the REMOVED line only, so an
archive pass reads as the move it is. A push that repoints a link *and* drops anything
else on the same line still blocks — the exemption is the rewrite, not the tool.

(4) **Registry bookkeeping**, exempted 17-08-2026 — see ``is_registry_bookkeeping``.
``registry_check.apply_fix`` regenerates four derived lines on every close, so two
closes inside the recency window always look like each other's revert; FINDINGS §435
measured that blocking BOTH sanctioned close paths under ordinary push traffic.

(5) **Surgical forward modification of a minutes-old line**, exempted 22-08-2026 after
the retier of five handoff rows hit it twice in one hour: rewriting someone's fresh row
IN PLACE (token swap inside an otherwise byte-identical line) is not a deletion — the
line's information survives. Detection is two-gated so the H1516 class cannot dress up
as this: (a) the replacement must be a NEAR match (``difflib`` ratio ≥ ``NEAR_RATIO``)
of the removed line among the pushed survivors, and (b) that exact replacement text
must NOT already exist in the file as of the blamed commit's parent. Gate (b) is the
load-bearing half: a stale pre-image reinstall also near-matches (it differs from the
fresh line by exactly the upstream edit), but its text demonstrably existed *before*
their commit — which is the definition of installing old work over new, and still
blocks. A forward edit produces content history has never seen; a revert replays
content it has. See ``best_near_match`` / ``pre_image_lines`` and test cases 14/14b.

(5) **Generated single-writer artifacts**, exempted 18-08-2026 — see
``is_generated_single_writer``. A ``--land`` caller replaces a whole file it is the
ONLY writer of (a dashboard snapshot, a stats JSON) every run, and some of those
files churn dozens of lines a day — every such push trips this guard by
construction, not by accident. Measured 18-08-2026 (H3073): four consecutive
``tools/refresh_dashboards_daily.py --land`` runs were refused this way and
misreported as "origin kept moving", when the scheduled task had in fact been
red for three days.

(7) **Same-session mint→close and claim→close**, exempted 24-08-2026 and
26-08-2026 respectively — see
``is_same_session_mint_close`` (FINDINGS §457). Closing a handoff minted in the
same session rewrites the very registry row / body lines the mint commit added
minutes earlier, so blame hits a fresh non-pushed commit and EVERY such close
refused — measured on H3060 (cleared with ``ALLOW_STALE_BASE_PUSH=1``, landed
as ``cb0acd668``). Three gates keep the H1516 stale-pre-image class out: the
blamer subject must BE a mint claim, the removed line must name that minted
H###, and this push must visibly work on the same H### elsewhere (path basename
or added line). A stale checkout reverting someone's just-minted stub deletes
the row without touching anything else named H#### and stays blocked.
Claim→RELEASE is the third pairing, exempted 15-09-2026 — see
``is_claim_release_inverse``: a ``handoff.py release H#### --commit`` on a
banner-less body changes only the queue row, so gate 3 above can never hold for it
(measured on H4527: 2 runs × 8 retries, all refused).

(8) **The FINDINGS next-number marker, bumped forward**, exempted 03-09-2026 — see
``findings_marker_bump`` (FINDINGS §695). ``FINDINGS.md`` ends with the single line
``§N takes the next number.``; every append CONSUMES that number and rewrites the
line, so every append deletes a line another session added minutes ago and every
append refuses — the same "routine work needs the override" shape §659 measured on
release pushes, and an override reflex trained on routine work is what §641/§643
warn about. One-directional and readable from the pushed content alone (the §437
bar): exempt only when the same push LEAVES a marker whose number is strictly
greater. A stale checkout reinstalling a pre-image marker moves the number backwards
or leaves it equal and still blocks — exactly the H1516 shape. The match is anchored
and whole-line, so nothing else on that line, and no other line in the file, gains
anything. See test cases 23/23b. §659's changelog-fragment twin stays OPEN.
That last sentence is superseded the same day: the twin shipped as class (9)
below — kept verbatim rather than rewritten so this guard's own history is
readable, and so the line survives its own recency check.

(9) **changelog_queue fragments consumed by a release cut**, exempted 03-09-2026 —
see ``promoted_queue_lines`` (FINDINGS §659, tightened by H3886). A cut
copies each ``changelog_queue/*.md`` fragment's bullet into ``CHANGELOG.md`` and
DELETES the fragment in the same commit, so every fragment another session added in
the last ``--recent-days`` is deleted by construction: measured 03-09-2026 on the
``v0.195.419`` cut, 35 lines across 33 files, and the same on every cut before it.
The text is not lost, it MOVED across paths, so the fix is a credit, not an override.
Same-push gated exactly like ``REGISTRY_RELOCATION_PAIR``: only the lines THIS PUSH ADDS
to ``CHANGELOG.md`` count, so a stale checkout that merely drops someone's fresh fragment
is credited with nothing and still blocks.

The credit is an EQUALITY test, and it is deliberately kept OUT of ``survivors`` (H3886,
07-09-2026). ``changelog_queue_consume.flush_bullets`` copies each non-blank fragment
line ``ln.rstrip()`` BYTE-IDENTICALLY into the release section, so a real cut always
produces exact text and needs no slack. Routing the changelog additions through the
survivor set instead — the shape shipped on 03-09 — also fed them to class 5's
``best_near_match``, and a fresh fragment's own BIRTH commit is its blamer, so gate (b)
is satisfied by construction (``_creation_sha`` -> empty pre-image): a push that DELETED
a fresh fragment while adding a REWORDED bullet was silently exempted. That is the H1516
class wearing a release cut's clothes, in the file class that churns hardest at release
time — the last place to widen a near-match surface. The credit is therefore taken like
§450's relocation: before blame, never as a survivor. Test cases 24 (promoted -> allowed),
24b (dropped -> blocks), 24c (reworded -> blocks).

(10) **Same-lane close-prep lines of the SAME handoff file**, downgraded to a loud
WARNING (not a block) 07-09-2026 — see ``is_same_lane_close_prep`` (GTD 0x, the
H4265 close incident). A drain session claimed H4265 (``exec-claim: H4265 …``),
filled its acceptance checkboxes in commit 8b5fbda (subject: "handoffs: … fanout
fills — H4260 umbrella + H4261–H4265 S1–S5 …"), and was then refused EIGHT times
when its own close push rewrote those same checkbox lines: the §457 exemption's
gate 1 only recognises mint/claim SUBJECTS, and 8b5fbda is a fill commit, so
every close of a handoff filled minutes earlier by its own lane blocked and
needed an explicit per-push override (MG 06-09-2026: «Флип разрешить»). The
class is deliberately NOT a silent exemption: lines whose
blaming commit's subject names the SAME H### as the changed ``handoffs/`` file
itself (marker provenance — mint, exec-claim, fill and close subjects all carry
their H###s), where THIS PUSH visibly works on that same H###, are reported as
``stale-base guard: WARNING — push ALLOWED`` naming every line, and the push
proceeds. Honest limit, accepted by the ruling: a stale checkout that reverts
ANOTHER session's work inside that one handoff file also warns instead of
blocking — the blast radius is bounded to the one file whose name carries the
H###, the warning stays in stderr for the human, and registry/README/GTD lines
(outside ``handoffs/H####-*.md`` basenames) keep blocking. A subject that names
NO handoff id still blocks outright (case 20b).

The list above was wrong when written, which is the durable lesson: it claimed three
classes with one outstanding, and (4) was already live. Enumerate a guard's false
positives by measurement before promoting it, not from its own docstring. The
``ours`` set still covers only commits inside the CURRENT push: rewriting your own
lines from an EARLIER push blocks everywhere except the one file-shape class (10)
downgraded to a warning. (A general self-lineage exemption — adder-is-ancestor —
was considered for §457 and REJECTED: the 04-08 incident's stale-checkout shape
contains the rival commit as an ancestor while reinstalling pre-image content, so
ancestry alone cannot separate the two; the mint-subject + same-H### +
this-push-names-it gates above are the narrower cut that can.)

The demotion argument was that three false-positive classes against two true incidents is
the wrong ratio for a blocker, since the standing response to a hook that refuses good
pushes is to switch it off, and then it protects nothing. The counter-argument, which won:
a silent revert of another session's work is not recoverable by the person it happens to —
they discover it days later, if ever — while a false positive costs one extra environment
variable at the moment of the push, by someone who can see exactly what is being reverted::

    ALLOW_STALE_BASE_PUSH=1  git push ...   # per-push override (the only one needed)
    STALE_BASE_PUSH_STRICT=1 git push ...   # accepted no-op; blocking is now the default

A deliberate revert of fresh upstream work used to be flagged too — correctly for the
stale-tree accident, but MG 04-10-2026 («гард запрещает удаление моей же строки —
поменяйте логику») measured the cost on the recurring estate churn: infra files land
(queue entries, close stubs, scratch notes) and get deleted wholesale hours later, and
refusing that teaches authors to reach for the override. Whole-file removals are now
exempt when the file's BIRTH commit is an ancestor of the pushed head: a tree that saw
the file born deletes it as a visible choice, and the stale-preimage accident cannot
produce the shape — a stale tree never saw the birth, so the birth commit is not an
ancestor and the refusal stands. CHANGELOG_QUEUE fragments are excluded: their
deletion is the §659 promotion contract (a fragment drops only once its bullet is
released into CHANGELOG.md), a policy gate rather than a staleness check. Line-level
rewrites inside files that survive keep every protection below, override and all.

LIMITS (measured, not assumed)
--------------------------
* Blame is per-path and costs ONE blame per changed file (batched: a single
  ``git blame --line-porcelain`` per path feeds every removed line); on a push
  touching hundreds of files this is still not free, so ``--max-paths``
  (default 40) bounds it and the script says so rather than silently sampling.
* **Work bounds (FINDINGS §543, §605)** — a line-level guard with unbounded work
  does not refuse, it HANGS, and a push killed mid-guard by the caller's timeout
  reports as silence, not as a verdict. Measured twice: a derived-views regen
  (§543, >300 s with no output) and a wholesale derived-JSON rewrite
  (§605, −28 488/+8 843 lines, >420 s standalone, push dead by timeout). Two
  bounds now cap the work per path: ``--max-blame-lines`` (default 2000) on the
  removed-line count, and ``--max-near-pairs`` (default 300 000) on the
  near-match comparison budget (removed × survivors, consumed by class 5's
  difflib work). Past either bound the path is NOT silently skipped — it gets a
  greppable ``STALE_BASE_CIRCUIT_BREAK`` verdict naming the path and the bound,
  and the check degrades to ref-level verification: a clean fast-forward
  (``merge-base --is-ancestor``) is allowed with that loud note; the same bulk
  rewrite on a forced/non-fast-forward update is refused fail-closed, because a
  forced push is exactly where git's own ref-level protection is switched off.
  A guard that degrades into an infinite computation converts every push into a
  silent kill, which is strictly worse than a visible skip (§605: a false
  refusal is visible; a hang teaches authors to bypass).
* Pure additions are never flagged; only deletions and rewrites of recent upstream lines.
* Whitespace-only differences are ignored (``-w``), so a CRLF renormalisation sweep does
  not trip it — the §299/§305 class is a different problem with a different fix.
* A push that reverts a line older than the window is not caught. That is the accepted
  cost of keeping false positives near zero.

A RETRY LOOP CANNOT WIN AGAINST THIS REFUSAL (H3134, FINDINGS §493)
---------------------------------------------------------------------
This is a LOCAL pre-push hook refusal, not a moved remote tip: a `fetch → rebase →
push` loop rebases cleanly every time and this script refuses every time, because
nothing about the refusal depends on where ``origin/main`` sits — the rebase never
changes the deleted lines this diff would drop. `report()` therefore prints a
stable, greppable marker (``STALE_BASE_GUARD_REFUSAL``) and names the override on
its first line, not twenty lines into the banner, so a wrapper can stop on the
FIRST refusal instead of burning its whole retry budget on a fixed answer (§493
measured a hand-written loop give up after 15 identical attempts).

The cheap discriminator for a wrapper that cannot inspect stderr: ``git merge-base
--is-ancestor origin/main HEAD`` is **true** for this LOCAL refusal (the local
branch already contains the remote tip — nothing to rebase onto) and **false**
for a genuine non-fast-forward (the remote moved and the local branch does not
yet contain it). ``handoff_claims.commit_texts_to_origin`` (FINDINGS §449) takes
the more precise route and reads this hook's own ``PUSH BLOCKED`` banner from the
push's stderr instead — it deliberately keeps retrying even on a confirmed guard
block, because its transforms are re-applied to freshly fetched content each pass
and a concurrent commit can change which exemption below applies; that is a
different, already-correct design and this handoff does not touch it.

NON-FAST-FORWARD IS NOT THIS GUARD'S BUSINESS (H4342, 08-09-2026)
------------------------------------------------------------------
The paragraph above is kept verbatim because its central claim is WRONG, and the
wrongness is the whole of H4342. It reads the two states as mutually exclusive —
LOCAL refusal *or* non-fast-forward. They are not. ``commit_texts_to_origin``
pins a base, builds a ``commit-tree`` on it, and pushes that detached sha; when a
concurrent session lands in that window the push is a non-fast-forward AND this
guard sees every line the winner just added as a line the push deletes. It then
printed ``STALE_BASE_GUARD_REFUSAL`` — "Retrying cannot clear it" — for the one
case where retrying is precisely what clears it, and the sticky
``diag["guard_blocked"]`` made the caller close with "This is NOT origin/main
moving". It was.

Measured 08-09-2026: the same H4339 close commit refused with 25 phantom
deletions in 2 paths when its base was one commit stale, and passed clean when
rebuilt on the tip — same transforms, same content. Against 3222 stale-base
refusals logged in ``logs/guard_firings.jsonl`` over ten days (241 episodes; the
worst single episode 383 refusals across 2 h 09 m) and 290 ``ALLOW_STALE_BASE_PUSH``
escapes, this shape is the reason the override reflex §641/§643 warn about ever
had routine work to train on.

``main()`` therefore asks ``push_is_fast_forward()`` before judging: a
non-fast-forward push gets ``STALE_BASE_NON_FF_SKIP``, its phantom lines named
in stderr, and exit 0 — git refuses the push itself, and on main/master a FORCED
one is refused fail-closed by ``scripts/pre_push_main_line_gate.py`` check 2
(rewind/rewrite, escape ``ALLOW_MAIN_LINE_REWIND=1``). Detection power lost for
the #1516 class: none — it is fast-forward-shaped by definition, as the opening
of this docstring says. Cases 26/26b pin both halves.

TWO EXEMPTIONS CONSIDERED FOR THIS HANDOFF, BOTH NOW ADDED
-----------------------------------------------------------
Both were checked against the same bar: recognisable from the pushed content
alone, with no guess about intent (§437's lesson — a heuristic exemption papers
over one false-positive class and leaves the others louder).

* **GTD active-state migration (H2697) — added, see ``cross_file_survivors``.**
  ``gtd_active_state.compact_card`` truncates an over-cap card to a status line
  in ``GTD_NEXT_ACTIONS.md`` while writing its FULL original text verbatim into
  ``GTD_ARCHIVE.md``, in the same commit. That satisfies the structural bar
  exactly: the deleted content reappears verbatim in the archive half of the
  SAME push. Scoped to this one declared file pair — not "any file elsewhere in
  the push", which would let the survivors check quietly absorb an unrelated
  file's coincidental text match.
* **Registry row relocation (FINDINGS §450, §530) — added once the shape became
  verbatim-checkable; see ``cross_file_survivors`` + ``relocated_registry_rows``.**
  This block originally said NOT added, on purpose: a ``handoff_close.py
  --commit`` move rewrites the row's status/date/tier cells, so no whole-line
  survivor exists, and matching on the bare ``H###`` id alone would exempt ANY
  deletion of that row whether or not the archive gained a real one. §530 then
  measured the guard refusing an H3167 close IDENTICALLY across two independent
  fresh checkouts — and the interim difflib near-match escape (ratio ≥ 0.85,
  landed earlier on 24-08-2026) misses real closes anyway, because the archived
  row APPENDS a long close summary that blows past the length slack. The
  checkable shape was there all along, one level down: treat
  ``handoffs/README.md ↔ handoffs/REGISTRY_ARCHIVE.md`` as ONE logical document.
  A row deleted from README.md counts as surviving ONLY when the SAME push adds
  to REGISTRY_ARCHIVE.md a row naming the SAME H### id AND carrying a contiguous
  verbatim fragment (≥ ``VERBATIM_FRAGMENT_MIN`` chars) of the moved row —
  recognisable from the pushed content alone, no intent guessed, scoped strictly
  to this one declared pair. One-directional: removing rows FROM the archive
  over live ones is still the pre-image shape and still blocks.

HUB-ROW REWRITES ARE FORWARD EDITS, NOT LOSSES (H4437, 09-09-2026)
------------------------------------------------------------------
One-line-per-subject hub tables make EVERY in-place row update a whole-line
rewrite, and a rewrite diffs as ``- old`` / ``+ new`` — indistinguishable from
a deletion. Measured: GTD row 0ae was rewritten 39 minutes after the commit
that minted it landed; the guard refused the rewrite as a revert, class 5's
near match correctly declined (the instruction text changed wholesale), and
§720's own advice ("insert a new line instead") does not exist for keyed
tables. ``ROW_REWRITE_PATHS`` declares the hub tables; a removed row is
credited when the SAME push re-adds a line with the same row token, the
identity survives (H### subset or a ≥40-char verbatim fragment), and the
replacement text is ABSENT from the blaming commit's pre-image — that last
gate is the #1516 load-bearing half, because a stale pre-image reinstall
re-adds text that existed before their edit and still blocks. Credits print
under ``STALE_BASE_ROW_REWRITE_ALLOWED`` and never pass silently.

LOCALITY IS THE PAIRING RULE THE THRESHOLDS WERE APPROXIMATING (H4498, 10-09-2026)
----------------------------------------------------------------------------------
MG, 10-09-2026: "remove this stale base hook or improve, it breakes my work now
many times a day". Measured before touching anything, from this repo's own
``logs/guard_firings.jsonl`` (ten days to 10-09): 4286 stale-base verdicts, 3695
refusals in 82 time-clustered blocking episodes (~8 a day, ~44 refusal firings
per episode), 332 ``ALLOW_STALE_BASE_PUSH`` escapes. 41 % of episodes end in an
override and 43 % end with the session giving up; no confirmed catch of a real
#1516 loss is recorded anywhere since the guard shipped. That is the §735 class
billing daily.

The first attempt at this fix was WRONG, and its refutation is the finding worth
keeping. It read gate (b) — "the replacement text is ABSENT from the blaming
commit's pre-image" — as the ONLY load-bearing property here (a stale tree can
reproduce old bytes; it cannot invent new ones) and dismissed ``NEAR_RATIO``,
H4437's row token and H4455's 40-char fragment as mere pairing heuristics. It
therefore paired by locality alone: the removed line's own hunk, plus gate (b).
The suite refuted that in **14 checks across 8 fences** (9b, 11b, 12b, 15b/15c,
16b, 21b, 27b, 28d/28e). The reason is exact: a destructive in-place OVERWRITE
also writes text absent from the pre-image, so gate (b) cannot separate "edited
their line" from "wrote over their line". **Identity is what separates them** —
those thresholds are not epicycles, they are the identity test.

What IS wrong with the shipped thresholds is that both are ABSOLUTE while the
identity they measure is relative. H4490's ``-def render(manuals, repo_root):``
-> ``+def render(manuals, repo_root, carried=None):`` keeps 29 of its 30
characters verbatim — 97 % of the line — and is refused because 29 < 40, while
class 5's ratio lands at 0.816 < 0.85. A short line has no way to carry a long
fragment, so it is judged by a bar it cannot reach.

CLASS 11 therefore keeps identity and makes it PROPORTIONAL, adding locality as
a second, independent condition. Both must hold: the replacement keeps a
contiguous verbatim run of at least ``SHORT_REWRITE_MIN_SHARE`` of the removed
line (never fewer than ``SHORT_REWRITE_MIN_RUN`` characters), AND it is one of
the lines this push adds inside the removed line's own diff hunk, with EVERY
line that hunk adds passing gate (b). A long hub row still has to carry a long
fragment, so 28d/28e keep blocking; a pure deletion has no hunk adds (case 31b);
a fresh line beside a reinstalled pre-image line cannot launder it (case 31c).
Class 11 is asked LAST, after class 5, so every existing pass keeps its banner.

Residual risk, stated plainly: a stale worker that itself EDITS a line it never
saw, while preserving half of it verbatim, is credited. That risk is not new —
classes 5, H4437 and H4455 all accept it already — and it is indistinguishable
from a deliberate edit by content alone, which is the only evidence a pre-push
hook has.

Install once per clone::

    git config core.hooksPath .githooks
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "tools"))
from _msk import which_bin

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
try:
    from generated_artifact_paths import GENERATED_SINGLE_WRITER_PATHS  # noqa: E402
except ImportError:
    # H4348: this file is vendored (cologne_batch_deploy.py, prepush-guard row)
    # into 14 sibling repos that never carry tools/generated_artifact_paths.py --
    # it is an Uprava-only declaration of --land single-writer targets. A bare
    # import here crashed the checker at module load in every vendored repo,
    # which .githooks/pre-push (`elif ! "$PY" "$CHECKER" ...; then status=1`)
    # turned into a BLOCKED push, not the fail-open the guard promises when its
    # own file is missing. Absent the module, no path is exempt -- exactly
    # today's behaviour in every repo that predates H3073 (18-08-2026).
    GENERATED_SINGLE_WRITER_PATHS = frozenset()

# S27 telemetry (29-08-2026): persist every verdict to the clone's central
# firing record — the "no central firing record exists anywhere" gap of the
# S2 census, which left guard-refusal counts permanently unknown. Optional by
# design: a missing/broken logger degrades to exactly the old behaviour.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from guard_firing_log import log_firing  # noqa: E402
except Exception:  # noqa: SE3 -- telemetry is optional; the guard is not
    log_firing = None

def escape_first_line(human_line: str) -> str:
    """Render the actionable override on the first refusal line."""
    return human_line


def escape_paragraph(human_line: str, paths: list[str] | None = None,
                     refusal_class: str = "content") -> str:
    """Keep override instructions direct; no separate ruling is required."""
    return human_line

ESCAPE_ENV = "ALLOW_STALE_BASE_PUSH"
STRICT_ENV = "STALE_BASE_PUSH_STRICT"
MAX_LISTED = 12
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+")

# Stable, greppable — a wrapper script can `grep` this in captured stderr and
# stop retrying on the FIRST hit instead of burning its whole budget re-asking
# a question this hook's own refusal never depends on the remote tip to answer
# (H3134, FINDINGS §493). Never rename without updating any caller that greps
# it (`handoff_claims.commit_texts_to_origin` currently keys off the banner
# text "PUSH BLOCKED" instead, for the more precise reason documented above).
REFUSAL_MARKER = "STALE_BASE_GUARD_REFUSAL"

# H4342 (08-09-2026): the NON-fast-forward verdict. Emitted instead of a refusal
# when the remote tip is not an ancestor of the pushed commit — see
# `push_is_fast_forward()` and the NON-FAST-FORWARD block in the module
# docstring. Contains neither `PUSH BLOCKED` nor `pre-push: BLOCKED` on purpose:
# `handoff_claims.commit_texts_to_origin` keys `diag["guard_blocked"]` off those
# two strings, and this verdict means the exact opposite of a guard block.
NON_FF_MARKER = "STALE_BASE_NON_FF_SKIP"

# FINDINGS §543/§605: per-path work bounds. A line-level guard with unbounded
# work does not refuse, it HANGS — and a push killed mid-guard by the caller's
# timeout reports as silence, not as a blocked guard, so the author retries into
# the same hang. Past a bound the path is skipped LOUDLY (never silently) and
# the verdict degrades to ref-level merge-base verification; see the LIMITS
# block in the module docstring and report_circuit_break().
CIRCUIT_MARKER = "STALE_BASE_CIRCUIT_BREAK"
DEFAULT_MAX_BLAME_LINES = 2000
DEFAULT_MAX_NEAR_PAIRS = 300_000
DEFAULT_BLAME_TIMEOUT_SECONDS = 30


class BlameTimeout(RuntimeError):
    """The line-level guard hit its wall-clock budget for one path."""

# --- H3069: CHANGELOG tag-drift check (FINDINGS §469) ------------------------
#
# The deletion-side scan above is structurally blind to §469's incident: a clean
# rebase that ADDS a bullet inside an already-tagged `## [x.y.z]` section deletes
# nothing, so `blame_recent` has nothing to flag and the corruption lands clean.
# This is a separate ADDITIVE check alongside `scan()` — it never touches
# `blame_recent`/`surviving_text`/any exemption — scoped to changelog paths,
# sections this push actually touches, and versions that have a pushed tag.
#
# Its override is deliberately NOT reused from ESCAPE_ENV: the two refusals guard
# different risk classes (a deletion-revert vs a mutation of published release
# notes), a wrapper grepping which hatch to raise should be able to tell them
# apart, and the existing banner's own wording ("deletes lines") would be wrong
# for an addition-side refusal.
TAG_DRIFT_ENV = "ALLOW_CHANGELOG_TAG_DRIFT"
TAG_DRIFT_MARKER = "CHANGELOG_TAG_DRIFT_REFUSAL"
#: Bounds for the guard's own git reads (19-10-2026): see `_git_timeout`.
GIT_TIMEOUT_S = 120
FETCH_TIMEOUT_S = 180
#: How long a push may wait for another session's fetch before it runs
#: UNLOCKED anyway (W8H: a lock is never the reason a push is blocked).
FETCH_LOCK_WAIT_S = 120
CHANGELOG_BASENAMES = ("CHANGELOG.md", "Changelog.md", "changelog.md")
SECTION_HEADING_RE = re.compile(r"^## \[([^\]]+)\]")


def _git_timeout(explicit=None) -> int:
    """Whole-second bound for one guard git read (19-10-2026).

    Uprava is a `blob:none` partial clone: a `git show`/`diff`/`blame` of a
    blob that is not local is a PROMISOR NETWORK FETCH, and the startup
    `git fetch` certainly is one. `subprocess.run` with no timeout waits in
    `poll()` forever on a stalled link, and because this script runs inside
    EVERY main push's pre-push hook, that wait holds the caller's push open
    until the caller's own (much larger) landing budget expires — the 19-10
    "mint hung in poll()" shape. `PRE_PUSH_GIT_TIMEOUT_S` raises the bound
    deliberately for a known-slow link; garbage keeps the default.
    """
    if explicit is not None:
        return explicit
    raw = (os.environ.get("PRE_PUSH_GIT_TIMEOUT_S") or "").strip()
    if raw:
        try:
            value = int(raw)
        except ValueError:
            return GIT_TIMEOUT_S
        if value > 0:
            return value
    return GIT_TIMEOUT_S


def _git_timed_out(args, timeout) -> None:
    print("pre-push stale-base: git %s did not answer in %ss (partial-clone "
          "blob fetch or a stalled link); treating the read as unavailable"
          % (" ".join(args), timeout), file=sys.stderr)


def git(*args: str, check: bool = False, timeout=None) -> str:
    timeout = _git_timeout(timeout)
    try:
        proc = subprocess.run(
            ("git",) + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        _git_timed_out(args, timeout)
        if check:
            raise RuntimeError("git %s timed out after %ss" % (" ".join(args), timeout))
        return ""
    if check and proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), proc.stderr.strip()))
    return proc.stdout


def git_ok(*args: str) -> bool:
    """Exit-code view of a git command that prints nothing (merge-base --is-ancestor)."""
    timeout = _git_timeout()
    try:
        proc = subprocess.run(
            ("git",) + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        _git_timed_out(args, timeout)
        return False
    return proc.returncode == 0


class GitReadUnavailable(RuntimeError):
    """``git`` failed for a reason that is NOT "the thing genuinely is not there".

    H5034 (17-09-2026, found by the H4235 verifier on the H5000 close, PR #3028).
    Every read below goes through the plain ``git()`` helper, which swallows a
    non-zero exit and returns empty stdout. For most call sites that is safe by
    accident: they read the OLD content an exemption must MATCH, so an empty
    read grants nothing and the push still blocks — fail-CLOSED. Two sites
    invert it and read EMPTINESS ITSELF as the evidence that unlocks the
    exemption (``main_already_dropped`` gate 2: "the line is not on main any
    more"; ``fresh_archive_rows``: "the pickaxe never saw this row"). There a
    git ERROR reads as proof and the guard exempts a removal it exists to
    refuse — fail-OPEN in a loss-prevention guard.

    So those two sites must be able to tell the two apart, and decline on
    anything that is not a clean answer.
    """


def git_rc(*args: str) -> tuple[int, str]:
    """(exit code, stdout) — the honest view ``git()`` throws away.

    A timeout answers (124, "") — a NON-zero code, so the two inverted sites
    that read emptiness as evidence (``main_already_dropped`` gate 2,
    ``fresh_archive_rows``) treat it as "git could not say" and decline the
    exemption they were about to grant (H5034). `git()`'s empty stdout is
    fail-closed at every other site by the same rule.
    """
    timeout = _git_timeout()
    try:
        proc = subprocess.run(
            ("git",) + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        _git_timed_out(args, timeout)
        return 124, ""
    return proc.returncode, proc.stdout


def path_in_tree(ref: str, path: str) -> bool | None:
    """Does the tree at ``ref`` carry ``path``? ``None`` = git could not say.

    ``ls-tree`` answers from the tree itself, so it needs neither the
    ``<ref>:<path>`` syntax that a literal colon breaks nor a readable blob:
    a gitlink (mode 160000) and a path whose blob object is missing both list
    here while ``git show`` fails on them. ``--full-tree`` because every path
    this guard handles is repository-root-relative (``git diff --name-only``),
    while ``ls-tree`` would otherwise read it relative to the cwd the push ran
    from.
    """
    rc, out = git_rc("ls-tree", "--full-tree", "--name-only", ref, "--", path)
    if rc != 0:
        return None
    return bool(out.strip())


def blob_read(ref: str, path: str) -> list:
    """Lines of ``path`` at ``ref``; ``[]`` when ``ref`` genuinely has no such
    path; raises :class:`GitReadUnavailable` for every other git failure.

    The three shapes that are an error rather than an absence, all seen in the
    wild: a gitlink/submodule entry at that path (``fatal: bad object``), a
    missing or corrupt blob object (``fatal: unable to read``), and a transient
    failure under load. ``git show`` reports all of them exactly as it reports
    a genuinely absent path — non-zero exit, empty stdout — so the tree itself
    is asked (:func:`path_in_tree`) before an empty read is believed.
    """
    spec = "%s:%s" % (ref, path)
    out = git("show", spec)
    if out:
        # Content came back: nothing is ambiguous, and this is the ONE read the
        # module's `git` seam must keep serving — the fixture cases monkeypatch
        # it (case 20 scripts `show`/`blame`/`log` with no repo at all).
        return out.split("\n")
    # Empty stdout is the ambiguous answer git gives to all four of: an empty
    # blob, an absent path, an unreadable one, and a transient failure. Only
    # here does it cost a second spawn to tell them apart.
    rc, raw = git_rc("show", spec)
    if rc == 0:
        return raw.split("\n")
    if path_in_tree(ref, path) is False:
        return []
    raise GitReadUnavailable(
        "git show %s failed and the path is present in (or unverifiable "
        "against) that tree" % spec)


def push_is_fast_forward(remote_ref: str, local_ref: str) -> bool:
    """True when `remote_ref` is already contained in the pushed commit.

    H4342 (08-09-2026). The whole line-level check below is only meaningful for
    a FAST-FORWARD push, and the module docstring has said so since the first
    line of it was written: "a fast-forward push always has
    ``merge-base == remote_tip``", and "Both #1516 incidents were clean
    fast-forwards". When the remote tip is NOT an ancestor of the pushed commit,
    the diff `removed_line_numbers()` computes is against a tip that is not this
    commit's parent, so every line the rival branch added since the fork shows up
    as a deletion this push "makes". It does not: the push is a non-fast-forward
    that git will refuse on its own, and on main/master a forced one is refused
    fail-closed by `scripts/pre_push_main_line_gate.py` check 2 (rewind/rewrite,
    escape ALLOW_MAIN_LINE_REWIND=1). Nothing is lost by declining to judge it.

    MEASURED, not assumed (08-09-2026). `handoff_claims.commit_texts_to_origin`
    pins `base = origin/main`, builds a commit-tree on it, then pushes; on this
    org's two most-contended files another session lands in that window often.
    The same H4339 close commit built on a base that had gone one commit stale
    was refused with 25 phantom deletions across 2 paths, and built on the
    current tip passed clean — same transforms, same content, different base.

    That race is the retry loop's normal, self-healing case, and this guard was
    converting it into `STALE_BASE_GUARD_REFUSAL` ("Retrying cannot clear it")
    plus the H3880 agent-override banner. Worse, `commit_texts_to_origin` reads
    that banner into a sticky `diag["guard_blocked"]`, so a caller that finally
    exhausted its retries reported "This is NOT origin/main moving" — the exact
    inversion of the truth. The guard's own docstring asserted the two states
    were mutually exclusive ("``--is-ancestor origin/main HEAD`` is **true** for
    this LOCAL refusal and **false** for a genuine non-fast-forward"); that is
    true for a branch push of HEAD and false for the plumbing push above, where
    the pushed ref is a detached `commit-tree` sha.

    Cost of the fix in detection power: zero for the class this guard exists to
    catch, which is fast-forward-shaped by definition. What is no longer flagged
    is a deletion inside a push that cannot land as it stands.
    """
    return git_ok("merge-base", "--is-ancestor", remote_ref, local_ref)


def blob_lines(ref: str, path: str) -> list:
    """Lines of ``path`` at ``ref``, numbered exactly as git numbers them (§695).

    NEVER ``str.splitlines()`` for anything a git line number will index into:
    it also breaks on form feed (U+000C), VT, NEL, U+2028 and U+2029, which git
    counts as ordinary characters inside a line. One stray form feed inside
    FINDINGS.md §544 shifted every later line by one, so blame line N indexed
    the text of line N-1 and EVERY content-based exemption below (survivors,
    registry bookkeeping, expired claim rows, class-5 near match) silently
    failed for the two thousand lines after it.

    H5034: this stays the quiet wrapper, for the callers whose empty read
    grants nothing (``blame_recent``'s ``old_text``, the two relocation
    helpers — an unreadable pre-image leaves every candidate line without a
    matching text and their exemptions decline). A caller that would read
    emptiness as EVIDENCE must call :func:`blob_read` and handle
    :class:`GitReadUnavailable` instead.
    """
    try:
        return blob_read(ref, path)
    except GitReadUnavailable:
        return [""]


INTEGRATION_REF_CANDIDATES = ("origin/main", "origin/master")

_MAIN_REF_CACHE: dict = {}
_MAIN_LINES_CACHE: dict = {}
_MAIN_ANCESTOR_CACHE: dict = {}


def integration_ref() -> str | None:
    """The repo's integration branch (``origin/main`` / ``origin/master``).

    ``None`` when neither exists — every caller below then declines, so a repo
    without one keeps exactly the pre-H5000 behaviour.
    """
    if "ref" not in _MAIN_REF_CACHE:
        found = None
        for cand in INTEGRATION_REF_CANDIDATES:
            if git("rev-parse", "--verify", "--quiet", cand).strip():
                found = cand
                break
        _MAIN_REF_CACHE["ref"] = found
    return _MAIN_REF_CACHE["ref"]


def _integration_stripped_lines(path: str) -> frozenset | None:
    """Stripped authored lines of ``path`` on the integration ref.

    A path GENUINELY absent there yields the empty set — which is the right
    answer: main deleted the file, so nothing this push drops from it is a
    silent revert.

    ``None`` when git could not read the path at all (H5034). The caller's gate
    2 asks "is this line's text absent from main?", so an unreadable blob used
    to answer "absent" for EVERY line and unlocked the exemption on a git
    error. ``None`` is UNKNOWN, and unknown must never exempt.
    """
    if path not in _MAIN_LINES_CACHE:
        ref = integration_ref()
        try:
            text = blob_read(ref, path) if ref else []
        except GitReadUnavailable:
            _MAIN_LINES_CACHE[path] = None
            return None
        _MAIN_LINES_CACHE[path] = frozenset(
            t.strip() for t in text if t.strip())
    return _MAIN_LINES_CACHE[path]


def main_already_dropped(remote_ref: str, path: str, sha: str,
                         stripped: str) -> bool:
    """True when the integration branch ALREADY dropped this line.

    H5000 (MG ruling 16-09-2026: «fix the guard to diff against origin/main»).
    The scan's base is ``origin/<branch-being-pushed>`` — the branch's own
    remote tip. That is right for the #1516 class, but it makes every commit
    main landed since that tip read as a deletion BY THIS PUSH: a feature
    branch that merges a fresh origin/main carries main's own removals, and the
    guard blames them on the pusher. Measured live on the H4958 close
    (16-09-2026): 17 lines across 4 files, every one of them main's own H4956
    ``tools/_common.py`` refactor (commit ``3e9f6cea5``), while the pushed tree
    was byte-identical to ``origin/main`` for all four paths.

    Two gates, both required, so coverage is not traded away:

    1. **The blamed commit is already on the integration ref.** Branch-only
       work by a co-worker (a commit main has never seen) is NOT covered by
       this exemption and still blocks — that is the shared-feature-branch half
       of the #1516 class.
    2. **The line's text is absent from the path on the integration ref.** If
       main still carries the line, dropping it IS a revert and still blocks.

    Both true means the content is already gone from the branch everything
    merges into: this push cannot be the thing that loses it.
    """
    ref = integration_ref()
    if not stripped or ref is None:
        return False
    if remote_ref == ref:
        # Pushing to main itself: the base already IS the integration ref, so
        # every removed line is present on it by construction. Decline
        # explicitly rather than rely on gate 2 — a main push must keep the
        # full #1516 coverage it has always had.
        return False
    if sha not in _MAIN_ANCESTOR_CACHE:
        _MAIN_ANCESTOR_CACHE[sha] = git_ok("merge-base", "--is-ancestor",
                                           sha, ref)
    if not _MAIN_ANCESTOR_CACHE[sha]:
        return False
    main_lines = _integration_stripped_lines(path)
    if main_lines is None:
        # H5034: git could not read the path on the integration ref, so gate 2
        # has NO answer — not "the line is gone from main". Fail closed: the
        # push blocks and the override is the documented human path, which is
        # the same posture gate 1 already has (git_ok on merge-base).
        return False
    return stripped not in main_lines


def path_matches_integration(local_ref: str, path: str) -> bool:
    """True when the pushed tree's ``path`` is byte-identical to the integration
    ref, so this push cannot change it.

    WBA (22-10-2026): a branch that adopts main's canonical version of a fix
    removes its own earlier duplicate from the diff. The line-level credits
    read that removal as a stale-base revert of branch-only lines — the blaming
    commit is not on main, so ``main_already_dropped`` gate 1 declines — even
    though the pushed file is byte-identical to main's. If the pushed tree
    already IS main's content for this path, merging the push is a no-op for
    it: credit the path before any blame.

    ``path_in_tree`` is asked first so a DELETION still takes the whole-file
    self-cleanup path above (and an unreadable tree declines, fail-closed).
    Only ``git diff --quiet`` exit 0 counts: a difference (1) or a git error
    (>1) grants nothing.
    """
    ref = integration_ref()
    if ref is None or not path_in_tree(local_ref, path):
        return False
    rc, _ = git_rc("diff", "--quiet", ref, local_ref, "--", path)
    return rc == 0


def pushed_commits(remote_ref: str, local_ref: str) -> set[str]:
    out = git("rev-list", "%s..%s" % (remote_ref, local_ref))
    return {line.strip() for line in out.splitlines() if line.strip()}


def changed_paths(remote_ref: str, local_ref: str) -> list[str]:
    # H5042: -z, split on NUL. Without it core.quotePath (default true)
    # C-quotes every non-ASCII name ("\320\272...md"), and every later
    # show/blame/pathspec on that spelling matches nothing — a Cyrillic,
    # Devanagari or IAST-named file was pushed through UNSCANNED.
    out = git("diff", "--name-only", "-z", "-w", remote_ref, local_ref)
    return [p for p in out.split("\0") if p.strip()]


# --------------------------------------------------------------------------- #
# Mint-claim exemption (GTD row WC7, H7216 residual, 22-10-2026)
# --------------------------------------------------------------------------- #
# The mint's claim commit is built by `tools/mint_push.py` with git plumbing:
# ONE commit whose parent IS the freshly fetched `origin/main` tip, carrying a
# new `handoffs/H###-*.md` stub plus the mint's own rewrite of the registry's
# DERIVED lines (the Next-free-ID marker, `**Counts:**`, the 🟡 header count)
# and, for a `--parent E###` child, one appended bullet in the epic's Children
# list. The #1516 class — "a pre-image copy deletes a line another session
# added moments ago" — cannot occur in that commit: every path except the
# registry/epic is byte-identical to the tip, and the only deletions are lines
# the mint itself derives. Proving that shape costs a handful of git reads
# instead of the 174-371 s blame sweep (338 s measured 22-10-2026, H7216) that
# could consume the whole claim push before it reached the network.
#
# The proof is STRICT and falls back to the full scan on ANY doubt — one
# parent == the remote tip, the exact mint subject, a changed-path set limited
# to an ADDED stub (+ the registry / an existing epic with derived-only
# deletions). A human push never carries that subject, so the guard keeps its
# full force for human pushes (the H7216 non-goal).
MINT_CLAIM_SUBJECT_RE = re.compile(
    r"^mint: claim (?:[HE]\d+ (?:stub|epic)"
    r"|[HE]\d+\.\.[HE]\d+ stubs \(batch of \d+\))$")

#: The registry lines `tools/mint_push.py::_readme_with_rows` legitimately
#: rewrites. Copies live here for the same reason `tools/mint_stub.py` keeps
#: its own: the checker must run standalone in a partial clone. Drift is
#: fail-SAFE — an unmatched derived line makes the proof decline and the full
#: scan run, never the other way round.
_MINT_DERIVED_README_RE = re.compile(
    r"^(?:"
    # The real line carries emphasis and a full stop: `**Next free ID: `H###`.**`
    # — matched exactly as it is written in handoffs/README.md today.
    r"(?:\*\*)?Next free ID: `H\d{3,}`\.?(?:\*\*)?\s*$"
    # The counts line may carry a parenthetical note after `rowed.`, so this
    # alternative is a prefix test, not a whole-line one.
    r"|\*\*Counts:\*\*\s*🔵 In work \*\*\d+\*\*\s*·\s*✅ Finished \*\*\d+"
    r"\*\*\s*·\s*🟡 Yet to launch \*\*\d+\*\*\s*·\s*total \*\*\d+\*\* rowed\."
    r"|##\s+🟡\s+.+?\s+\(\d+\)\s*$"
    r")")

#: The epic Children placeholder `tools/mint_epics.py::_epic_with_children`
#: replaces with the first child bullet.
_MINT_DERIVED_EPIC_RE = re.compile(
    r"^_none yet — mint children with `--parent E###`_$")

_MINT_STUB_PATH_RE = re.compile(r"^handoffs/[HE]\d+-[^/]+\.md$")
_MINT_EPIC_PATH_RE = re.compile(r"^handoffs/epics/[HE]\d+-[^/]+\.md$")


def _diff_line_texts(remote_ref: str, local_ref: str,
                     path: str) -> tuple[list[str], list[str]]:
    """(removed, added) line TEXTS of `path` between the two refs (-w, -U0)."""
    out = git("diff", "-w", "-U0", remote_ref, local_ref, "--", path)
    removed: list[str] = []
    added: list[str] = []
    # Only hunks carry content: the `diff --git` / `---` / `+++` preamble sits
    # BEFORE the first `@@`, so skipping everything up to it cannot confuse a
    # content line that begins with `-` or `+` for a header (the `-w -U0`
    # output has no context lines inside a hunk).
    in_hunks = False
    for line in out.splitlines():
        if line.startswith("@@"):
            in_hunks = True
            continue
        if not in_hunks:
            continue
        if line.startswith("-"):
            removed.append(line[1:])
        elif line.startswith("+"):
            added.append(line[1:])
    return removed, added


def _mint_only_derived_deletions(remote_ref: str, local_ref: str, path: str,
                                 derived_re: "re.Pattern[str]") -> bool:
    """True when every line this push removes from `path` is either re-added
    verbatim elsewhere in the file (a move) or a line the MINT derives."""
    removed, added = _diff_line_texts(remote_ref, local_ref, path)
    surviving = set(added)
    return all(ln in surviving or derived_re.search(ln) for ln in removed)


def mint_claim_proof(remote_ref: str, local_ref: str) -> dict | None:
    """Prove the pushed commit is a mint claim; None when it is anything else.

    The returned dict is the evidence carried into the hook's journal line.
    Every read is cheap (rev-list / rev-parse / diff / cat-file): no blame.
    """
    head = git("rev-list", "--parents", "-n", "1", local_ref).split()
    if len(head) != 2:
        return None                    # not the mint's single-commit shape
    remote_sha = git("rev-parse", "--verify", "--quiet", remote_ref).strip()
    if not remote_sha or head[1] != remote_sha:
        return None                    # parent is NOT the remote tip: no proof
    subject = git("log", "-1", "--format=%s", local_ref).strip()
    if not MINT_CLAIM_SUBJECT_RE.match(subject):
        return None                    # not a mint claim; human pushes keep the scan
    paths = changed_paths(remote_sha, local_ref)
    if not paths:
        return None
    added: list[str] = []
    touched: list[str] = []
    for path in paths:
        exists = git_ok("cat-file", "-e", "%s:%s" % (remote_sha, path))
        if path == "handoffs/README.md":
            if not exists:
                return None
            if not _mint_only_derived_deletions(remote_sha, local_ref, path,
                                                _MINT_DERIVED_README_RE):
                return None
            touched.append(path)
        elif _MINT_EPIC_PATH_RE.match(path):
            if exists:
                # An epic's Children splice only appends; anything else is not
                # the mint shape and must face the full scan.
                if not _mint_only_derived_deletions(remote_sha, local_ref, path,
                                                    _MINT_DERIVED_EPIC_RE):
                    return None
                touched.append(path)
            else:
                added.append(path)
        elif _MINT_STUB_PATH_RE.match(path):
            if exists:
                # A claim only ever ADDS its stub; rewriting an existing
                # handoff body is not mint's to do.
                return None
            added.append(path)
        else:
            return None                # any other path: no exemption
    if not added:
        return None                    # a claim must add its stub/epic
    return {"subject": subject, "parent": remote_sha,
            "added": added, "touched": touched}


def removed_line_numbers(remote_ref: str, local_ref: str, path: str) -> list[int]:
    """Line numbers AT THE REMOTE TIP that this push removes or rewrites."""
    out = git("diff", "-w", "-U0", remote_ref, local_ref, "--", path)
    numbers: list[int] = []
    old_line = 0
    for line in out.splitlines():
        m = HUNK_RE.match(line)
        if m:
            old_line = int(m.group(1))
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            numbers.append(old_line)
            old_line += 1
    return numbers


def added_line_numbers(remote_ref: str, local_ref: str, path: str) -> list[int]:
    """Line numbers IN THE PUSHED FILE that this push adds or rewrites."""
    out = git("diff", "-w", "-U0", remote_ref, local_ref, "--", path)
    numbers: list[int] = []
    new_line = 0
    for line in out.splitlines():
        # The plus side of the hunk header carries the NEW start; HUNK_RE above
        # captures only the minus side, so this needs its own pattern.
        hm = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", line)
        if hm:
            new_line = int(hm.group(1))
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("+"):
            numbers.append(new_line)
            new_line += 1
    return numbers


_HEX = set("0123456789abcdef")


def blame_map(remote_ref: str, path: str,
              timeout_seconds: int = DEFAULT_BLAME_TIMEOUT_SECONDS) -> dict[int, list]:
    """Introducing [sha, author, time] of EVERY line of `path` at the remote tip,
    from ONE git blame invocation.

    §543/§605: the original loop paid one `git blame -L n,n` subprocess per
    removed line — 28k subprocesses on a wholesale derived-JSON rewrite, each
    re-parsing a multi-megabyte file. One batched `--line-porcelain` blame per
    path returns the identical per-line answer (same `-w`, same tip) at
    O(file) total. Keyed by the FINAL line number at the remote tip; lines git
    did not report (binary, unreadable) are simply absent — callers skip them,
    exactly as the per-line form did on empty output.
    """
    try:
        proc = subprocess.run(
            (which_bin("git"), "blame", "-w", "--line-porcelain", remote_ref, "--", path),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise BlameTimeout(
            "%s exceeded %ss" % (path, timeout_seconds)
        ) from exc
    out = proc.stdout
    result: dict[int, list] = {}
    cur: list | None = None
    for line in out.splitlines():
        if not line or line.startswith("\t"):
            continue
        parts = line.split()
        # Porcelain header: "<40-hex sha> <orig_lineno> <final_lineno> [<group>]".
        if parts and len(parts[0]) == 40 and set(parts[0]) <= _HEX:
            sha = parts[0]
            try:
                lineno = int(parts[2])
            except (IndexError, ValueError):
                lineno = 0
            cur = result.setdefault(lineno, [sha, "", None])
            cur[0] = sha
            continue
        if cur is None:
            continue
        if line.startswith("author "):
            cur[1] = line[len("author "):].strip()
        elif line.startswith("author-time "):
            try:
                cur[2] = datetime.fromtimestamp(int(line.split()[1]),
                                                tz=timezone.utc)
            except (ValueError, IndexError):
                cur[2] = None
    return result


def changelog_sections(text: str) -> list[tuple[str, int, int]]:
    """[(version, body_start0, body_end0_exclusive)] for each `## [v]` heading.

    A section's body is everything from the line after its heading down to (not
    including) the next `## [` heading, or EOF. `[Unreleased]` parses like any
    other bracket token and is filtered later by the tag lookup.
    """
    lines = text.split("\n")
    heads: list[tuple[str, int]] = []
    for i, ln in enumerate(lines):
        m = SECTION_HEADING_RE.match(ln)
        if m:
            heads.append((m.group(1).strip(), i))
    sections: list[tuple[str, int, int]] = []
    for j, (ver, hidx) in enumerate(heads):
        end = heads[j + 1][1] if j + 1 < len(heads) else len(lines)
        sections.append((ver, hidx + 1, end))
    return sections


def posix_basename(path: str) -> str:
    """Basename across BOTH separators — §469 gate 1.

    The inline form this replaces read ``replace("\\\\", "/")`` — a
    TWO-character literal that never matches a real Windows path, so every
    backslash-separated CHANGELOG path silently skipped the whole tag-drift
    check (H3587 wave-2 delta review; found by reading, pinned here so the
    two-char spelling cannot creep back).
    """
    return path.replace("\\", "/").split("/")[-1]


def changelog_tag_drift(remote_ref: str, local_ref: str,
                        max_paths: int) -> list[dict]:
    """Sections this push mutates under a version that already has a pushed tag.

    Returns one dict per drifted section:
        {"path": ..., "tag": "vx.y.z", "version": ..., "heading": ...,
         "lines": [(pushed_line_no, kind), ...]}
    where kind is "added" or "changed" relative to `git show <tag>:<path>`.

    Fail-open on everything it cannot verify: no local tag object, a tag blob
    that lacks the file entirely, an unparseable diff — none of these block,
    because a guard that refuses pushes it cannot reason about gets switched
    off (the stale-base sibling's own demotion lesson). Only a verified,
    byte-level difference between the pushed section and the tagged section
    refuses.
    """
    findings: list[dict] = []
    for path in changed_paths(remote_ref, local_ref)[:max_paths]:
        if posix_basename(path) not in CHANGELOG_BASENAMES:
            continue
        added = added_line_numbers(remote_ref, local_ref, path)
        if not added:
            continue  # nothing inserted/rewritten by THIS push: deletion-side scan's job
        pushed_lines = blob_lines(local_ref, path)
        for ver, b0, b1 in changelog_sections("\n".join(pushed_lines)):
            touched = [n for n in added if b0 <= n <= b1]
            if not touched:
                continue  # untouched section: never diffed (170+ sections must not cost)
            tag = "v%s" % ver.split()[0].lstrip("v")
            if not git("rev-parse", "--verify", "--quiet",
                       "refs/tags/%s" % tag).strip():
                continue  # [Unreleased], untagged versions: allowed by design
            tag_blob = git("show", "%s:%s" % (tag, path))
            if not tag_blob.strip():
                continue  # file absent at the tag: unverifiable, fail open
            tag_sections = {v: (s0, s1) for v, s0, s1 in
                            changelog_sections(tag_blob)}
            tag_lines = tag_blob.split("\n")
            if ver in tag_sections:
                t0, t1 = tag_sections[ver]
                tag_body = tag_lines[t0:t1]
            else:
                tag_body = []  # section created after tagging: whole body is drift
            pushed_body = pushed_lines[b0:b1]
            sm = difflib.SequenceMatcher(a=tag_body, b=pushed_body, autojunk=False)
            drift: list[tuple[int, str]] = []
            for op, i0, i1, j0, j1 in sm.get_opcodes():
                if op == "equal":
                    continue
                kind = "changed" if op == "replace" else "added"
                for k in range(j0, j1):
                    drift.append((b0 + k + 1, kind))
            if drift:
                heading = pushed_lines[b0 - 1].strip() if b0 - 1 < len(pushed_lines) else ver
                findings.append({"path": path, "tag": tag, "version": ver,
                                 "heading": heading, "lines": drift})
    return findings


def report_tag_drift(findings: list[dict]) -> None:
    total = sum(len(f["lines"]) for f in findings)
    e = sys.stderr
    print("", file=e)
    print("%s — LOCAL guard refusal, not a moved remote tip." % TAG_DRIFT_MARKER,
          file=e)
    print("  Override:  %s=1 git push ..." % TAG_DRIFT_ENV, file=e)
    print("PUSH BLOCKED — this push adds or changes %d line(s) inside "
          "CHANGELOG.md section(s) already published under a pushed tag, in "
          "%d section(s)." % (total, len(findings)), file=e)
    print("FINDINGS §469: a silent ADDITION inside a tagged section deletes "
          "nothing, so the deletion-side check above cannot see it; a released "
          "section must stay byte-identical to its tag.", file=e)
    print("", file=e)
    shown = 0
    for f in findings:
        print("  %s" % f["path"], file=e)
        print("      %s  (tag %s)" % (f["heading"], f["tag"]), file=e)
        for ln, kind in f["lines"]:
            if shown >= MAX_LISTED:
                break
            print("          line %-6d %s vs %s:CHANGELOG.md"
                  % (ln, kind, f["tag"]), file=e)
            shown += 1
        if shown >= MAX_LISTED:
            print("          …", file=e)
            break
    print("", file=e)
    print("If the change IS deliberate (fixing the section's prose, never its "
          "meaning):  %s=1 git push ..." % TAG_DRIFT_ENV, file=e)
    print("", file=e)


STUB_MARKER = "STUB claimed by mint_handoff.py"


def changelog_structure_findings(text: str) -> list[dict]:
    """Structural collisions in a CHANGELOG body: duplicate headings + order.

    The #2335 release-rebase collision (29-08-2026) inserted `## [0.195.347]`
    ABOVE the then-[Unreleased] block, so later appends landed inside a tagged
    section AND a duplicate `## [0.195.347]` heading materialised further
    down. The tag-drift check above only fires when THIS push adds lines into
    a tagged section — it is silent on a layout that is ALREADY broken and on
    a heading duplicated by a bad merge. Both shapes are verified here from
    the pushed text alone, no tag lookup needed:

      - duplicate-heading: the same `## [v]` token appears twice — one of the
        two bodies is unreachable by any reader or tool (`changelog_sections`
        itself keeps only the LAST occurrence).
      - order-violation: version sections do not strictly descend
        (`[Unreleased]` first, then newest → oldest). The collision shipped
        …349, 347, 348… — a shape no correct history produces.

    Pure function; the caller scopes it to changed CHANGELOG paths.
    """
    findings: list[dict] = []
    lines = text.split("\n")
    heads: list[tuple[str, int]] = []
    for i, ln in enumerate(lines):
        m = SECTION_HEADING_RE.match(ln)
        if m:
            heads.append((m.group(1).strip(), i))
    seen: dict[str, int] = {}
    for ver, i in heads:
        if ver in seen:
            findings.append({"kind": "duplicate-heading", "version": ver,
                             "line": i + 1,
                             "first_line": seen[ver] + 1})
        else:
            seen[ver] = i

    def rank(ver: str):
        if ver == "Unreleased":
            return (0, [])
        nums = [int(x) for x in re.findall(r"\d+", ver)]
        return (1, [-n for n in nums])

    ranked = [(rank(ver), ver, i + 1) for ver, i in heads
              if ver != "Unreleased"]
    for a, b in zip(ranked, ranked[1:]):
        if not (a[0] < b[0]):
            findings.append({"kind": "order-violation",
                             "version": "%s then %s" % (a[1], b[1]),
                             "line": b[2], "first_line": a[2]})
    return findings


def rank_key_lt(a, b) -> bool:
    """Strictly-less for the (group, negated-nums) rank tuples."""
    return a < b


def changelog_structure_path_findings(remote_ref: str, local_ref: str,
                                      max_paths: int) -> list[tuple[str, list[dict]]]:
    """Structural findings per changed CHANGELOG path in THIS push.

    Same changed-path scoping as `changelog_tag_drift` (a push that never
    touches a changelog never pays for the check); runs the pure
    `changelog_structure_findings` on the pushed content. Returns
    [(path, findings)] for paths with at least one finding.
    """
    out: list[tuple[str, list[dict]]] = []
    for path in changed_paths(remote_ref, local_ref)[:max_paths]:
        if posix_basename(path) not in CHANGELOG_BASENAMES:
            continue
        pushed = git("show", "%s:%s" % (local_ref, path))
        if not pushed.strip():
            continue  # file deleted in this push: not this check's class
        f = changelog_structure_findings(pushed)
        if f:
            out.append((path, f))
    return out


def report_structure_drift(findings: list[dict], path: str) -> None:
    e = sys.stderr
    print("", file=e)
    print("%s — LOCAL guard refusal, not a moved remote tip." % TAG_DRIFT_MARKER,
          file=e)
    print("  Override:  %s=1 git push ..." % TAG_DRIFT_ENV, file=e)
    print("PUSH BLOCKED — %s is structurally broken in this push: "
          "%d finding(s)." % (path, len(findings)), file=e)
    print("FINDINGS (29-08-2026 #2335 collision): a duplicated `## [v]` "
          "heading or a non-descending section order means a release rebase "
          "or a bad merge lodged content inside a tagged section — the "
          "tag-drift check cannot see a layout that is already broken or a "
          "duplicate heading, so this shape-level check refuses.", file=e)
    print("", file=e)
    shown = 0
    for f in findings:
        if shown >= MAX_LISTED:
            print("          …", file=e)
            break
        print("      line %-6d %s: %s (first occurrence line %d)"
              % (f["line"], f["kind"], f["version"], f["first_line"]), file=e)
        shown += 1
    print("", file=e)
    print("If the change IS deliberate (repairing the leaked layout):  "
          "%s=1 git push ..." % TAG_DRIFT_ENV, file=e)
    print("", file=e)


def surviving_text(local_ref: str, path: str) -> set[str]:
    """Every non-blank stripped line of the path as this push would leave it.

    Used to separate a MOVE from a LOSS. Renumbering a changelog section, resolving a
    merge by relocating someone's rows, reordering a table — all delete lines at their
    old position and re-add them elsewhere. The remote keeps the content, so there is
    nothing to protect. Only a line whose text survives NOWHERE in the pushed file is a
    real deletion. (Found by dogfooding: the guard blocked its own landing commit for
    exactly this, which is the false-positive class that gets a blocking hook disabled.)
    """
    out = git("show", "%s:%s" % (local_ref, path))
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


# H3134: a card evicted from GTD_NEXT_ACTIONS.md by `gtd_active_state.py
# --migrate` is written verbatim into GTD_ARCHIVE.md in the SAME commit — see
# the module docstring's exemptions section for why this qualifies (verbatim
# survivor). Scoped to declared pairs on purpose: widening to "any two files
# touched by the same push" would let the survivors check quietly absorb an
# unrelated file's coincidental text match.
CROSS_FILE_ARCHIVE_PAIRS = {
    "gtd_next_actions.md": "GTD_ARCHIVE.md",
}

# FINDINGS §450/§530 (H3253): the two halves of the handoff registry are ONE
# logical document — a close MOVES a row from the live half to the archive
# half. Unlike the GTD pair above, survivor credit is gated on the SAME push:
# only lines this push ADDS to REGISTRY_ARCHIVE.md count, so a stale checkout
# that merely drops someone's fresh row gains no credit from rows archived
# long ago. One-directional by construction — see relocated_registry_rows()
# for the rewritten-status-cell shape; un-archiving over live rows blocks.
# Keys are case-folded for dispatch; values are exact Git tree paths.
# Git pathspecs remain case-sensitive on Windows. Lowercasing the value made
# real archive moves invisible while the old lowercase-only fixtures passed.
# H4569 (11-09-2026): since the H4409 shard split REGISTRY_ARCHIVE.md is a META
# file and closed rows land in handoffs/registry/archive-shard-NNNN.md, so the
# archive half is BOTH pathspecs (tools/registry_source.py SHARD_DIR_RELPATH).
# Credit comes from net_added_line_texts — a shard rotation re-adds rows it
# removed from the older shard, and those moved rows must credit nothing.
REGISTRY_SHARD_GLOB = ":(glob)handoffs/registry/archive-shard-*.md"
REGISTRY_SHARD_RE = re.compile(r"^handoffs/registry/archive-shard-\d+\.md$")
REGISTRY_RELOCATION_PAIR = {
    "handoffs/readme.md": ("handoffs/REGISTRY_ARCHIVE.md", "handoffs/registry/"),
}

# FINDINGS §659 (03-09-2026): a release cut CONSUMES changelog_queue/*.md — each
# fragment's bullet is copied into CHANGELOG.md and the fragment file is deleted in
# the SAME commit (cut_release.py, H3833). Every fragment another session queued in
# the last --recent-days is therefore deleted by construction, so EVERY release push
# refuses (measured on v0.195.419: 35 lines across 33 files), and the only way out
# was the human-addressed override — routine work behind an override is the reflex
# §641/§643 warn about. This is a MOVE, not a loss: the bullet is right there in the
# pushed CHANGELOG.md, which is exactly what surviving_text() exists to recognise,
# only across paths. A directory prefix rather than a dict key because the queue is
# a glob of many one-entry files, and one-directional: fragments feed the changelog,
# never the reverse.
CHANGELOG_QUEUE_PREFIX = "changelog_queue/"

# §530 bar: a shorter shared run is noise — ids, pipes, "| Sonnet | x |"
# boilerplate recur across unrelated rows — while 40+ contiguous chars are
# unique to the moved row. A line shorter than the bar can never claim the
# fragment exemption.
VERBATIM_FRAGMENT_MIN = 40


def has_verbatim_fragment(text: str, candidates) -> bool:
    """True when >= VERBATIM_FRAGMENT_MIN contiguous chars of `text` appear
    verbatim inside one of `candidates`.

    The §437 bar made mechanical: recognisable from the pushed content alone,
    no intent guessed. Survives the status-cell rewrite a close performs,
    because the title/link/repo cells move over untouched."""
    if len(text) < VERBATIM_FRAGMENT_MIN:
        return False
    n = VERBATIM_FRAGMENT_MIN
    for cand in candidates:
        for i in range(len(text) - n + 1):
            if text[i:i + n] in cand:
                return True
    return False


def cross_file_survivors(remote_ref: str, local_ref: str, path: str) -> set[str]:
    """Lines of `path`'s declared sibling archive that count as survivors.

    GTD pair: every non-blank stripped line of the sibling AS THIS PUSH WOULD
    LEAVE IT — the migration always rewrites the archive in the same commit,
    so the pushed tree IS the same-push evidence. Registry pair (§530): only
    the lines THIS PUSH ADDS to REGISTRY_ARCHIVE.md, so an archive untouched
    by the push credits nothing. The changelog queue (§659) is NOT here, on
    purpose: its credit is an equality test taken before blame, because this set
    also feeds class 5's near match — see `promoted_queue_lines`. Empty set if
    `path` has no declared sibling.
    """
    key = path.replace("\\", "/").lower()
    sibling = CROSS_FILE_ARCHIVE_PAIRS.get(key)
    if sibling:
        out = git("show", "%s:%s" % (local_ref, sibling))
        return {ln.strip() for ln in out.splitlines() if ln.strip()}
    if key in REGISTRY_RELOCATION_PAIR:
        return set(fresh_archive_rows(remote_ref, local_ref,
                                      REGISTRY_RELOCATION_PAIR[key], path))
    if REGISTRY_SHARD_RE.match(key):
        # H4569: a shard rotation moves rows verbatim into ANOTHER shard. Only
        # rows this push adds to a sibling shard count — an untouched shard
        # credits nothing, and the text survives byte-for-byte, so no loss.
        # Exact equality only: the caller keeps these out of class 5.
        added, _ = diff_line_texts(remote_ref, local_ref, REGISTRY_SHARD_GLOB,
                                   ":(exclude)" + path)
        return set(added)
    return set()


# handoffs/H123-foo.md -> handoffs/archive/H123-foo.md, in a path or a full blob URL.
# Negative lookahead so an already-archived link is left alone (the transform must be
# idempotent, or a second archive pass would stop matching).
ARCHIVE_REPOINT_RE = re.compile(r"(handoffs/)(?!archive/)(H\d+[^)\s\"'<>]*\.md)")


def archive_normalized(text: str) -> str:
    """Collapse the pre- and post-archive spelling of a handoff link to one form.

    Class 3 of the known false positives: `handoff_close.py` archiving a handoff
    repoints every `handoffs/X.md` reference to `handoffs/archive/X.md`, including
    inside registry rows another session added minutes ago. The row is NOT lost —
    only its link is repointed — but the raw text no longer matches, so the
    surviving-text check in `blame_recent` cannot see it as a move.

    Normalizing the REMOVED line makes that visible: it is exempt only when its
    text, once the repoint is applied, still exists verbatim in the pushed file. A
    push that repoints a link AND drops anything else on the line does not match,
    so this forgives exactly the archive rewrite and nothing more.

    ONE DIRECTION ONLY — do not also normalize the survivors. Un-archiving someone's
    link (pushing `handoffs/X.md` over their `handoffs/archive/X.md`) is the exact
    pre-image revert this guard exists to catch, and it is what the test's own case 1
    does. Normalizing both sides makes the two indistinguishable and silently forgives
    the real defect; the lookahead above is what keeps the transform one-way.
    """
    return ARCHIVE_REPOINT_RE.sub(r"\1archive/\2", text)


# The two halves of the handoff registry. Scoped deliberately: the "Last updated"
# shape below appears in EVERY authored .md in the org, and exempting it globally
# would let a session silently revert someone's date bump.
REGISTRY_PATHS = ("handoffs/readme.md", "handoffs/registry_archive.md")

# FINDINGS §695 (03-09-2026): every FINDINGS.md append necessarily rewrites the
# file's single trailing marker line `§N takes the next number.` — the number is
# consumed and bumped by the very act of appending. That line is therefore
# deleted-and-replaced on EVERY append, so every append trips this guard the same
# way §659 measured every release push tripping it, and a guard overridden on
# routine work trains the override reflex it exists to prevent (§641/§643 class).
#
# One-directional, and readable from the pushed content alone per the §437 bar:
# exempt ONLY when the same push leaves a marker whose number is STRICTLY
# GREATER. A stale checkout reinstalling a pre-image marker moves the number
# backwards (or leaves it equal) and still blocks — that is precisely the H1516
# shape. The match is anchored and whole-line, so a push that rewrites the marker
# into anything else gains no exemption, and every other line stays fully guarded.
#
# The marker has two hand-off forms — `§N takes the next number.` and the long
# `§N takes the next number past §M.` (findings_append writes the long one when
# the file already ends in it, so a session can splice the tail without a tool).
# Both are the same consumed-and-bumped line, so both match here; otherwise a
# routine append silently regains the block this exemption exists to remove.
FINDINGS_BASENAMES = ("findings.md",)
FINDINGS_MARKER_RE = re.compile(r"^§(\d+) takes the next number(?: past §\d+)?\.$")


def findings_marker_bump(path: str, text: str, survivors: set) -> bool:
    """The FINDINGS next-number marker, consumed by an append (§695).

    ``text`` is the removed line; ``survivors`` is every stripped line of the
    file as this push would leave it. True only when both are the marker and the
    surviving number is strictly greater — a bump forward, never a rollback.
    """
    norm = path.replace("\\", "/").lower()
    if not any(norm.endswith(b) for b in FINDINGS_BASENAMES):
        return False
    removed = FINDINGS_MARKER_RE.match(text.strip())
    if removed is None:
        return False
    old = int(removed.group(1))
    for line in survivors:
        kept = FINDINGS_MARKER_RE.match(line)
        if kept is not None and int(kept.group(1)) > old:
            return True
    return False


# Lines `registry_check.apply_fix` REGENERATES on every close: the dated header, the
# next-free-ID marker, the counts line, and each bucket header's `(N)`.
REGISTRY_BOOKKEEPING_RES = (
    re.compile(r"^_Created:.*Last updated:.*_$"),
    re.compile(r"^\*\*Next free ID:"),
    re.compile(r"^\*\*Counts:\*\*"),
    re.compile(r"^##\s+.*\(\d+\)\s*$"),
)


# The Active Claims ledger. Its rows are written by `claim_handoff.py`, aged out by
# wall-clock TTL, and removed by `sweep_expired_claims.py` — nobody authors one.
CLAIM_LEDGER_PATHS = ("next_task_queue.md",)

# `| H3001 | multi | exec · Opus 5 (claude-opus-5) · pid28180 | <claimed ISO> | <expires ISO> |`
# Anchored to the whole five-cell shape INCLUDING both timestamps, so no other line in
# that file (the denylist, prose, headers) can match it.
CLAIM_ROW_RE = re.compile(
    r"^\|\s*H\d+\s*\|[^|]*\|[^|]*\|\s*(?P<claimed>\d{4}-\d{2}-\d{2}T[\d:]+Z)\s*"
    r"\|\s*(?P<expires>\d{4}-\d{2}-\d{2}T[\d:]+Z)\s*\|\s*$"
)


def is_expired_claim_row(path: str, text: str, now: datetime | None = None) -> bool:
    """An Active-Claims ledger row whose TTL has ALREADY run out.

    Class (b) of the §437 family, measured 18-08-2026. A claim row expires on a
    6-hour TTL but this guard protects any line for 3 days, so for ~2.5 days a row
    is simultaneously **expired** (the ledger says it is free) and **protected**
    (this guard says deleting it is a silent revert). In that window
    ``sweep_expired_claims.py`` — the org's only sanctioned release path, which has
    no ``--force`` and sets no escape — cannot land, and releasing a dead claim
    requires ``ALLOW_STALE_BASE_PUSH=1`` on entirely routine hygiene. That is the
    exact false-positive shape that got this guard demoted to a warning once before.

    Exempt because the row is **derived, and already dead by its own timestamp**: it
    is a lease, its content is reconstructible by re-claiming, and losing one
    destroys no work.

    The expiry check is the load-bearing half and is not optional. An **unexpired**
    row still blocks, because deleting a live claim is how two sessions end up in one
    tree (H214) — the incident this ledger exists to prevent. Whoever widens this must
    keep that case red.
    """
    norm = path.replace("\\", "/").lower()
    if not any(norm.endswith(p) for p in CLAIM_LEDGER_PATHS):
        return False
    m = CLAIM_ROW_RE.match(text.strip())
    if not m:
        return False
    try:
        expires = datetime.strptime(m.group("expires"), "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            expires = datetime.strptime(m.group("expires"), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return False  # unparseable expiry -> never exempt, fail closed
    return expires.replace(tzinfo=timezone.utc) <= (now or datetime.now(timezone.utc))


def is_registry_bookkeeping(path: str, text: str) -> bool:
    """A generated bookkeeping line in the handoff registry — recomputed, never authored.

    Class (a) of FINDINGS §437, and the last false positive that forced
    ``ALLOW_STALE_BASE_PUSH=1`` on routine work. ``registry_check.apply_fix`` rewrites
    the dated header, the next-free-ID marker, the ``**Counts:**`` line and every
    bucket header's ``(N)`` on EVERY close. Two closes inside the 3-day window
    therefore always look like each other's revert, because both legitimately rewrite
    the same four lines — and §435 measured that blocking BOTH sanctioned close paths
    under ordinary push traffic.

    Exempt because these lines are **derived**, not authored: their content is a
    function of the rows around them, so a close that recomputes them destroys no
    work, and a close that gets them wrong is caught by ``registry_check`` rather
    than by this guard. Handoff ROWS are not covered — a row is real content, and
    losing one is exactly the §1516 defect.
    """
    norm = path.replace("\\", "/").lower()
    if not any(norm.endswith(p) for p in REGISTRY_PATHS):
        return False
    stripped = text.strip()
    return any(rx.match(stripped) for rx in REGISTRY_BOOKKEEPING_RES)


def is_generated_single_writer(path: str) -> bool:
    """A declared generated artifact with exactly one writer (H3073).

    Every path in `tools.generated_artifact_paths.GENERATED_SINGLE_WRITER_PATHS`
    is replaced WHOLESALE by its own `--land` caller via
    `handoff_claims.commit_texts_to_origin` — never hand-edited, never
    concurrently authored. A whole-file replacement therefore destroys no work
    regardless of how many lines it deletes, so the whole path is exempt
    rather than trying to pattern-match individual regenerated lines the way
    `is_registry_bookkeeping` does for the registry. Keyed on the DECLARATION
    in that shared module, never on "the pushing script looked automated" —
    widening this must add a path there, not loosen the check here.
    """
    norm = path.replace("\\", "/")
    return norm in GENERATED_SINGLE_WRITER_PATHS


# H4383 (08-09-2026): generalizes the FRUIT_INDEX.md single-writer exemption
# to the whole class of auto-generated, DATE-STAMPED snapshot files this org
# produces one NEW path for per day (`FRUIT_LAUNCH_STATUS_DD.MM.YY.md`,
# `tools/fruit_report.py`). `GENERATED_SINGLE_WRITER_PATHS` above is a fixed
# path SET and cannot cover a family whose filename embeds the run date — a
# hand-added static entry per day is not maintainable, so this needs a glob.
#
# Origin: two sessions regenerating the SAME day's snapshot at different
# times legitimately drop rows for handoffs that closed in between — the
# later run's file is a smaller, CORRECT re-derivation from live registry
# state, not a stale-base revert of hand-authored content — and this guard
# refused the second push (08-09-2026), forcing a manual
# `ALLOW_STALE_BASE_PUSH=1` from a real terminal for work that is, by
# construction, always safe to replace wholesale.
#
# Two gates, BOTH checked against content the push already carries or the
# remote tip already has — no intent guessed, same bar as every other
# exemption in this file (§437):
#   (a) the path's basename matches a declared snapshot-name glob
#       (`SNAPSHOT_GLOB_PREFIXES` below), and
#   (b) the file's own header AT THE REMOTE TIP (the pre-image this push
#       would delete) carries a generic "auto-generated / do not hand-edit"
#       marker — the same vocabulary `tools/dirty_tree_sweep.py`'s
#       `GENERATED_MARKERS` already checks for elsewhere in this repo
#       (`tools/fruit_report.py` stamps
#       "_Auto-generated by [tools/fruit_report.py](...) — do not hand-edit;
#       re-run to refresh._" into every snapshot it writes).
#
# Header-only detection (dropping gate a and matching ANY `.md` whose
# pre-image carries the marker) was considered and rejected: it is not
# reliably present in the SAME wording across every generator in this repo
# (`tools/build_pipeline_stats.py` stamps only
# "_Auto-generated by tools/build_pipeline_stats.py._", no "do not hand-edit"
# clause), so trusting the header alone would either miss real generated
# files or, worse, risk a false match against a hand-authored doc that
# happens to quote generator prose. The documented, auditable fallback the
# task asked for is therefore kept: a named filename-glob allowlist, widened
# by adding to the tuple — never by loosening the header check — when a
# sibling date-stamped generated family is confirmed to have the same
# single-writer, re-run-to-regenerate shape.
#
# Widened 08-09-2026 (H4412 follow-up, "widen wanted"): confirmed two more
# families whose generator scripts stamp the same "Auto-generated by ...
# do not hand-edit" header and are re-run (not hand-edited) to refresh:
#   - `ROADMAP_DRAIN_STATUS_*.md`      <- tools/roadmap_drain_report.py
#   - `HANDOFF_LIFECYCLE_METRICS_*.md` <- tools/handoff_lifecycle_metrics.py
SNAPSHOT_GLOB_PREFIXES = (
    "FRUIT_LAUNCH_STATUS_",
    "ROADMAP_DRAIN_STATUS_",
    "HANDOFF_LIFECYCLE_METRICS_",
)
GENERATED_HEADER_MARKERS = ("do not hand-edit", "Auto-generated by")


def is_generated_snapshot(remote_ref: str, path: str) -> bool:
    """A date-stamped snapshot file whose own header proves it is machine-written.

    See the `SNAPSHOT_GLOB_PREFIXES` comment above for the two-gate rationale.
    Reads the file's pre-image (its content AT THE REMOTE TIP, i.e. what this
    push would delete) rather than the pushed version, because the guard's
    question is always "does the content this push REMOVES deserve
    protection" — a pre-image that already declares itself generated answers
    that directly, and a brand-new path (no pre-image) is not this exemption's
    business (nothing to remove yet).
    """
    norm = path.replace("\\", "/")
    base = norm.rsplit("/", 1)[-1]
    if not base.endswith(".md"):
        return False
    if not any(base.startswith(p) for p in SNAPSHOT_GLOB_PREFIXES):
        return False
    try:
        pre_image = git("show", "%s:%s" % (remote_ref, path))
    except Exception:  # noqa: BLE001 -- unreadable pre-image: not this exemption's business
        return False
    if not pre_image.strip():
        return False
    return any(marker in pre_image for marker in GENERATED_HEADER_MARKERS)


def is_mint_stub(remote_ref: str, path: str) -> bool:
    """A freshly minted handoff skeleton being filled in the same pass.

    `mint_handoff.py` lands a placeholder body on origin/main, then the session that
    minted it replaces those placeholders with real content — a legitimate rewrite of
    lines that are, by construction, minutes old and authored outside the push.
    """
    if "/handoffs/" not in "/" + path.replace("\\", "/"):
        return False
    return STUB_MARKER in git("show", "%s:%s" % (remote_ref, path))


# FINDINGS §457: the live mint_handoff.py claim subjects (checked against
# origin/main history 24-08-2026) — single and batch range forms.
MINT_SUBJECT_RE = re.compile(r"^mint: claim\s+(?P<spec>H\d+(?:\.\.H\d+)?)\b")
# FINDINGS §557: the OTHER machine-generated writer of lines a close erases.
# `handoff.py claim` / `claim_handoff.py` write the queue's Active-Claims row,
# and `handoff_close.py` drops it again — a pair exactly as symmetric as
# mint→close, but with a different subject, so §457's gate 1 never matched it
# and every claim→close was routed through ALLOW_STALE_BASE_PUSH=1. Three live
# forms (handoff_claims.py:339/875, claim_handoff.py:311, all present in
# origin/main history 26-08-2026):
#     exec-claim: H#### (<repo>) claimed by <tier> (marker+ledger)
#     exec-claim: H#### CLAIMED by <tier> (marker only)
#     exec-claim: H#### (<repo>) executing (ledger mirror)
# Claims are always a SINGLE handoff — no batch-range form, deliberately, so a
# non-handoff claim subject (`exec-claim: /skill-drain slice …`) captures
# nothing and stays blocked.
CLAIM_SUBJECT_RE = re.compile(r"^exec-claim:\s+(?P<spec>H\d+)\b")
# XZE (26-10-2026): the id must start a token. Bare ``H\d+`` also matched the
# TAIL of a longer alphanumeric token, and this corpus is full of them —
# ``docs/ROADMAP_SAMSKRTE_ACQUISITION_NEW_STUDENTS_2026H2.md`` yields ``H2``.
# That bogus id became the bullet's identity anchor: `gtd_bullet_token()`
# returns the FIRST match, so a trailer-only GTD row whose body cites that
# roadmap was keyed on ``H2`` while the writer's replacement card ends with
# ``H5092``, gate 2 found no candidate, and the close died on
# STALE_BASE_GUARD_REFUSAL five times on 26-10-2026 — with no H### lost, no
# stale pre-image, and no exemption applicable (the tool's own
# `verify_row_identity` documents the trailer-only row as safe, because it
# reasons about the NEW card's first token while this guard keys on the OLD
# one). A lookbehind keeps every real id (`H5092`, `handoffs/H7279-x`,
# `refs/heads/claims/H7283.2026…`, `#H7249`) and drops only the mid-token
# fragments.
HID_RE = re.compile(r"(?<![A-Za-z0-9])H\d+")
# H5195: the claim-ledger id vocabulary — an H### handoff id OR a GTD @DO row
# id (`GTD-<line>-<slug>`, written by tools/claim_gtd_row.py). Consumed by the
# claim-release inverse exemption only; registry lanes keep plain HID_RE.
CLAIM_REF_RE = re.compile(
    r"H\d+|GTD-\d{1,5}-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
# A registry row's OWN id is its first table cell. H4569 critic round 3: 12 of
# 95 live README rows mention another H### in their text, so "any shared id"
# let closing H4000 credit a stale drop of the H9999 row that cited it.
ROW_ID_RE = re.compile(r"^\|\s*(H\d+)\s*\|")


def row_id(text: str):
    """First-cell H### of a registry table row, else None."""
    m = ROW_ID_RE.match(text.strip())
    return m.group(1) if m else None


def _expand_mint_spec(spec: str) -> set[str]:
    """`H3423` -> {H3423}; `H3428..H3431` -> every id in the inclusive range."""
    if ".." in spec:
        lo_s, hi_s = spec.split("..", 1)
        try:
            lo, hi = int(lo_s[1:]), int(hi_s[1:])
        except ValueError:
            return {spec}
        if hi < lo or hi - lo > 200:  # absurd range -> never trust it wholesale
            return set()
        return {"H%d" % n for n in range(lo, hi + 1)}
    return {spec}


_MINT_HIDS_CACHE: dict[str, frozenset[str]] = {}


def mint_subject_hids(sha: str) -> frozenset[str]:
    """H###s the commit MINTED or CLAIMED, from its subject alone.

    Empty set = neither a mint nor a claim commit. Cached: blame can hit the
    same sha for many lines of one push.

    Both writers count (FINDINGS §557). A guard that exempts a
    machine-generated write has to enumerate EVERY writer of that class: the
    untreated members are not safer, they are permanently routed through the
    manual override, which trains the override into a reflex and defeats the
    guard. Widen here by adding a subject regex, never by loosening gates 2/3
    in ``is_same_session_mint_close`` — those are what keep the H1516
    stale-pre-image class out.
    """
    if sha not in _MINT_HIDS_CACHE:
        subject = git("log", "-1", "--format=%s", sha).strip()
        m = MINT_SUBJECT_RE.match(subject) or CLAIM_SUBJECT_RE.match(subject)
        _MINT_HIDS_CACHE[sha] = frozenset(_expand_mint_spec(m.group("spec"))) \
            if m else frozenset()
    return _MINT_HIDS_CACHE[sha]


def is_same_session_mint_close(text: str, sha: str,
                               push_hids: frozenset[str],
                               path: str | None = None) -> bool:
    """The removed line is THIS handoff's own mint or claim — §457, §557.

    Measured 18-08-2026 closing H3060 minutes after minting it: the close
    rewrites the very registry row / body lines the mint commit added minutes
    earlier, so the blame hits a fresh, non-pushed commit and the guard refused
    EVERY same-session mint→close (cleared each time with ALLOW_STALE_BASE_PUSH=1;
    cb0acd668 was one). §455(b)'s mint exemption lives in the DUPLICATE-push
    guard and inspects commit SUBJECTS — two guards, two data sources, so it
    never covered this one.

    Measured again 26-08-2026 closing H3541 minutes after CLAIMING it: gates 2
    and 3 held verbatim, and only gate 1 failed, because the row erased was the
    Active-Claims row written by `handoff.py claim` (`exec-claim: H3541 …`)
    rather than by `mint_handoff.py`. Same shape, second writer — FINDINGS §557.

    Measured THIRD on 27-08-2026 closing H3587 (this file's own landing): the
    id never appears in the REMOVED LINES AT ALL, because a spec-filled-at-mint
    stub ships WITHOUT the "STUB claimed by" marker (so ``is_mint_stub`` sees a
    filled file) and its placeholder body lines carry no H### token (so gate 2's
    text scan found nothing). The fill of such a stub was therefore refused
    unless ``path`` linking below exists. ``path`` extends gate 2 narrowly:
    an id counts as named when it appears in THIS changed path's basename,
    which by construction means the file being rewritten IS the minted
    artifact — the abuse surface someone else's unrelated fresh file would
    need its name to carry a foreign minted id.

    Exempt only when ALL THREE hold, so the H1516 pre-image class cannot dress
    up as a close:
      1. the blamer commit's subject is a mint claim (`mint: claim H#### stub`,
          incl. the `H####..H####` batch form) or an exec-claim
         (`exec-claim: H#### …`, added 26-08-2026 — FINDINGS §557);
      2. the removed line — or, since the H3587 measurement, this changed
         path's basename — NAMES one of those minted H###s;
      3. THIS PUSH also names that H### somewhere (a changed path's basename or
          an added line) — i.e. we are visibly working ON that handoff, not
         reverting someone else's just-minted stub wholesale. A stale checkout
         that reinstalls pre-mint content deletes the row without touching
         anything else named H####, and stays blocked.
    """
    minted = mint_subject_hids(sha)
    if not minted:
        return False
    named = set(HID_RE.findall(text))
    if path:
        named |= set(HID_RE.findall(os.path.basename(path)))
    return bool(named & minted & push_hids)


# Claim→release (15-09-2026, H4527). `handoff.py release H#### --commit` lands
# under exactly this subject (tools/handoff.py cmd_release); a trailing
# "+ session-end note" etc. still matches. Hand-worded release subjects
# ("release H#### stale exec-claim …") deliberately do NOT — they stay on the
# ordinary path, so the forgeable surface is one machine-written shape.
RELEASE_SUBJECT_RE = re.compile(
    r"^release\s+(?P<hid>H\d+|GTD-\d{1,5}-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s+claim\b")
CLAIM_LEDGER_BASENAME = "NEXT_TASK_QUEUE.md"
# H5195: GTD @DO claims (`GTD-<line>-<slug>`) live in the same ledger and their
# releases are the same inverse; the id fragment above is the single vocabulary
# for both shapes. Registry lanes keep their own HID_RE/ROW_ID_RE untouched.
_CLAIM_ROW_ID_RE = re.compile(
    r"^\|\s*(H\d+|GTD-\d{1,5}-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s*\|")


def claim_row_id(text: str):
    """First-cell claim id of an Active-Claims ledger row (H### or GTD-…)."""
    m = _CLAIM_ROW_ID_RE.match(text.strip())
    return m.group(1) if m else None
_CLAIM_HID_CACHE: dict[str, str | None] = {}


def claim_subject_hid(sha: str) -> str | None:
    """The H### an ``exec-claim:`` commit claimed, else None (mint excluded)."""
    if sha not in _CLAIM_HID_CACHE:
        m = CLAIM_SUBJECT_RE.match(git("log", "-1", "--format=%s", sha).strip())
        _CLAIM_HID_CACHE[sha] = m.group("spec") if m else None
    return _CLAIM_HID_CACHE[sha]


_RELEASE_BLAMER_HID_CACHE: dict[str, frozenset[str]] = {}


def release_blamer_hids(sha: str) -> frozenset[str]:
    """H### ids the blaming commit's subject names, in any form (H4945).

    Widens gate 2 of ``is_claim_release_inverse`` from "subject IS an
    ``exec-claim: H####`` commit" to "subject NAMES this H### anywhere".
    ``claim_subject_hid`` (the strict ``exec-claim:``-only reader) is kept
    unchanged beside this function — it is pinned by its own test as a
    regression guard on ``CLAIM_SUBJECT_RE``, though nothing in this module
    calls it any more; the shared §457/§557 same-session mint-close path
    reads ``CLAIM_SUBJECT_RE`` directly via ``mint_subject_hids``, and that
    path is untouched by this change. A legitimate rewrite of a claim row —
    MG restoring a wrongly-cleared row, a dedupe pass, a reformat — changes
    the row's blamer to a commit subject that no longer matches
    ``CLAIM_SUBJECT_RE`` even though the row content and its own id are
    unchanged (measured 16-09-2026 closing H4926: blamer subject "restore
    the live H4926 Mac claim row dropped by ..."). Gates 1 and 3 of
    ``is_claim_release_inverse`` already confine credit to one row of the
    claim ledger whose OWN id equals the id THIS push releases, so widening
    this gate cannot credit a foreign row or a bulk queue tidy — the
    unrelated-subject and wrong-id negative controls in
    ``tools/test_pre_push_stale_base_check.py`` cases 15f/15g prove it.
    """
    if sha not in _RELEASE_BLAMER_HID_CACHE:
        subject = git("log", "-1", "--format=%s", sha).strip()
        _RELEASE_BLAMER_HID_CACHE[sha] = frozenset(
            CLAIM_REF_RE.findall(subject))
    return _RELEASE_BLAMER_HID_CACHE[sha]


def release_subject_hids(remote_ref: str, local_ref: str) -> frozenset[str]:
    """H###s whose claim a commit in THIS push releases, by subject."""
    out = git("log", "--format=%s", "%s..%s" % (remote_ref, local_ref))
    return frozenset(m.group("hid") for m in
                     (RELEASE_SUBJECT_RE.match(s.strip())
                      for s in out.splitlines()) if m)


def is_claim_release_inverse(path: str, text: str, sha: str,
                             release_hids: frozenset[str]) -> bool:
    """The removed line is an Active-Claims row this push RELEASES (H4527).

    ``is_same_session_mint_close`` gate 3 wants the push to name the H###
    in a changed path or an added line. A release on a handoff whose body
    carries no 🔒 CLAIMED banner only DELETES the queue row (reconcile_banner
    changes nothing), so gate 3 fails by construction and every such release
    was refused. A release is the claim's own inverse; all four gates below
    are content-checkable, and together they are narrower than §457:

      1. the path is the claim ledger (``NEXT_TASK_QUEUE.md`` by basename);
      2. the blamer's subject NAMES the claimed H### in any form (H4945;
         was: the blamer IS an ``exec-claim: H####`` commit) — the mint
         writer is still excluded because gate 1 already confines this to
         a file the mint writer never touches;
      3. the removed row's OWN id (first table cell; H### or, since H5195,
         a `GTD-<line>-<slug>` GTD claim id) is that claimed id — a row that
         merely cites the id elsewhere does not
         credit (the H4569 round-3 lesson);
      4. a commit in THIS push is subjected ``release <that id> claim``.

    H1516 safety: a stale checkout that reinstalls a pre-claim copy carries
    no release subject and stays blocked; a release subject never exempts
    any line other than that id's own claim-ledger row, which is exactly
    what a release is meant to delete. Residual: two live claims on one id
    would both drop — ``claim_handoff.py`` already refuses a second claim.
    Gate 2 widening (H4945): a restored/reworded row's blamer no longer
    matches ``exec-claim:``, but gates 1+3 already require the row to be
    THIS id's own ledger row and gate 4 requires THIS push to release THIS
    id — so a blamer subject naming a different id, or a subject naming no
    id at all, still fails to credit.
    """
    if not release_hids:
        return False
    if posix_basename(path) != CLAIM_LEDGER_BASENAME:
        return False
    rid = claim_row_id(text)
    return (rid is not None and rid in release_hids
            and rid in release_blamer_hids(sha))


# GTD 0x (H4265 close incident, 06-09-2026): the ONE provenance signal shared by
# every handoff-lane writer — mint, exec-claim, fanout-fill and close subjects
# all carry their H### ids. ``mint_subject_hids`` above only admits the two
# machine writers; this cache admits ANY subject naming a handoff id, and is
# consumed ONLY by ``is_same_lane_close_prep``, whose verdict downgrades the
# block to a loud warning instead of exempting silently.
_SUBJECT_HIDS_CACHE: dict[str, frozenset[str]] = {}


def subject_hids(sha: str) -> frozenset[str]:
    """Every H### named in the commit's subject — the lane marker, any writer."""
    if sha not in _SUBJECT_HIDS_CACHE:
        subject = git("log", "-1", "--format=%s", sha).strip()
        _SUBJECT_HIDS_CACHE[sha] = frozenset(HID_RE.findall(subject))
    return _SUBJECT_HIDS_CACHE[sha]


def is_same_lane_close_prep(path: str, sha: str,
                            push_hids: frozenset[str]) -> bool:
    """Class (10): the removed line is a handoff file's own close-prep work.

    All three gates are content-checkable (the §437 bar — no intent guessed):

      1. the changed path IS a handoff file whose BASENAME names an H###
         (``handoffs/H4265-*.md``, active or ``handoffs/archive/``). Registry,
         GTD, FINDINGS and every other path never satisfy this gate and keep
         the hard block;
      2. the blaming commit's subject names that SAME H### (8b5fbda named
         H4265 in "… H4261–H4265 S1–S5 …"; close commits name theirs in
         "docs: close H4265 — …"). A subject naming no handoff id fails here
         and the line stays a hard block (case 20b);
      3. THIS PUSH visibly works on that same H### (a changed path's basename
         or an added line names it) — the close/fill/re-open shape, not a
         drive-by edit of an unrelated file.

    NOT a silent exemption: the caller collects these into the warned bucket,
    prints every line under ``stale-base guard: WARNING`` and ALLOWS the push
    (MG 06-09-2026: «Флип разрешить»). A stale checkout reverting another
    session's lines inside the same handoff file also warns instead of
    blocking — that is the accepted cost, bounded to the one file whose name
    carries the id, and the reason the class is a warning, never a ``continue``
    toward silence.
    """
    norm = path.replace("\\", "/")
    if "/handoffs/" not in "/%s" % norm:
        return False
    m = HID_RE.search(posix_basename(norm))
    if not m:
        return False
    hid = m.group(0)
    return hid in subject_hids(sha) and hid in push_hids


# FINDINGS §720 (H4437, 09-09-2026): one-line-per-subject hub tables make EVERY
# in-place row update a whole-line rewrite, and a whole-line rewrite diffs as
# `- old` / `+ new` — indistinguishable from a deletion. Measured on GTD row
# 0ae: commit 66c7c591e rewrote it 39 minutes after 2fc34b758 minted it and the
# guard refused the rewrite as a revert; class 5's near match correctly
# declined (the instruction text changed wholesale, ratio ~0.6 < NEAR_RATIO),
# and §720's own advice ("insert a new line instead of extending theirs") does
# not exist for keyed tables — the row id IS the identity, the update IS a
# rewrite. The exemption is deliberately narrower than §457/class-10, all four
# gates content-checkable (the §437 bar):
#   1. the path is a DECLARED hub table (exact basename) — everywhere else the
#      hard block stands untouched;
#   2. the removed line and some same-push added line share the ROW TOKEN
#      (first table cell) — a rewrite, not an unrelated addition;
#   3. identity survives: every H### the removed line names the replacement
#      names too, OR they share a contiguous ≥ VERBATIM_FRAGMENT_MIN verbatim
#      fragment — a token reused by a different task does not credit;
#   4. gate (b), the #1516 load-bearing half: the replacement text is ABSENT
#      from the blaming commit's pre-image. A stale pre-image reinstall
#      re-adds text that existed before their edit and still blocks; a genuine
#      forward rewrite writes text that did not exist and passes. None
#      (unknowable pre-image) conservatively blocks.
# Never silent: every credit prints under ROW_REWRITE_MARKER below, mirroring
# the class-10 discipline (listed, loud, verifiable after the fact).
ROW_REWRITE_PATHS = frozenset({"GTD_NEXT_ACTIONS.md", "NEXT_TASK_QUEUE.md"})
ROW_REWRITE_MARKER = "STALE_BASE_ROW_REWRITE_ALLOWED"
ROW_TOKEN_RE = re.compile(r"^\|\s*([0-9A-Za-z]{1,6})\s*\|")


def row_token(line: str) -> str | None:
    """First table cell of a hub row, else None (blank/separator/header fail)."""
    text = line.strip()
    if not text.startswith("|"):
        return None
    m = ROW_TOKEN_RE.match(text)
    return m.group(1) if m else None


def row_identity_preserved(old_line: str, new_line: str) -> bool:
    """Gate 3: the rewrite keeps the row's identity (H###s or a long fragment)."""
    old_hids = set(HID_RE.findall(old_line))
    new_hids = set(HID_RE.findall(new_line))
    if old_hids and old_hids <= new_hids:
        return True
    # H4586: a shared blob-URL prefix is not identity
    return has_verbatim_fragment(_mask_link_boilerplate(old_line),
                                 (_mask_link_boilerplate(new_line),))


# H5052 (16-09-2026, FINDINGS §785): the §720/H4437/H4455/H4600 credits exist to
# permit FORWARD lifecycle edits (open -> DONE, a re-date, a re-scope). They were
# keyed only on identity (row token / H### / verbatim fragment), never on the
# DIRECTION of the edit — so a rewrite that strips a terminal marker back to the
# open form rode the same credit. That is the exact shape of the reverted H4932
# strike inside 8768072fda (a struck `~~…~~ **DONE 16-09-2026 (H4932)**` row
# reverted to its older un-struck text carries the same row token), measured as
# one of the ways that degenerate commit's GTD wipe reached main. A credit may
# therefore NOT regress a terminal row to open: the line stays uncredited, the
# push blocks with the standard listing, and ALLOW_STALE_BASE_PUSH=1 remains the
# deliberate, loud override.
TERMINAL_STATE_RE = re.compile(r"✅|\bDONE\b|\bRESOLVED\b|\bARCHIVED\b|~~")


def state_regression(old_line: str, new_line: str) -> bool:
    """True when a rewrite removes the terminal marker a line carried (H5052).

    Forward (credited): open -> open (edit), open -> terminal (lifecycle flip),
    terminal -> terminal (re-date, extra ✅). Backward (refused): anything where
    the old line was terminal and the new one is not — DONE -> open, unstriking.
    """
    return (bool(TERMINAL_STATE_RE.search(old_line))
            and not TERMINAL_STATE_RE.search(new_line))


# H4614 (13-09-2026): gate (b) was BYTE-IDENTITY (`cand in pre`), so a stale
# reinstall of OLD row content perturbed trivially (a date-bump, one word) was
# not byte-present in the pre-image and every rewrite credit (H4437 row,
# H4455 fragment, H4498 hunk, H4600 bullet) CREDITED it as a forward edit —
# measured red before this change: a 2-char-perturbed GTD 0ae v1 landed over a
# colleague's fresh v2 under STALE_BASE_ROW_REWRITE_ALLOWED, on both the row
# and the H4600 bullet path. Hardening: when the replacement is a NEAR match
# (>= NEAR_RATIO, with the same real_quick_ratio/quick_ratio upper-bound
# prescreens best_near_match uses) of an IDENTITY-ANCHORED pre-image line —
# one sharing the candidate's row token or first H### — the "new" text is the
# old text plus cosmetic noise and the push is still a reinstall. A genuine
# forward rewrite contains the colleague's fresh edit and is FAR from the
# parent pre-image (case 28's measured ~0.6). Unanchored candidates keep
# exact-only semantics — the residual class-5 bypass then loses only a
# near-match-sized edit, an accepted limit. Accepted trade, stated rather
# than hidden: a genuine surgical extension on top of a SMALL colleague edit
# is also near the pre-image and now blocks loudly (override available) —
# the guard's designed trade of a visible cheap false positive against a
# silent expensive revert (case 33c pins it). Conservative block, never
# silent.
STALE_REINSTALL_NEAR_CAP = 50  # anchored pre-image lines compared per candidate


def _identity_anchor(line: str) -> tuple[str | None, str | None]:
    """(row token, first H###) of a line — the anchors a keyed rewrite keeps
    (H4437 gate 2 / H4600 gate 2 keys)."""
    m = HID_RE.search(line)
    return row_token(line), (m.group(0) if m else None)


def _near_anchored_preinstall(cand: str, pre: set[str]) -> bool:
    """H4614: is `cand` a NEAR match of an identity-ANCHORED pre-image line?
    Unanchored lines never match (exact-only semantics preserved); the
    real_quick_ratio/quick_ratio prescreens are upper bounds on ratio(), so a
    true >= NEAR_RATIO match can never be screened away; the cap bounds a
    pathological pre-image at 50 anchored comparisons (best_near_match's
    budget discipline)."""
    tok, hid = _identity_anchor(cand)
    if not tok and not hid:
        return False
    tlen = len(cand)
    slack = max(8, int(0.35 * tlen))
    compared = 0
    for old in pre:
        otok, ohid = _identity_anchor(old)
        if not ((tok and tok == otok) or (hid and hid == ohid)):
            continue
        compared += 1
        if compared > STALE_REINSTALL_NEAR_CAP:
            break
        if abs(len(old) - tlen) > slack:
            continue
        sm = difflib.SequenceMatcher(None, cand, old)
        if sm.real_quick_ratio() < NEAR_RATIO or sm.quick_ratio() < NEAR_RATIO:
            continue
        if sm.ratio() >= NEAR_RATIO:
            return True
    return False


def _forward_edit_ok(remote_ref: str, path: str, sha: str, cand: str,
                     pre_cache: dict) -> bool | None:
    """Gate (b), the #1516 load-bearing half, shared by both credit paths:
    True when the replacement text is ABSENT from the blaming commit's
    pre-image (a genuine forward rewrite), None when the pre-image is
    unknowable or the text re-installs the pre-image (conservative block)."""
    key = (sha, path)
    if key not in pre_cache:
        if sha == _creation_sha(remote_ref, path):
            # §458: the blamer is the file's BIRTH commit — nothing existed
            # before it, so the replacement is forward by definition.
            pre_cache[key] = set()
        else:
            pre_cache[key] = pre_image_lines(sha, path)
    pre = pre_cache[key]
    if pre is None:
        # Unknowable pre-image: cannot prove forward edit — keep blocking.
        return None
    if cand in pre:
        # The replacement text existed BEFORE their edit: this push is
        # re-installing the pre-image — the #1516 class. Still a hit.
        return None
    if _near_anchored_preinstall(cand, pre):
        # H4614: the replacement is the pre-image with cosmetic noise — a
        # perturbed stale reinstall, not a forward edit. Conservative block.
        return None
    return True


def fragment_rewrite_credit(remote_ref: str, path: str, sha: str, old_line: str,
                            added_lines: list[str],
                            pre_cache: dict) -> str | None:
    """H4455 (MG ruling 09-09-2026, option (b)): the H4437 row-rewrite credit
    extended beyond the declared hub tables. A removed line in ANY file is
    credited as a same-push REWRITE — not a deletion — when some same-push
    added line in the SAME file shares a contiguous >= VERBATIM_FRAGMENT_MIN
    verbatim fragment with it (H4437's identity rule, gate 3) and the
    replacement passes gate (b) — absent from the blaming commit's pre-image.
    Returns the credited fragment length label or None. Loud via ROW_REWRITE_MARKER.

    H4586 (critic F1): the fragment is taken with the shared blob-URL /
    ``handoffs/`` boilerplate masked out, and a handoff-registry row (README or
    archive half) is only rewritten by a same-push row of the SAME first-cell
    id that keeps its title/slug cell (``row_text_relocated``) — otherwise a
    stale close that also mints any row credited the colleague's retitled row
    through the 53-char link prefix and the shared status boilerplate."""
    keyed = row_id(old_line) if is_registry_path(path) else None
    masked_old = _mask_link_boilerplate(old_line)
    for cand in added_lines:
        if cand == old_line:
            # A pure reinstall of the SAME text is survivors-territory, not a
            # rewrite; and gate (b) would block it anyway. Skip cheaply.
            continue
        if state_regression(old_line, cand):
            continue  # H5052: a credit never regresses a terminal line to open
        if keyed:
            if row_id(cand) != keyed or not row_text_relocated(old_line, (cand,)):
                continue
        elif not has_verbatim_fragment(masked_old,
                                       (_mask_link_boilerplate(cand),)):
            continue
        if _forward_edit_ok(remote_ref, path, sha, cand, pre_cache) is True:
            return "verbatim>=%d" % VERBATIM_FRAGMENT_MIN
    return None


def row_rewrite_token(remote_ref: str, path: str, sha: str, old_line: str,
                      added_rows: dict[str, list[str]],
                      pre_cache: dict) -> str | None:
    """Gate 2+3+4 for one removed row: its token when the rewrite is a forward
    edit, else None. `added_rows` maps row token -> stripped same-push added
    lines for this path; `pre_cache` is blame_recent's shared pre-image cache."""
    tok = row_token(old_line)
    if not tok:
        return None
    for cand in added_rows.get(tok, ()):
        if not row_identity_preserved(old_line, cand):
            continue
        if state_regression(old_line, cand):
            continue  # H5052: a credit never regresses a terminal row to open
        if _forward_edit_ok(remote_ref, path, sha, cand, pre_cache) is True:
            return tok
    return None


# H4600 (12-09-2026): the §720 credit's dash-bullet twin for the GTD
# lifecycle. GTD_NEXT_ACTIONS.md rows are DASH bullets, not table rows, so
# ``row_token()`` never fires on them; and a lifecycle flip (`@DO` -> DONE)
# rewrites the bullet wholesale — it keeps the subject + H### ids but shares
# NO >=40-char verbatim fragment (H4455 declines; class 11 declines too: a
# ~400-char bullet keeps far under SHORT_REWRITE_MIN_SHARE of itself). The
# measured 12-09 repro: the Close-H4584 flip only passed because its text
# happened to carry a 51-char commit URL — the fragment-less twin still
# refused (line-1272 shape, blamer 8a7aba9ed). Same four gates, re-keyed on
# the bullet's OWN identity anchor (the H### id, per §720's "the row id IS
# the identity, the update IS a rewrite"):
#   1. the path is the DECLARED GTD bullet hub (exact basename) — everywhere
#      else the hard block stands untouched;
#   2. the removed bullet and some same-push added bullet share the bullet's
#      OWN identity anchor — the mint trailer's row id (`row `XYZ``) when the
#      bullet carries one, else the FIRST H### (H7295: the writer's trailer id
#      is shared by every minted card and must never pair two rows);
#   3. ``row_identity_preserved``: every H### the removed bullet names the
#      replacement names too (or a >= VERBATIM_FRAGMENT_MIN verbatim
#      fragment) — a token reused by a different task does not credit;
#   4. gate (b), the #1516 load-bearing half: the replacement text is ABSENT
#      from the blaming commit's pre-image — a stale reinstall still blocks.
# Never silent: credited through ``row_credits``, printed under
# ROW_REWRITE_MARKER like both twins.
GTD_BULLET_PATHS = frozenset({"GTD_NEXT_ACTIONS.md"})

# GTD XY0 (26-10-2026): every minted row ends with the writer's provenance
# trailer `(minted DD-MM-YYYY, row `XYZ` via gtd_mint_row/H5092)` — that H### is
# the WRITER's handoff id, not the row's. Gate 2 keyed the credit on the
# bullet's FIRST H### only, so a card whose body opens by naming the trailer id
# in prose (the `XY0` card literally discusses `(H5092)`) could never be
# credited on its real identity: closing it was refused with
# STALE_BASE_GUARD_REFUSAL while the writer had built a replacement that keeps
# every id the bullet names (H5092 + H5851). The body-id fallback still
# applies to UNMINTED bullets; for minted ones H7295 (below) supersedes it by
# anchoring on the trailer's row id, which is the same identity done exactly.
MINT_TRAILER_RE = re.compile(
    r"\([^()]*row\s+`[^`\n]+`\s+via\s+gtd_mint_row/H\d+\)")
# H7295 (26-10-2026, reports/XZK_SECOND_PUSH_PROOF_2026-10-26.md, card XZK):
# the trailer's `row `XYZ`` id is the ROW's identity; the `H###` beside it is
# the WRITER's. Every card minted by gtd_mint_row.py shares the same writer id
# inside that trailer, so keying gate 2 on the first H### meant one minted
# close could credit the deletion of ANY other minted row: measured through
# the real hook, a push that dropped rival card `ZQ1` and added a close of
# `ZQ2` was credited (both first H###s were `H5092`, `found = 0`), and only the
# row-id-keyed gtd-row-disappearance gate — which has a documented override —
# stopped it. The anchor below is the row id, and the writer trailer can never
# be the credit anchor for a minted bullet.
MINT_ROW_ID_RE = re.compile(
    r"row\s+`([^`\n]+)`\s+via\s+gtd_mint_row/H\d+")


def gtd_bullet_row_id(line: str) -> str | None:
    """The `XYZ` of a GTD bullet's mint trailer (`row `XYZ``), else None.

    A bullet without the writer trailer has no row id: its identity stays the
    first H### (`gtd_bullet_token`), which is then the row's own handoff id.
    """
    text = line.strip()
    if not text.startswith("-"):
        return None
    m = MINT_ROW_ID_RE.search(text)
    return m.group(1).strip() if m else None


def gtd_bullet_token(line: str) -> str | None:
    """First H### of a GTD dash bullet, else None (non-bullet / id-less fail —
    a bullet that names no handoff id has no identity anchor to credit)."""
    text = line.strip()
    if not text.startswith("-"):
        return None
    m = HID_RE.search(text)
    return m.group(0) if m else None


def gtd_bullet_body_ids(line: str) -> set[str]:
    """The H###s a GTD bullet names OUTSIDE its mint trailer(s).

    The trailer's id is the writer's provenance (`gtd_bullet_token` may return
    exactly it for a trailer-only stub); these are the ids the row is actually
    about. GTD `XY0` is the shape that needs the distinction — its body names
    both the tool id (in prose) and the handoff it exists to discuss."""
    text = line.strip()
    if not text.startswith("-"):
        return set()
    return set(HID_RE.findall(MINT_TRAILER_RE.sub("", text)))


def bullet_rewrite_token(remote_ref: str, path: str, sha: str, old_line: str,
                         added_bullets: dict[str, list[str]],
                         added_bullet_rows: dict[str, list[str]],
                         pre_cache: dict) -> str | None:
    """H4600: gates 2+3+4 for one removed GTD dash bullet — its token when the
    same-push rewrite is a forward edit, else None. `added_bullets` maps the
    first-H### token -> stripped same-push added bullet lines for this path;
    `added_bullet_rows` maps the mint trailer's row id -> the same lines;
    `pre_cache` is blame_recent's shared pre-image cache.

    H7295: a MINTED bullet (one carrying the `row `XYZ` via gtd_mint_row/H### `
    trailer) is keyed on its own row id ONLY. Every minted card carries the
    same writer id, so the first-H### bucket — and the body-id widening that
    papered over it (GTD XY0) — let a close of one row credit the deletion of
    another. The replacement must name the SAME row id; the writer trailer is
    never a credit anchor. Unminted bullets keep the first-H### path, widened
    to a shared BODY id when the body names handoffs (XY0's original shape).

    The returned token is the identity the credit actually keyed on — the row
    id for a minted pair — so the loud marker names the row rather than the
    writer."""
    row_id = gtd_bullet_row_id(old_line)
    tok = gtd_bullet_token(old_line)
    body_ids = gtd_bullet_body_ids(old_line)
    if row_id:
        cands = list((added_bullet_rows or {}).get(row_id, ()))
        if not cands:
            return None
    else:
        if not tok:
            return None
        cands = list(added_bullets.get(tok, ()))
        if body_ids:
            # Non-minted bullet: the first-H### key is its own id, but a body
            # that names other handoffs still pairs on a shared body id.
            seen = set(cands)
            for bucket in added_bullets.values():
                for cand in bucket:
                    if cand not in seen and body_ids & gtd_bullet_body_ids(cand):
                        seen.add(cand)
                        cands.append(cand)
    for cand in cands:
        if row_id and gtd_bullet_row_id(cand) != row_id:
            # H7295 gate 2 for minted rows: same row id or no credit. A
            # cross-row close shares only the writer's trailer id — refused.
            continue
        if not row_identity_preserved(old_line, cand):
            continue
        if state_regression(old_line, cand):
            continue  # H5052: a credit never regresses a terminal bullet to open
        if _forward_edit_ok(remote_ref, path, sha, cand, pre_cache) is True:
            if row_id:
                return row_id
            shared = sorted(body_ids & gtd_bullet_body_ids(cand))
            return shared[0] if shared else tok
    return None


def blame_recent(remote_ref: str, path: str, lines: list[int],
                 cutoff: datetime, ours: set[str],
                 survivors: set[str],
                 pre_cache: dict | None = None,
                 push_hids: frozenset[str] = frozenset(),
                 blame: dict[int, list] | None = None,
                 near_budget: list[int] | None = None,
                 lane_warns: list[dict] | None = None,
                 added_rows: dict[str, list[str]] | None = None,
                 added_bullets: dict[str, list[str]] | None = None,
                 added_bullet_rows: dict[str, list[str]] | None = None,
                 row_credits: list[dict] | None = None,
                 added_lines: list[str] | None = None,
                 hunk_adds: dict[int, list[str]] | None = None,
                 near_survivors: set[str] | None = None,
                 release_hids: frozenset[str] = frozenset(),
                 ) -> tuple[list[tuple[int, str, str]], list[dict], bool]:
    """(hits, modifications, overflow) for removed lines added recently by
    someone else.

    ``hits`` are true losses — block. ``modifications`` are class-5 forward edits
    (near-match replacement whose text never existed before the blamed commit) —
    exempt with a note. ``lane_warns``, when given, collects class-10 same-lane
    close-prep lines: they do NOT block; the caller reports them as a loud
    warning and allows the push (GTD 0x, MG «Флип разрешить» 06-09-2026).
    ``added_rows`` + ``row_credits`` carry the §720 (H4437) row-rewrite
    exemption for declared hub tables: a credited row lands in ``row_credits``
    and never reaches ``hits``. ``blame`` is the batched per-path map from
    ``blame_map``; ``near_budget`` is a one-element mutable counter shared
    across the path's class-5 comparisons. ``overflow`` is True when that
    budget ran out mid-path — the caller turns the path into an explicit
    uncheckable verdict (§543/§605) rather than silently skipping the rest or
    grinding on for hours.
    """
    hits: list[tuple[int, str, str]] = []
    mods: list[dict] = []
    overflow = False
    if row_credits is None:
        row_credits = []
    old_text = blob_lines(remote_ref, path)
    if pre_cache is None:
        pre_cache = {}
    if blame is None:
        blame = blame_map(remote_ref, path)
    if near_budget is None:
        near_budget = [DEFAULT_MAX_NEAR_PAIRS]
    for ln in lines:
        info = blame.get(ln)
        if info is None:
            continue
        sha, author, when = info[0], info[1], info[2]
        # Moved, not lost: the same text is still somewhere in the pushed file —
        # either verbatim, or with its handoff link repointed to archive/ (class 3).
        stripped = ""
        # H4639: one per-line context feeds both rule evaluators below — the
        # line-exemption table (_LINE_EXEMPTION_RULES) and the credit/gate
        # rule table (_CREDIT_RULES). Both tables and _apply_rules are declared
        # below, after their predicate helpers; module globals are late-bound.
        ctx = _RuleCtx(remote_ref=remote_ref, path=path, ln=ln, sha=sha,
                       author=author, when=when, cutoff=cutoff,
                       stripped=stripped, survivors=survivors,
                       near_survivors=near_survivors, near_budget=near_budget,
                       pre_cache=pre_cache, push_hids=push_hids,
                       added_rows=added_rows, added_bullets=added_bullets,
                       added_bullet_rows=added_bullet_rows,
                       added_lines=added_lines, hunk_adds=hunk_adds,
                       lane_warns=lane_warns, release_hids=release_hids)
        if 1 <= ln <= len(old_text):
            stripped = old_text[ln - 1].strip()
            ctx.stripped = stripped
            # A removed BLANK line carries no authored content, so there is
            # nothing for the H1516 revert class to destroy. Everywhere below,
            # an empty ``stripped`` already disables every exemption AND the
            # class-5 near-match, so such a line fell straight through to the
            # recency test and blocked on its own — a pure false positive.
            # Measured (§659): after the queue exemption landed, the ONE line
            # still refusing the v0.195.419 cut was the blank between a
            # fragment's ``### Added`` header and its bullet.
            if not stripped:
                continue
            # H4639: the content exemptions ride _LINE_EXEMPTION_RULES — the
            # exact-equality "moved, not lost" credit (the consumer end of the
            # data-driven survivor sources: H4569 shard rotation, H4569-r4
            # close-into-shard, H4595 close-rotation integration, §530
            # sibling-archive moves, H4586's archive_normalized repoint arm)
            # and its derived-content kin — in the same order the inline
            # chain ran. Overflow is unpacked (not discarded) so a future
            # budgeted exemption predicate aborts loudly instead of
            # silently exempting — the §543/§605 contract (H4639 critic).
            consumed, ovf = _apply_rules(ctx, _LINE_EXEMPTION_RULES,
                                         row_credits, mods)
            if ovf:
                overflow = True
                break
            if consumed:
                continue
        if sha in ours:
            continue
        # H4639: the per-line credit/gate chain rides _CREDIT_RULES — one
        # declared entry per credit (H4437 row, H4600 bullet, H4455 fragment,
        # §457 mint-close, class-10 warn, class-5 near-match, H4498 hunk);
        # first match consumes the line, order exactly as the inline chain
        # ran. Terminal default below: the recency-windowed hit.
        consumed, ovf = _apply_rules(ctx, _CREDIT_RULES, row_credits, mods)
        if ovf:
            overflow = True
            break
        if consumed:
            continue
        if when is not None and when >= cutoff:
            hits.append((ln, sha[:9], author))
    return hits, mods, overflow


NEAR_RATIO = 0.85

def _creation_sha(remote_ref: str, path: str) -> str | None:
    """The commit that added `path` (its birth), as of the remote tip."""
    out = git("log", "--format=%H", "--diff-filter=A", "-1",
              remote_ref, "--", path)
    return out.strip() or None


def best_near_match(text: str, survivors: set[str],
                    budget: list[int] | None = None,
                    ties_out: list[str] | None = None,
                    ) -> tuple[tuple[str, float] | None, bool]:
    """Closest pushed-survivor line to `text` above NEAR_RATIO, else None.

    Second return value is the §543/§605 overflow flag: True when the shared
    per-path comparison budget (`budget[0]`, one-element mutable counter) ran
    out before every candidate was examined — the caller must NOT treat that as
    "no near-match" and block, because an unfinished exemption search is an
    UNANSWERED question, not a negative one. quick_ratio prescreens are sound
    here: both are upper bounds on ratio(), so a true ≥ NEAR_RATIO match can
    never be screened away.

    `ties_out`, when given, is filled with EVERY candidate tied at the winning
    ratio, best first-seen order preserved. FINDINGS §697 addendum: `survivors`
    is a set, so which of several equally-good candidates `best` happens to be
    is iteration-order luck — and Class 5's gate (b) then asks its question of
    that arbitrary winner. Measured on FINDINGS.md, whose convention is a
    serially-numbered trailer line (`§NNN takes the next number.`) that the file
    also QUOTES in its own body: deleting `§695 takes the next number.` scores
    0.96296 against both the real successor `§697 takes the next number.` (a
    genuine forward edit, absent from the pre-image) and the long-dead quoted
    `§689 takes the next number.` (present in the pre-image). Whenever the
    stale twin won the tie, every future append to that file was refused. The
    caller resolves the tie on the pre-image instead of here, so the gate keeps
    asking "did ANY equally-good replacement text not exist before their edit?"
    — which is the question Class 5 was always meant to ask.
    """
    best: tuple[str, float] | None = None
    ties: list[str] = []
    overflow = False
    tlen = len(text)
    slack = max(8, int(0.35 * tlen))
    for cand in survivors:
        if budget is not None:
            if budget[0] <= 0:
                if ties_out is not None:
                    ties_out[:] = ties
                return best, True
            budget[0] -= 1
        if abs(len(cand) - tlen) > slack:
            continue
        sm = difflib.SequenceMatcher(None, text, cand)
        if sm.real_quick_ratio() < NEAR_RATIO or sm.quick_ratio() < NEAR_RATIO:
            continue
        r = sm.ratio()
        if r < NEAR_RATIO:
            continue
        if best is None or r > best[1]:
            best = (cand, r)
            ties = [cand]
        elif r == best[1]:
            ties.append(cand)
    if ties_out is not None:
        ties_out[:] = ties
    return best, overflow


def pre_image_lines(sha: str, path: str) -> set[str] | None:
    """Stripped non-blank lines of `path` as of the blamed commit's PARENT.

    None means unknowable here (no parent, no blob at that revision) — callers
    treat None as 'cannot prove this is a forward edit' and keep blocking."""
    out = git("show", "%s~1:%s" % (sha, path))
    if not out.strip():
        return None
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def added_line_texts(remote_ref: str, local_ref: str, path: str) -> list[str]:
    """Stripped non-empty ADDED (+) lines of this push for `path`."""
    out = git("diff", "-w", "-U0", remote_ref, local_ref, "--", path)
    texts: list[str] = []
    for line in out.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            t = line[1:].strip()
            if t:
                texts.append(t)
    return texts


def net_added_line_texts(remote_ref: str, local_ref: str,
                         *paths: str) -> list[str]:
    """ADDED lines across `paths` (git pathspecs) that this push does not also
    REMOVE somewhere under the same pathspecs — rows that are new to the set,
    not rows moved between its files (H4569: a registry shard rotation)."""
    added, removed = diff_line_texts(remote_ref, local_ref, *paths)
    return [t for t in added if t not in removed]


def diff_line_texts(remote_ref: str, local_ref: str,
                    *paths: str) -> tuple[list[str], set[str]]:
    """(added, removed) stripped content lines of this push under `paths`."""
    out = git("diff", "-w", "-U0", remote_ref, local_ref, "--", *paths)
    added: list[str] = []
    removed: set[str] = set()
    in_hunk = False  # a content line may itself begin "---"/"+++"
    for line in out.splitlines():
        if line.startswith("diff --git "):
            in_hunk = False
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        t = line[1:].strip()
        if not t:
            continue
        if line.startswith("+"):
            added.append(t)
        elif line.startswith("-"):
            removed.add(t)
    return added, removed


def fresh_archive_rows(remote_ref: str, local_ref: str, paths,
                       live_path: str) -> list[str]:
    """Net-added archive-half lines that can credit a removed `live_path` row:
    same H### as a row this push removes, and text NEW to the archive.

    H4569 critic: a stale tree that reverts a colleague's REOPEN drops the
    fresh README row and puts the old archived row back byte-identical —
    net-added, same id, >40 chars verbatim, so it would pass as a close. A
    real close always writes new text (status, date, summary cells). So a
    line the archive half EVER held on ``remote_ref`` (the pickaxe sees it
    enter or leave) credits nothing. Full history, not a time window: the
    reopen may be weeks older than the README edit the guard protects
    (critic round 2). Only same-id candidates are searched — usually one per
    close — so a wholesale shard rewrite costs no searches at all."""
    removed_ids: set[str] = set()
    # callers may hand the case-folded dispatch key; pathspecs are case-exact
    out = git("diff", "-w", "-U0", remote_ref, local_ref, "--",
              ":(icase)" + live_path)
    for line in out.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            rid = row_id(line[1:])
            if rid:
                removed_ids.add(rid)
    fresh = []
    for t in net_added_line_texts(remote_ref, local_ref, *paths):
        if row_id(t) not in removed_ids:
            continue
        # H5034: the SECOND fail-open of the same shape as gate 2 — emptiness
        # here is read as "history never held this row", which is what makes
        # the row count as fresh and credits the relocation. A failed pickaxe
        # prints nothing too, so a git error used to manufacture that proof.
        # A non-zero exit is UNKNOWN: treat the row as seen (credit nothing).
        seen = git("log", "-S", t, "-1", "--format=%H", remote_ref,
                   "--", *paths).strip()
        if seen:
            continue  # history held this row: credits nothing
        # Empty. That is the evidence that makes the row "fresh", so confirm
        # the pickaxe actually RAN before believing it (same seam order as
        # blob_read: the patchable git() first, the honest exit code only for
        # the ambiguous empty answer).
        rc, _out = git_rc("log", "-S", t, "-1", "--format=%H", remote_ref,
                          "--", *paths)
        if rc == 0:
            fresh.append(t)
    return fresh


def hunk_rewrite_map(remote_ref: str, local_ref: str,
                     path: str) -> dict[int, list[str]]:
    """H4498 (class 11): removed OLD line number -> the stripped non-blank texts
    this push ADDS inside that line's own diff hunk.

    Built from the same ``diff -w -U0`` the rest of the guard reads, so a hunk
    here is a contiguous edited region and nothing else. A removed line whose
    hunk adds nothing does not appear with a non-empty list — a pure deletion
    has no replacement to credit."""
    out = git("diff", "-w", "-U0", remote_ref, local_ref, "--", path)
    hunks: list[tuple[list[int], list[str]]] = []
    removed: list[int] = []
    added: list[str] = []
    old_line = 0
    for line in out.splitlines():
        m = HUNK_RE.match(line)
        if m:
            if removed:
                hunks.append((removed, added))
            removed, added = [], []
            old_line = int(m.group(1))
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            removed.append(old_line)
            old_line += 1
        elif line.startswith("+"):
            text = line[1:].strip()
            if text:
                added.append(text)
    if removed:
        hunks.append((removed, added))
    return {ln: adds for lns, adds in hunks for ln in lns}


SHORT_REWRITE_MIN_RUN = 16
SHORT_REWRITE_MIN_SHARE = 0.5


def longest_verbatim_run(text: str, cand: str) -> int:
    """Length of the longest contiguous substring of `text` present in `cand`."""
    return difflib.SequenceMatcher(None, text, cand, autojunk=False) \
        .find_longest_match(0, len(text), 0, len(cand)).size


def hunk_rewrite_credit(remote_ref: str, path: str, sha: str, old_line: str,
                        hunk_adds: list[str], pre_cache: dict) -> str | None:
    """H4498, class 11 — H4455's credit made PROPORTIONAL and LOCAL.

    The §735 class is a rewrite whose surviving identity is large *relative to
    the line* but small in absolute characters, so both shipped pairing tests
    decline it: H4490's ``-def render(manuals, repo_root):`` ->
    ``+def render(manuals, repo_root, carried=None):`` keeps 29 of its 30
    characters verbatim — 97 % of the line — and is refused because 29 < 40,
    while class 5's ratio lands at 0.816 < 0.85.

    Two conditions replace the absolute one, and BOTH are needed. The first
    attempt at this handoff dropped identity entirely and paired on locality +
    gate (b) alone; the suite refuted it in 14 checks across 8 fences (9b, 11b,
    12b, 15b/15c, 16b, 21b, 27b, 28d/28e). The refutation is worth keeping: a
    replacement that is merely NEW text in the same place is what a destructive
    in-place overwrite looks like too, so gate (b) alone cannot separate "edited
    their line" from "wrote over their line". Identity is what separates them.

    * **Identity, proportional:** the replacement keeps a contiguous verbatim
      run of at least ``SHORT_REWRITE_MIN_SHARE`` of the removed line, never
      fewer than ``SHORT_REWRITE_MIN_RUN`` characters — so a short line is
      judged by how much of ITSELF survives, and a long hub row still has to
      carry a long fragment (28d/28e keep blocking).
    * **Locality:** the replacement is one of the lines this push adds inside
      the removed line's OWN diff hunk, and EVERY line that hunk adds passes
      gate (b) — tighter than H4455, which accepts a candidate anywhere in the
      file. A pure deletion has no hunk adds; a fresh line added beside a
      reinstalled pre-image line cannot launder it.
    """
    if not hunk_adds or not old_line:
        return None
    need = max(SHORT_REWRITE_MIN_RUN,
               int(len(old_line) * SHORT_REWRITE_MIN_SHARE))
    match = None
    for cand in hunk_adds:
        if cand == old_line:
            continue
        run = longest_verbatim_run(old_line, cand)
        if run >= need:
            match = run
            break
    if match is None:
        return None
    for cand in hunk_adds:
        if _forward_edit_ok(remote_ref, path, sha, cand, pre_cache) is not True:
            return None
    return "hunk-run=%d/%d" % (match, len(old_line))


# --- H4639: declarative credit/gate rule tables ------------------------------
# The per-line credit chain in blame_recent() accreted one hardcoded if-branch
# per credit (five credit patches in five commits proved the pattern). This
# block turns it into data: two tables, one thin evaluator (_apply_rules).
#
#   _LINE_EXEMPTION_RULES — run BEFORE the ours-check, per removed line, in
#     declared order; a match consumes the line (exempt, never a hit). The
#     exact-equality "moved, not lost" credit is the consumer end of the
#     data-driven survivor SOURCES, which were already lookup tables rather
#     than if-chains:
#       * H4569 shard rotation — a row moved verbatim into ANOTHER shard
#         (cross_file_survivors' REGISTRY_SHARD_RE / REGISTRY_SHARD_GLOB
#         branch);
#       * H4569 round 4 close-into-shard + §530 registry relocation
#         (REGISTRY_RELOCATION_PAIR / relocated_registry_rows /
#         fresh_archive_rows);
#       * H4595 close-rotation integration + sibling-archive moves
#         (CROSS_FILE_ARCHIVE_PAIRS);
#       * H4586 blob-URL prefix cell — the archive_normalized repoint arm
#         (class 3) of the same equality test (its fragment-masking critic
#         fixes live inside fragment_rewrite_credit, unchanged).
#
#   _CREDIT_RULES — run AFTER the ours-check, in declared order; the FIRST
#     rule whose predicate matches consumes the line. Order is load-bearing
#     and preserved from the inline chain: a line that would satisfy two
#     credits must fire the same one it always did (the row rewrite runs
#     before the fragment credit; class 5 spends its comparison budget and
#     runs before the recency-windowed hunk credit; the class-10 warning
#     precedes class 5; the §457 mint-close precedes class 10).
#
# Behavior contract (unchanged, pinned by tools/test_pre_push_stale_base_check.py):
# same predicates, same order, same payloads, same refusal texts. The credit
# helpers keep their own signatures — the table adapters below are the only
# new indirection, so tests that construct internals directly need no
# adaptation.

_OVERFLOW = object()  # sentinel: a rule ran out of the §543/§605 path budget


class _RuleCtx:
    """Per-line evaluation context for the H4639 rule tables.

    One mutable bag per removed line, built once in blame_recent() and shared
    by both evaluators. Fields mirror blame_recent's locals; ``stripped`` is
    filled in after the old_text lookup ("" when the line number is outside
    the old blob — every credit rule gates on it, exactly as the inline chain
    did)."""

    __slots__ = ("remote_ref", "path", "ln", "sha", "author", "when",
                 "cutoff", "stripped", "survivors", "near_survivors",
                 "near_budget", "pre_cache", "push_hids", "added_rows",
                 "added_bullets", "added_bullet_rows", "added_lines",
                 "hunk_adds", "lane_warns", "release_hids")

    def __init__(self, *, remote_ref, path, ln, sha, author, when, cutoff,
                 stripped, survivors, near_survivors, near_budget, pre_cache,
                 push_hids, added_rows, added_bullets, added_bullet_rows,
                 added_lines, hunk_adds, lane_warns, release_hids=frozenset()):
        self.remote_ref = remote_ref
        self.path = path
        self.ln = ln
        self.sha = sha
        self.author = author
        self.when = when
        self.cutoff = cutoff
        self.stripped = stripped
        self.survivors = survivors
        self.near_survivors = near_survivors
        self.near_budget = near_budget
        self.pre_cache = pre_cache
        self.push_hids = push_hids
        self.added_rows = added_rows
        self.added_bullets = added_bullets
        self.added_bullet_rows = added_bullet_rows
        self.added_lines = added_lines
        self.hunk_adds = hunk_adds
        self.lane_warns = lane_warns
        self.release_hids = release_hids


def _apply_rules(ctx, rules, row_credits: list, mods: list):
    """Thin evaluator: run `rules` in declared order against one removed line.

    The FIRST rule whose predicate matches consumes the line. Returns
    ``(consumed, overflow)``. Action dispatch: "credit" appends the payload
    to `row_credits` (printed loudly under ROW_REWRITE_MARKER), "warn"
    appends to ctx.lane_warns (LANE_WARN_MARKER), "mod" appends to `mods`
    (class-5 forward edits), "exempt" just consumes. A ``needs`` name skips
    the rule when that per-path input is absent (added_rows/added_bullets/
    added_lines/lane_warns/hunk_adds may be None for a path, as before);
    ``recent`` restricts the rule to the recency window. ``payload is
    _OVERFLOW`` aborts the path — the caller turns it into the explicit
    uncheckable verdict (§543/§605), never a silent skip. An empty
    ctx.stripped consumes nothing: every rule gates on authored content, and
    the inline chain's blank line fell straight through to the recency test.

    CONTRACT (H4639): consumption is by TRUTHINESS — a predicate declines by
    returning None/False; any returned credit/mod payload must therefore be
    truthy (non-empty label, dict). A future predicate whose meaningful
    payload could be falsy must box it (e.g. return a dict), or it will
    silently decline where the pre-table chain consumed.
    """
    if not ctx.stripped:
        return False, False
    for rule in rules:
        needs = rule.get("needs")
        if needs is not None and getattr(ctx, needs) is None:
            continue
        if rule.get("recent") and not (ctx.when is not None
                                       and ctx.when >= ctx.cutoff):
            continue
        payload = rule["check"](ctx)
        if not payload:
            # None (credit/mod rule declines) or False (exemption check
            # declined): fall through to the next rule. Credit/mod payloads
            # are always truthy (non-empty labels, dicts), so this is
            # equivalent to the inline chain's ``is not None`` tests.
            continue
        if payload is _OVERFLOW:
            return False, True
        act = rule["act"]
        if act == "credit":
            row_credits.append({"line": ctx.ln, "sha": ctx.sha[:9],
                                "token": payload})
        elif act == "warn":
            ctx.lane_warns.append({"line": ctx.ln, "sha": ctx.sha[:9],
                                   "author": ctx.author})
        elif act == "mod":
            mods.append(payload)
        # "exempt": the line simply never reaches the hits.
        return True, False
    return False, False


# --- _LINE_EXEMPTION_RULES predicates ----------------------------------------

def _exempt_moved_not_lost(ctx):
    """Exact-equality survivor credit (classes 1/3): the removed line
    survives verbatim in the pushed tree, or with its handoff link repointed
    to archive/ (H4586's archive_normalized arm). Fed by the data-driven
    sources listed in the banner above — shard rotation, close-into-shard,
    close-rotation integration, sibling-archive moves."""
    return ctx.stripped in ctx.survivors or \
        archive_normalized(ctx.stripped) in ctx.survivors


def _exempt_main_already_dropped(ctx):
    """H5000: the integration branch already dropped this line (see
    ``main_already_dropped``) — main's own removal, carried in by a merge or a
    rebase, not a revert authored by this push. Declared FIRST so main's churn
    never reaches the content exemptions or the recency hit; two ref-level git
    calls per (sha, path), both cached."""
    return main_already_dropped(ctx.remote_ref, ctx.path, ctx.sha,
                                ctx.stripped)


def _exempt_registry_bookkeeping(ctx):
    """Derived registry bookkeeping (counts, marker, dated header, bucket
    headers): regenerated by every close, so a rewrite destroys no work."""
    return is_registry_bookkeeping(ctx.path, ctx.stripped)


def _exempt_findings_marker(ctx):
    """The FINDINGS next-number marker, bumped forward by an append: it is
    consumed by construction, and the number only ever moves up (§695)."""
    return findings_marker_bump(ctx.path, ctx.stripped, ctx.survivors)


def _exempt_expired_claim(ctx):
    """An Active-Claims row that is ALREADY past its own TTL: a dead lease,
    not authored content. An unexpired row is NOT exempt and still blocks."""
    return is_expired_claim_row(ctx.path, ctx.stripped)


_LINE_EXEMPTION_RULES = (
    {
        # H5000 (MG 16-09-2026): base correction. The scan diffs against the
        # pushed branch's own remote tip, so everything main landed since that
        # tip reads as this push's deletion. A line already absent from
        # origin/main, whose blamer main already contains, cannot be lost by
        # this push — main dropped it first. ORDER IS LOAD-BEARING: declared
        # first so main's churn never spends the class-5 near-match budget.
        "id": "H5000-main-already-dropped",
        "act": "exempt",
        "check": _exempt_main_already_dropped,
    },
    {
        "id": "moved-not-lost-exact-survivor",
        "act": "exempt",
        "check": _exempt_moved_not_lost,
    },
    {
        "id": "derived-registry-bookkeeping",
        "act": "exempt",
        "check": _exempt_registry_bookkeeping,
    },
    {
        "id": "findings-next-number-bump",
        "act": "exempt",
        "check": _exempt_findings_marker,
    },
    {
        "id": "expired-claim-row",
        "act": "exempt",
        "check": _exempt_expired_claim,
    },
)


# --- _CREDIT_RULES predicates (thin adapters — the credit helpers keep their
# --- own signatures and remain directly callable) ----------------------------

def _credit_row_rewrite(ctx):
    return row_rewrite_token(ctx.remote_ref, ctx.path, ctx.sha, ctx.stripped,
                             ctx.added_rows, ctx.pre_cache)


def _credit_bullet_rewrite(ctx):
    return bullet_rewrite_token(ctx.remote_ref, ctx.path, ctx.sha,
                                ctx.stripped, ctx.added_bullets,
                                ctx.added_bullet_rows, ctx.pre_cache)


def _credit_fragment_rewrite(ctx):
    return fragment_rewrite_credit(ctx.remote_ref, ctx.path, ctx.sha,
                                   ctx.stripped, ctx.added_lines,
                                   ctx.pre_cache)


def _credit_mint_close(ctx):
    return is_same_session_mint_close(ctx.stripped, ctx.sha, ctx.push_hids,
                                      path=ctx.path)


def _credit_claim_release(ctx):
    return is_claim_release_inverse(ctx.path, ctx.stripped, ctx.sha,
                                    ctx.release_hids)


def _credit_same_lane(ctx):
    return is_same_lane_close_prep(ctx.path, ctx.sha, ctx.push_hids)


def _credit_hunk_rewrite(ctx):
    return hunk_rewrite_credit(ctx.remote_ref, ctx.path, ctx.sha,
                               ctx.stripped, ctx.hunk_adds.get(ctx.ln, []),
                               ctx.pre_cache)


def _class5_near_forward_mod(ctx):
    """CLASS 5: a near-match survivor whose text history has never seen before
    this commit's parent is a forward edit on top of their line, not a loss.

    Extracted verbatim from blame_recent's inline block (H4639). H4586
    (critic F2): ``near_survivors``, when given, is the subset class 5 may
    fuzzy-match against — registry archive rows are credited by exact
    equality or relocated_registry_rows only. Returns the mods payload, None
    (decline — the chain continues to the hunk credit / recency hit), or
    _OVERFLOW (§543/§605 budget out mid-path — the caller aborts into the
    explicit uncheckable verdict).
    """
    tied: list = []
    best, ovf = best_near_match(ctx.stripped,
                                ctx.survivors if ctx.near_survivors is None
                                else ctx.near_survivors, ctx.near_budget,
                                ties_out=tied)
    if ovf:
        return _OVERFLOW
    if best is None:
        return None
    key = (ctx.sha, ctx.path)
    if key not in ctx.pre_cache:
        if ctx.sha == _creation_sha(ctx.remote_ref, ctx.path):
            # FINDINGS §458: the blamer is the file's own BIRTH commit.
            # Gate (b)'s question — did the replacement text exist before
            # their edit? — has a definite answer here: NOTHING existed
            # before the file was born, so any near-match rewrite of birth
            # lines is forward by definition. The old code took
            # `pre_image_lines`'s None ("missing parent blob") as unknowable
            # and blocked, which refused the FIRST legitimate edit every file
            # younger than the window ever receives. A stale overwrite of a
            # newborn still blocks: it produces no near-match survivor to
            # pass gate (a) with.
            ctx.pre_cache[key] = set()
        else:
            ctx.pre_cache[key] = pre_image_lines(ctx.sha, ctx.path)
    pre = ctx.pre_cache[key]
    # FINDINGS §697 addendum: ask gate (b) of EVERY candidate tied at the
    # winning ratio, not of whichever one set iteration happened to yield.
    # One equally-good replacement absent from the pre-image is a forward
    # edit; a stale twin that merely ties with it must not veto that. Gates
    # 2/3 are untouched — a pre-image reinstall with no better-or-equal
    # fresh twin still blocks (case 14b), and NEAR_RATIO is unchanged.
    # H4614: byte-absence is not forwardness — a PERTURBED stale reinstall
    # (the pre-image plus cosmetic noise) is not byte-present either. A
    # candidate only counts as forward when it is absent from the pre-image
    # AND not a near match of an identity-anchored pre-image line (same
    # helper as _forward_edit_ok; unanchored candidates are unaffected).
    if pre is not None and any(
            c not in pre and not _near_anchored_preinstall(c, pre)
            for c in (tied or [best[0]])):
        return {"line": ctx.ln, "sha": ctx.sha[:9],
                "similarity": round(best[1], 2)}
    # pre unknown (missing parent/blob) or text existed pre-X: conservative
    # fall-through — still a hit (decline here; the chain continues).
    return None


_CREDIT_RULES = (
    {
        # FINDINGS §720 (H4437): a whole-line REWRITE of a recently-landed
        # row in a declared hub table — same token, identity preserved,
        # replacement text absent from the blamer's pre-image — is a forward
        # edit, not a loss. Credited rows land in ``row_credits`` and print
        # loudly under ROW_REWRITE_MARKER.
        "id": "H4437-row-rewrite",
        "needs": "added_rows",
        "act": "credit",
        "check": _credit_row_rewrite,
    },
    {
        # H4600: the same credit for the GTD dash-bullet lifecycle — the
        # §720 twin. An @DO -> DONE flip rewrites the bullet wholesale; same
        # first H### token, identity preserved, gate (b). Loud via
        # ROW_REWRITE_MARKER.
        "id": "H4600-gtd-bullet-rewrite",
        "needs": "added_bullets",
        "act": "credit",
        "check": _credit_bullet_rewrite,
    },
    {
        # H4455 (MG ruling 09-09-2026, option (b)): the same credit for ANY
        # file — a same-push replacement sharing a >=40-char verbatim
        # fragment with the removed line, still gate-(b)-checked. Code-file
        # in-place refactors (H4445: lanes_probe.py:51/140/286) and 0sq
        # one-liners pass; true deletions and <40-char near-misses still
        # block.
        "id": "H4455-fragment-rewrite",
        "needs": "added_lines",
        "act": "credit",
        "check": _credit_fragment_rewrite,
    },
    {
        # FINDINGS §457: the line is the fresh footprint of THIS handoff's
        # own mint (same-session mint→close). Verified against the three
        # gates in is_same_session_mint_close — the H1516 stale-pre-image
        # class does not satisfy gate 3 and still blocks below.
        "id": "same-session-mint-close",
        "act": "exempt",
        "check": _credit_mint_close,
    },
    {
        # H4527 (15-09-2026): claim→release, the §557 pair's inverse. A
        # release on a banner-less body only deletes the ledger row, so
        # §457 gate 3 cannot hold; see is_claim_release_inverse's four gates.
        "id": "claim-release-inverse",
        "act": "exempt",
        "check": _credit_claim_release,
    },
    {
        # CLASS 10 (GTD 0x, H4265): the line belongs to the SAME handoff
        # file's own close-prep — the blaming commit's subject names the
        # file's H###. Downgraded to a LOUD warning, never a silent pass:
        # collected into ``lane_warns`` and reported by report() while the
        # push is allowed.
        "id": "class10-same-lane-close-prep",
        "needs": "lane_warns",
        "act": "warn",
        "check": _credit_same_lane,
    },
    {
        # CLASS 5: see _class5_near_forward_mod. ORDER IS LOAD-BEARING: the
        # comparison budget is spent even when this rule declines and the
        # line later falls to the hunk credit or the recency hit — and a
        # line this rule credits never reaches the hunk credit.
        "id": "class5-near-match-forward-edit",
        "act": "mod",
        "check": _class5_near_forward_mod,
    },
    {
        # CLASS 11 (H4498, §735): the removed line's OWN hunk is being
        # rewritten — every line this push adds inside that hunk is absent
        # from the blamer's pre-image. Tighter than H4455 (which asks gate
        # (b) of one candidate anywhere in the file); a pure deletion has no
        # hunk adds and a pre-image reinstall fails gate (b), so both still
        # block. Recency-windowed ("recent": only removed lines inside the
        # window reach it), exactly as the inline chain gated it.
        "id": "H4498-hunk-rewrite",
        "needs": "hunk_adds",
        "recent": True,
        "act": "credit",
        "check": _credit_hunk_rewrite,
    },
)


def promoted_queue_lines(remote_ref: str, local_ref: str, path: str,
                         removed: list[int]) -> set[int]:
    """Removed `changelog_queue/*.md` lines this push PROMOTES into CHANGELOG.md.

    Class (9), §659, tightened to equality by H3886. `cut_release.py --apply`
    consumes the queue and stages each fragment's DELETION into the release
    commit, so every cut deletes lines another session queued minutes ago —
    measured on the v0.195.419 cut, 35 lines across 33 files. The bullet is not
    lost, it moved: `changelog_queue_consume.flush_bullets` copies each non-blank
    fragment line `ln.rstrip()` byte-identically into the release section.

    A removed fragment line is exempt ONLY when its exact stripped text is among
    the lines this SAME push ADDS to CHANGELOG.md. Not a near match, not a §530
    fragment prefix: a real cut is always byte-identical, so slack buys nothing
    here and costs the one thing this guard is for. Dropping someone's fresh
    fragment without promoting it blocks (case 24b); promoting a REWORDED bullet
    blocks (case 24c).

    Taken like §450's relocation — before blame, and deliberately never as a
    `survivors` entry, which also feeds class 5's difflib near match.
    """
    key = path.replace("\\", "/").lower()
    if not (key.startswith(CHANGELOG_QUEUE_PREFIX) and key.endswith(".md")):
        return set()
    promoted: set[str] = set()
    for base in CHANGELOG_BASENAMES:
        promoted.update(added_line_texts(remote_ref, local_ref, base))
    if not promoted:
        return set()
    old_text = blob_lines(remote_ref, path)
    ok: set[int] = set()
    for ln in removed:
        if not 1 <= ln <= len(old_text):
            continue
        stripped = old_text[ln - 1].strip()
        if stripped and stripped in promoted:
            ok.add(ln)
    return ok


def relocated_registry_rows(remote_ref: str, local_ref: str, path: str,
                            removed: list[int]) -> set[int]:
    """Removed README rows this push RELOCATES into REGISTRY_ARCHIVE.md.

    §450 measured six refused attempts on one close: relocating a row rewrites
    its status/date cells in the same operation, so no whole-line survivor
    exists and the surviving-text check cannot see the move. Predicate (the
    finding's own "checkable" bar): the removed line names an H###, AND the
    archive half GAINS, in this same push, a row naming the SAME H### that
    carries a contiguous verbatim fragment (>= VERBATIM_FRAGMENT_MIN) of the
    removed line — §530's fold-in (H3253), replacing the interim difflib
    near-match whose length slack missed real closes: the archived row appends
    a long close summary, so |cand| - |text| blows past max(8, 0.35*len) and
    the very relocation this predicate exists to allow was refused again,
    identically across two independent fresh checkouts on 24-08-2026 (H3167).
    A stale checkout that merely drops someone's fresh row adds nothing to the
    archive and stays blocked; an archive row naming the id without carrying
    the row's text also stays blocked — the bare-id false negative §437/§450
    warn against. H4586: "the row's text" is its title/slug cell, matched
    exactly (``row_text_relocated``) — the 40-char fragment alone was met by
    the shared blob-URL prefix.
    """
    target = REGISTRY_RELOCATION_PAIR.get(
        path.replace("\\", "/").lower())
    if not target:
        return set()
    added_archive = fresh_archive_rows(remote_ref, local_ref, target, path)
    if not added_archive:
        return set()
    old_text = blob_lines(remote_ref, path)
    ok: set[int] = set()
    for ln in removed:
        if not 1 <= ln <= len(old_text):
            continue
        stripped = old_text[ln - 1].strip()
        rid = row_id(stripped)
        if not rid:
            continue
        same_id = [c for c in added_archive if row_id(c) == rid]
        if same_id and row_text_relocated(stripped, same_id):
            ok.add(ln)
    return ok


# H4586 (H4569 critic): every registry row links under one shared blob prefix
# (``https://github.com/gasyoun/Uprava/blob/main/handoffs/``, 53 chars), so a
# >= VERBATIM_FRAGMENT_MIN run of the WHOLE row was satisfied by the link
# alone — a stale tree closing H#### from an OLDER copy of its README row
# silently dropped a colleague's fresh title edit. A close (handoff_close.py)
# rewrites only the status cell and repoints the link ``handoffs/X.md`` ->
# ``handoffs/archive/X.md`` (handoff_archive.repoint_text); every other cell
# moves over byte-identical. So the row's title/slug cell must reappear
# EXACTLY, modulo that repoint: the middle cell linking under ``handoffs/``
# (a PR link in the legacy-tag column is not the title — critic F4), else the
# first link-bearing middle cell; a row with no link at all (none of the 4,328
# rows on 11-09-2026) must keep EVERY middle cell (critic F5: a 40-char run of
# a long plain title survives an in-place edit). Status-cell
# edits are rewritten by any close: out of scope. A row with no middle cell
# falls back to the fragment test with the URL/path boilerplate masked.
BLOB_PREFIX_RE = re.compile(r"https?://github\.com/[^/\s)]+/[^/\s)]+/blob/[^/\s)]+/")
HANDOFFS_PATH_RE = re.compile(r"handoffs/(?:archive/)?")
HANDOFFS_LINK_RE = re.compile(r"\]\([^)]*handoffs/")


def is_registry_path(path: str) -> bool:
    """The handoff registry: README (live half) or either archive pathspec."""
    key = path.replace("\\", "/").lower()
    if key in REGISTRY_RELOCATION_PAIR:
        return True
    return any(key == t.lower() or (t.endswith("/") and key.startswith(t.lower()))
               for targets in REGISTRY_RELOCATION_PAIR.values() for t in targets)


def _row_cells(row: str) -> list[str]:
    """Stripped cells of a markdown table row (escaped ``\\|`` kept)."""
    parts = re.split(r"(?<!\\)\|", row.strip())
    if len(parts) >= 2 and not parts[0].strip():
        parts = parts[1:]
    if len(parts) >= 2 and not parts[-1].strip():
        parts = parts[:-1]
    return [p.strip() for p in parts]


def _unrepoint(cell: str) -> str:
    return cell.replace("handoffs/archive/", "handoffs/")


def _title_cells(row: str):
    """The row's identity cells (see block comment), repoint undone; None
    when the row has no cell between its id and its status."""
    middle = _row_cells(row)[1:-1]
    if not middle:
        return None
    linked = [c for c in middle if "](" in c]
    if not linked:
        return {_unrepoint(c) for c in middle}
    pick = next((c for c in linked if HANDOFFS_LINK_RE.search(c)), linked[0])
    return {_unrepoint(pick)}


def _mask_link_boilerplate(text: str) -> str:
    return HANDOFFS_PATH_RE.sub("", BLOB_PREFIX_RE.sub("", text))


def row_text_relocated(removed_row: str, candidates) -> bool:
    """True when one candidate row carries `removed_row`'s own title/slug
    cell exactly, not just the blob-URL prefix every row shares (H4586)."""
    need = _title_cells(removed_row)
    if need is not None:
        return any(need <= {_unrepoint(c) for c in _row_cells(cand)[1:-1]}
                   for cand in candidates)
    return has_verbatim_fragment(_mask_link_boilerplate(removed_row),
                                 [_mask_link_boilerplate(c) for c in candidates])


# MG 04-10-2026 whole-file self-cleanup credits: filled by scan() when a push
# deletes a path whose birth commit the pusher's history contains; printed as
# a loud ALLOWED note in report().
_SELF_CLEANED_CREDITS: list[dict] = []
# WBA (22-10-2026): paths whose pushed tree is byte-identical to the
# integration ref. The push cannot change (let alone lose) them; reported
# loudly so a human can see the credit was taken.
EQUIVALENT_MARKER = "STALE_BASE_EQUIVALENT"
_EQUIVALENT_CREDITS: list[dict] = []


def scan(local_ref: str, remote_ref: str, recent_days: float,
         max_paths: int,
         max_blame_lines: int = DEFAULT_MAX_BLAME_LINES,
         max_near_pairs: int = DEFAULT_MAX_NEAR_PAIRS,
         ) -> tuple[dict[str, list], dict[str, list], bool, dict[str, dict],
                    dict[str, list]]:
    """(found, modified, truncated, uncheckable, warned, row_credits).

    ``uncheckable`` maps path -> {"removed", "reason"} for every path whose
    line-level analysis exceeded the §543/§605 work bounds. Such paths get NO
    line-level verdict here — the caller degrades them to ref-level
    verification and prints the STALE_BASE_CIRCUIT_BREAK note, loudly, either
    way. ``warned`` maps path -> [line dicts] for class-10 same-lane close-prep
    lines (GTD 0x): they never block, but they are reported loudly so a human
    can verify them after the push lands. ``row_credits`` maps path ->
    [line dicts] for §720 (H4437) hub-row rewrites the guard credits as
    forward edits: they never block either, and print just as loudly.
    """
    ours = pushed_commits(remote_ref, local_ref)
    cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)
    paths = changed_paths(remote_ref, local_ref)
    truncated = len(paths) > max_paths
    # §457 gate 3: which H###s THIS PUSH visibly works on — ids in changed path
    # basenames anywhere in the diff, plus ids inside added lines per path.
    push_hids = frozenset(h for p in paths for h in HID_RE.findall(p))
    # H4527: ids whose claim a commit in this push releases (subject-level).
    release_hids = release_subject_hids(remote_ref, local_ref)

    found: dict[str, list] = {}
    modified: dict[str, list] = {}
    uncheckable: dict[str, dict] = {}
    warned: dict[str, list] = {}
    row_credits: dict[str, list] = {}
    pre_cache: dict = {}
    for path in paths[:max_paths]:
        # WBA: if the pushed tree's copy already equals main's, the diff below
        # only shows the branch's earlier duplicate being replaced by main's
        # canonical content — a no-op once merged, not a stale-base revert.
        if path_matches_integration(local_ref, path):
            _EQUIVALENT_CREDITS.append({"path": path})
            continue
        removed = removed_line_numbers(remote_ref, local_ref, path)
        if not removed:
            continue
        # MG 04-10-2026: whole-file self-cleanup. When the push removes the
        # path ENTIRELY and the file's birth commit is an ancestor of the
        # pushed head, the pusher's tree saw the file born — deleting it is a
        # visible choice, and the stale-preimage accident cannot produce the
        # shape (a stale tree never saw the birth, so the birth commit is NOT
        # an ancestor and the refusal stands). Line-level rewrites inside
        # files that survive keep every protection below. Checked before any
        # blame: one cat-file + at most one merge-base per deleted file.
        # CHANGELOG_QUEUE fragments are EXCLUDED: their deletion is governed
        # by the §659 promotion contract (a fragment drops only when its
        # bullet is released into CHANGELOG.md — suite cases 24b/24c), not by
        # lineage; an unconsumed fragment is real work, stale or not.
        if (not path_in_tree(local_ref, path)
                and not path.startswith(CHANGELOG_QUEUE_PREFIX)):
            _birth = _creation_sha(remote_ref, path)
            if _birth and git_rc("merge-base", "--is-ancestor",
                                 _birth, local_ref)[0] == 0:
                _SELF_CLEANED_CREDITS.append({"path": path,
                                              "sha": _birth[:9]})
                continue
        if is_generated_single_writer(path):
            continue
        if is_generated_snapshot(remote_ref, path):
            continue
        if is_mint_stub(remote_ref, path):
            continue
        # FINDINGS §450: rows this push relocates into REGISTRY_ARCHIVE.md are
        # moves, not losses — drop them from the flagged set before blaming.
        relocated = relocated_registry_rows(remote_ref, local_ref, path, removed)
        if relocated:
            removed = [ln for ln in removed if ln not in relocated]
            if not removed:
                continue
        # §659 (H3886): fragment lines whose exact text this push copies into
        # CHANGELOG.md are promoted by a release cut, not lost. Same pre-blame
        # position as §450 above, and the credit never reaches `survivors` —
        # that set also feeds class 5's near match, which forgave a reworded
        # bullet (case 24c).
        promoted = promoted_queue_lines(remote_ref, local_ref, path, removed)
        if promoted:
            removed = [ln for ln in removed if ln not in promoted]
            if not removed:
                continue
        own_survivors = surviving_text(local_ref, path)
        survivors = own_survivors | \
            cross_file_survivors(remote_ref, local_ref, path)
        # H4586 (critic F2): a stale MOVE that keeps the status cell (archive
        # tool, registry split) scores ~0.98 against the colleague's retitled
        # row and passes gate (b) — the repointed link is never byte-equal to
        # their pre-image. The §659 precedent: archive rows credit by exact
        # equality (above) or relocated_registry_rows, never by near match.
        near_survivors = own_survivors if is_registry_path(path) else None
        # §543/§605 work bounds. Fired BEFORE any blame: on a wholesale
        # derived-file rewrite the old loop paid one blame subprocess per
        # removed line and one difflib comparison per (removed, survivor)
        # pair — hours of unbounded work, with the push killed by the
        # caller's timeout before any verdict existed.
        if len(removed) > max_blame_lines:
            uncheckable[path] = {
                "removed": len(removed),
                "reason": "%d removed line(s) > --max-blame-lines %d"
                          % (len(removed), max_blame_lines)}
            continue
        # H4569 critic: bound the pool class 5 actually walks. Exact-only
        # cross-file survivors must not trip the break — on a fast-forward
        # push "uncheckable" passes, so a big rotation hid a dropped row.
        pair_pool = survivors if near_survivors is None else near_survivors
        if len(removed) * len(pair_pool) > max_near_pairs:
            uncheckable[path] = {
                "removed": len(removed),
                "reason": "near-match pairs ~%d (removed x survivors) > "
                          "--max-near-pairs %d"
                          % (len(removed) * len(pair_pool), max_near_pairs)}
            continue
        added_lines = added_line_texts(remote_ref, local_ref, path)
        path_push_hids = frozenset(push_hids) | {
            h for t in added_lines for h in HID_RE.findall(t)}
        # §720 (H4437): the same-push added lines of a declared hub table,
        # keyed by row token — the rewrite side of the exemption.
        added_rows: dict[str, list[str]] = {}
        if posix_basename(path.replace("\\", "/")) in ROW_REWRITE_PATHS:
            for t in added_lines:
                tok = row_token(t)
                if tok:
                    added_rows.setdefault(tok, []).append(t)
        # H4600: the same-push added dash bullets of the declared GTD hub,
        # keyed by first H### — the rewrite side of the bullet exemption.
        # H7295: minted bullets are also keyed by the trailer's row id, the
        # identity that actually anchors their credit (the writer H### is
        # shared by every minted card and cannot tell two rows apart).
        added_bullets: dict[str, list[str]] = {}
        added_bullet_rows: dict[str, list[str]] = {}
        if posix_basename(path.replace("\\", "/")) in GTD_BULLET_PATHS:
            for t in added_lines:
                tok = gtd_bullet_token(t)
                if tok:
                    added_bullets.setdefault(tok, []).append(t)
                rid = gtd_bullet_row_id(t)
                if rid:
                    added_bullet_rows.setdefault(rid, []).append(t)
        try:
            blame = blame_map(remote_ref, path)
        except BlameTimeout as exc:
            uncheckable[path] = {
                "removed": len(removed),
                "reason": "git blame timeout: %s" % exc,
            }
            continue
        budget = [max_near_pairs]
        lane_warns: list[dict] = []
        path_row_credits: list[dict] = []
        hits, mods, overflow = blame_recent(remote_ref, path, removed, cutoff,
                                            ours, survivors, pre_cache,
                                            path_push_hids, blame, budget,
                                            lane_warns, added_rows,
                                            added_bullets, added_bullet_rows,
                                            path_row_credits, added_lines,
                                            hunk_rewrite_map(remote_ref,
                                                             local_ref, path),
                                            near_survivors,
                                            release_hids=release_hids)
        if overflow and not hits:
            # Budget ran out before any concrete loss was proven: an unfinished
            # exemption search is an unanswered question, so the path gets the
            # explicit uncheckable verdict instead of a speculative refusal
            # (§605: a false refusal is visible; a hang teaches authors to
            # bypass — and a speculative block on unaffordable analysis is the
            # false-refusal cousin of the same mistake).
            uncheckable[path] = {
                "removed": len(removed),
                "reason": "near-match budget exhausted mid-path (%d removed "
                          "line(s), bound %d)" % (len(removed), max_near_pairs)}
            continue
        if hits:
            found[path] = hits
        if mods:
            modified[path] = mods
        if lane_warns:
            warned[path] = lane_warns
        if path_row_credits:
            row_credits[path] = path_row_credits
    return found, modified, truncated, uncheckable, warned, row_credits


LANE_WARN_MARKER = "STALE_BASE_SAME_LANE_WARNING"


def report_lane_warnings(warned: dict[str, list], e=None) -> None:
    """The loud class-10 verdict: lines named, push ALLOWED (GTD 0x).

    Never silent — the whole point of downgrading the H4265 refusal is that the
    same-lane rewrite still shows up in stderr for the human, with every line
    and its blaming commit, so a foreign session's stale revert of a handoff
    file cannot hide behind the class either.
    """
    e = e or sys.stderr
    n_warn = sum(len(v) for v in warned.values())
    print("%s — push ALLOWED — %d recently-added handoff line(s) were "
          "rewritten/deleted by a commit whose subject names the same H### as "
          "the file (same-lane close-prep, the H4265 shape; MG 06-09-2026 "
          "«Флип разрешить», GTD 0x):" % (LANE_WARN_MARKER, n_warn), file=e)
    for path, warns in warned.items():
        print("  %s" % path, file=e)
        for w in warns:
            print("      line %-6d added by %s (%s)" % (w["line"], w["sha"],
                                                        w["author"]), file=e)
    print("  If these lines could belong to ANOTHER session's work, verify by "
          "hand:  git blame --line-porcelain <remote> -- <path>", file=e)
    print("", file=e)


def report_non_ff(found: dict[str, list], remote_ref: str,
                  e=None, row_credits: dict[str, list] | None = None) -> None:
    """A NON-fast-forward push: say so, name the phantom lines, block nothing.

    Deliberately worded to contain NEITHER banner string
    `handoff_claims.GUARD_BANNER_RE` matches (`PUSH BLOCKED` /
    `pre-push: BLOCKED`), because a caller that reads this run as a guard block
    draws the exact opposite conclusion from the truth: this IS origin/main
    moving, and refetch-and-retry is what clears it.

    ``row_credits`` (H4437): credited row rewrites are just as phantom on a
    non-ff base as refusals — the exemption emptied ``found``, so without
    naming them here the skip would print "0 'deleted' line(s)" over a push
    whose credit was decided against a tip that is not this commit's parent.
    """
    row_credits = row_credits or {}
    e = e or sys.stderr
    total = sum(len(v) for v in found.values()) + \
        sum(len(v) for v in row_credits.values())
    print("", file=e)
    print("%s — push NOT blocked by this guard. %s is not an ancestor of the "
          "pushed commit, so this push is a NON-fast-forward: git will refuse "
          "it on its own (and on main the line gate refuses a forced one). The "
          "%d 'deleted' line(s) below are an artefact of diffing against a tip "
          "that is not this commit's parent — refetch, rebuild on the current "
          "tip, and push again." % (NON_FF_MARKER, remote_ref, total), file=e)
    for path, hits in sorted(found.items()):
        print("  %s" % path, file=e)
        for line, sha, author in hits[:5]:
            print("      line %-6d added by %s (%s)" % (line, sha, author), file=e)
        if len(hits) > 5:
            print("      … %d more" % (len(hits) - 5), file=e)
    for path, rws in sorted(row_credits.items()):
        print("  %s (row-rewrite credit — phantom here)" % path, file=e)
        for r in rws[:5]:
            print("      line %-6d added by %s  (row token %s)"
                  % (r["line"], r["sha"], r["token"]), file=e)
        if len(rws) > 5:
            print("      … %d more" % (len(rws) - 5), file=e)
    print("", file=e)


def report(found: dict[str, list], modified: dict[str, list],
           remote_ref: str, recent_days: float,
           truncated: bool, max_paths: int,
           warned: dict[str, list] | None = None,
           row_credits: dict[str, list] | None = None) -> None:
    warned = warned or {}
    row_credits = row_credits or {}
    total = sum(len(v) for v in found.values())
    e = sys.stderr
    print("", file=e)
    if not found:
        # Class 5 pass-through: say WHY the rewrite was allowed so the note is
        # greppable from wrappers, mirroring the refusal banner's discipline.
        # A push with no recent-line interaction stays silent, as before.
        n_mod = sum(len(v) for v in modified.values())
        if n_mod:
            print("stale-base guard: ALLOWED - %d recently-added line(s) were "
                  "modified in place (forward edits on top of upstream work, none "
                  "deleted)." % n_mod, file=e)
            for path, mods in modified.items():
                for m in mods:
                    print("  %s:%d sim %.2f (%s)" % (path, m["line"],
                                                     m["similarity"], m["sha"]), file=e)
        if _SELF_CLEANED_CREDITS:
            print("stale-base guard: ALLOWED - %d deleted file(s) were born "
                  "inside the pusher's own history (whole-file self-cleanup, "
                  "MG 04-10-2026):" % len(_SELF_CLEANED_CREDITS), file=e)
            for _c in _SELF_CLEANED_CREDITS[:10]:
                print("  %s (born at %s)" % (_c["path"], _c["sha"]), file=e)
        if _EQUIVALENT_CREDITS:
            print("%s — push ALLOWED — %d path(s) are byte-identical to the "
                  "integration ref (the branch adopted main's canonical "
                  "content, so this push is a no-op for them — WBA):"
                  % (EQUIVALENT_MARKER, len(_EQUIVALENT_CREDITS)), file=e)
            for _c in _EQUIVALENT_CREDITS[:10]:
                print("  %s" % _c["path"], file=e)
        n_rw = sum(len(v) for v in row_credits.values())
        if n_rw:
            print("%s — push ALLOWED — %d recently-added line(s) rewritten in "
                  "place (same row token, forward edit — H4437 §720 + H4455 "
                  "verbatim fragment):"
                  % (ROW_REWRITE_MARKER, n_rw), file=e)
            for path, rws in row_credits.items():
                print("  %s" % path, file=e)
                for r in rws:
                    print("      line %-6d added by %s  (row token %s)"
                          % (r["line"], r["sha"], r["token"]), file=e)
            print("  If a credited row could belong to ANOTHER session's "
                  "work, verify by hand:", file=e)
            print("    git blame --line-porcelain %s -- <path>" % remote_ref,
                  file=e)
        if sum(len(v) for v in warned.values()):
            report_lane_warnings(warned, e)
        if n_mod or warned or n_rw or _EQUIVALENT_CREDITS:
            if truncated:
                print("NOTE: only the first %d changed paths were scanned (--max-paths)."
                      % max_paths, file=e)
            print("", file=e)
        return
    # The banner must match what main() actually returns — the H2656 lesson, kept
    # after the 16-08-2026 re-promotion to a blocker. It once printed "PUSH BLOCKED"
    # on a path that warned and let the push through; a session read that as a
    # refusal twice and hand-verified origin both times before noticing. Now the
    # check blocks unconditionally, so the one banner is the true one.
    print("", file=e)
    # H3134 (FINDINGS §493): the override belongs on the FIRST line, not twenty
    # lines into the banner — a retry loop that only greps stderr for
    # REFUSAL_MARKER can stop after one attempt instead of burning its whole
    # budget re-asking a question this refusal never depends on the remote tip
    # to answer. This is always a LOCAL hook decision (a genuine non-fast-forward
    # never reaches this script — git itself rejects it first).
    print(escape_first_line("%s — LOCAL guard refusal, not a moved remote tip."
                            "  Override:  %s=1 git push ..."
                            % (REFUSAL_MARKER, ESCAPE_ENV)), file=e)
    print("PUSH BLOCKED — this push deletes %d line(s) that landed on %s"
          % (total, remote_ref), file=e)
    print("within the last %g day(s), in %d file(s), and your commits never "
          "reference them." % (recent_days, len(found)), file=e)
    print("", file=e)
    shown = 0
    for path, hits in found.items():
        print("  %s" % path, file=e)
        for ln, sha, author in hits:
            if shown >= MAX_LISTED:
                break
            print("      line %-6d added by %s (%s)" % (ln, sha, author), file=e)
            shown += 1
        if shown >= MAX_LISTED:
            print("      …", file=e)
            break
    print("", file=e)
    if sum(len(v) for v in warned.values()):
        print("Also warned (class 10 same-lane close-prep — listed, not blocked, "
              "but this push is refused for the OTHER lines above):", file=e)
        for path, warns in warned.items():
            print("  %s" % path, file=e)
            for w in warns:
                print("      line %-6d added by %s (%s)" % (w["line"], w["sha"],
                                                            w["author"]), file=e)
        print("", file=e)
    if sum(len(v) for v in row_credits.values()):
        print("Also credited (§720 row-state rewrites — these lines would pass, "
              "but this push is refused for the OTHER lines above):", file=e)
        for path, rws in row_credits.items():
            print("  %s" % path, file=e)
            for r in rws:
                print("      line %-6d added by %s  (row token %s)"
                      % (r["line"], r["sha"], r["token"]), file=e)
        print("", file=e)
    if _EQUIVALENT_CREDITS:
        print("Also credited (paths byte-identical to the integration ref — "
              "no net change, WBA):", file=e)
        for _c in _EQUIVALENT_CREDITS[:10]:
            print("  %s" % _c["path"], file=e)
        print("", file=e)
    print("That is Uprava#1516. Twice now a clean fast-forward with green hooks has", file=e)
    print("installed a pre-image copy over another session's work: 6 files on 29-07", file=e)
    print("(stale index after `git reset --soft`), 19 link fixes on 04-08 (stale", file=e)
    print("checkout — the branch ref moved, the working tree did not).", file=e)
    print("", file=e)
    print("If you did NOT mean to touch those lines, your file content is stale:", file=e)
    print("    git fetch origin && git rebase %s" % remote_ref, file=e)
    print("and if `git status` lists files you never edited, do NOT `git add -A` and", file=e)
    print("do NOT lift a patch out of that tree (a patch encodes its base, FINDINGS", file=e)
    print("§308) — rebuild on a fresh worktree off %s and re-apply your edits." % remote_ref, file=e)
    print("", file=e)
    print(escape_paragraph("If the revert IS deliberate:  %s=1 git push ..."
                           % ESCAPE_ENV,
                           paths=sorted(found),
                           refusal_class="content"), file=e)
    if truncated:
        print("", file=e)
        print("NOTE: only the first %d changed paths were scanned (--max-paths)." % max_paths, file=e)
    print("", file=e)


def report_circuit_break(uncheckable: dict[str, dict], ref_ok: bool,
                         remote_ref: str) -> None:
    """The loud §543/§605 verdict for paths the work bound skipped.

    Printed on EVERY circuit-broken push, allowed or refused — the row's bar is
    an explicit «skipped, uncheckable» verdict instead of silent omission. The
    marker sits on the first line so wrappers can grep it.
    """
    e = sys.stderr
    print("", file=e)
    print("%s — %d path(s) SKIPPED by the work bound, UNCHECKED at line level "
          "(FINDINGS §543, §605)." % (CIRCUIT_MARKER, len(uncheckable)), file=e)
    for path, info in uncheckable.items():
        print("  %s: %s" % (path, info["reason"]), file=e)
    if ref_ok:
        print("  Degraded to ref-level verification: %s IS an ancestor of the "
              "pushed tip (clean fast-forward) — allowed, but these paths were "
              "NOT scanned for silent line-level reverts." % remote_ref, file=e)
    else:
        print("  PUSH BLOCKED — ref-level verification FAILED: %s is NOT an "
              "ancestor of the pushed tip (forced/non-fast-forward update), "
              "and a bulk rewrite of unscanned paths on such an update is "
              "refused fail-closed." % remote_ref, file=e)
        print("  " + escape_first_line("Override:  %s=1 git push ..." % ESCAPE_ENV),
              file=e)
    print("  If this push might revert ANOTHER SESSION's lines on those paths, "
          "verify by hand first:", file=e)
    print("    git blame --line-porcelain %s -- <path>" % remote_ref, file=e)
    print("", file=e)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("local_ref")
    ap.add_argument("remote_ref")
    ap.add_argument("--recent-days", type=float, default=3.0)
    ap.add_argument("--max-paths", type=int, default=40)
    ap.add_argument("--max-blame-lines", type=int,
                    default=DEFAULT_MAX_BLAME_LINES,
                    help="per-path removed-line bound past which the path is "
                         "skipped loudly (§543/§605)")
    ap.add_argument("--max-near-pairs", type=int,
                    default=DEFAULT_MAX_NEAR_PAIRS,
                    help="per-path near-match comparison budget (§543/§605)")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-mint-exempt", action="store_true",
                    help="disable the mint-claim fast path (force the full "
                         "line scan; used by the control cases and by a human "
                         "who wants the sweep anyway)")
    args = ap.parse_args(argv)

    if not args.no_fetch:
        # Bounded (19-10-2026): the one call in this guard that is certainly
        # network. A stalled fetch here used to hold every main push open.
        #
        # W8H (MG ruling 24-10-2026): a fetch is not a read — it WRITES
        # `refs/remotes/<remote>/*` in the shared object store, and this hook
        # runs on EVERY push, so it was the single loudest source of the
        # 20-10-2026 ref thrash (five backwards moves in one session). It now
        # goes through git_net's serialized fetch lane. Fail-open: any lane
        # fault falls back to the plain bounded fetch this line always did.
        _remote, _, _ref = args.remote_ref.partition("/")
        _remote = _remote or "origin"
        _ref = _ref or "main"
        _lane_ok = False
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
            import git_net  # noqa: PLC0415 -- sibling tool, imported on the fetch path only
            _lane = git_net.run_fetch(os.getcwd(), (_ref,), remote=_remote,
                                      timeout_s=FETCH_TIMEOUT_S,
                                      lock_timeout_s=FETCH_LOCK_WAIT_S)
            _lane_ok = True
            if _lane.get("waited_s"):
                print("git_net: fetch lane waited %.1fs for another session"
                      % _lane["waited_s"], file=sys.stderr)
        except Exception:  # noqa: BLE001 -- a lane fault must never block a push
            _lane_ok = False
        if not _lane_ok:
            git("fetch", _remote, "--quiet", timeout=FETCH_TIMEOUT_S)

    if not git("rev-parse", "--verify", "--quiet", args.remote_ref).strip():
        if args.json:
            print(json.dumps({"result": "skip", "reason": "remote ref not found"}))
        return 0

    # GTD WC7 (H7216 residual): the claim commit's parent IS the remote tip, so
    # the stale-pre-image class is structurally impossible and the blame sweep
    # is not just slow, it is unanswerable in principle. The proof declines on
    # any doubt and the full scan below runs exactly as before.
    if not args.no_mint_exempt:
        proof = mint_claim_proof(args.remote_ref, args.local_ref)
        if proof is not None:
            detail = ("parent == %s; subject %r; added %s; touched %s"
                      % (proof["parent"], proof["subject"],
                         ",".join(proof["added"]) or "-",
                         ",".join(proof["touched"]) or "-"))
            if log_firing is not None:
                try:
                    log_firing(git("rev-parse", "--show-toplevel").strip(),
                               "stale-base", "mint-claim-exempt", detail)
                except Exception as exc:  # noqa: SE3 -- telemetry never changes a verdict
                    print(f"warn: stale-base telemetry (mint-claim-exempt) failed: {exc}",
                          file=sys.stderr)
            print("pre-push stale-base: MINT CLAIM — line scan EXEMPT "
                  "(structural proof: the commit's parent IS the remote tip, "
                  "the only deletions are the mint's derived lines, every other "
                  "path is the tip's own content). %s" % detail, file=sys.stderr)
            if args.json:
                print(json.dumps({"result": "mint-claim-exempt",
                                  "parent": proof["parent"],
                                  "subject": proof["subject"],
                                  "added": proof["added"],
                                  "touched": proof["touched"]}))
            return 0

    found, modified, truncated, uncheckable, warned, row_credits = scan(
        args.local_ref, args.remote_ref, args.recent_days, args.max_paths,
        args.max_blame_lines, args.max_near_pairs)

    # H4342: a NON-fast-forward push is not this guard's business, and every
    # line it flags on one is a phantom. See push_is_fast_forward().
    # H4437: credited row rewrites are phantom on a non-ff base too — and the
    # exemption EMPTIES ``found``, so the gate must key on any line-level
    # signal or the credit blinds the verdict exactly like a refusal would.
    if (found or row_credits) and not push_is_fast_forward(args.remote_ref,
                                                           args.local_ref):
        if log_firing is not None:
            try:
                log_firing(git("rev-parse", "--show-toplevel").strip(),
                           "stale-base", "non-ff-skip",
                           "non-fast-forward push; %d phantom line(s) in %d "
                           "path(s) not scanned: %s"
                           % (sum(len(v) for v in found.values()), len(found),
                              ",".join(sorted(found))[:400]))
            except Exception as exc:  # noqa: SE3 -- telemetry must never break the guard
                print(f"warn: stale-base telemetry (non-ff-skip log_firing) failed: {exc}", file=sys.stderr)
        if args.json:
            print(json.dumps({
                "result": "non-ff-skip",
                "paths": sorted(found),
                "lines": sum(len(v) for v in found.values()),
                "row_rewrites": {p: len(v) for p, v in row_credits.items()},
            }))
            return 0
        report_non_ff(found, args.remote_ref, row_credits=row_credits)
        return 0

    # §543/§605: circuit-broken paths degrade to ref-level verification —
    # fast-forward passes (loudly), a forced/non-ff bulk rewrite fails closed.
    ref_ok = True
    if uncheckable:
        ref_ok = git_ok("merge-base", "--is-ancestor",
                        args.remote_ref, args.local_ref)

    # H3069: additive §469 check — silent ADDITIONS inside an already-tagged
    # CHANGELOG section. Runs only when its own hatch is not raised; the
    # deletion-side scan and every one of its exemptions are untouched.
    drift: list[dict] = []
    structural: list[tuple[str, list[dict]]] = []
    if not os.environ.get(TAG_DRIFT_ENV):
        drift = changelog_tag_drift(args.remote_ref, args.local_ref,
                                    args.max_paths)
        # Same refusal family, same hatch: layout-level collisions the
        # line-diff above cannot see (duplicate headings, non-descending
        # sections — the #2335 collision class, repaired 29-08-2026).
        structural = changelog_structure_path_findings(
            args.remote_ref, args.local_ref, args.max_paths)

    blocked = (bool(found) or bool(drift) or bool(structural)
               or (bool(uncheckable) and not ref_ok))

    # S27 telemetry: one JSONL line per run into the clone's central firing
    # log (logs/guard_firings.jsonl in the MAIN checkout — every worktree of
    # the clone shares it). "refuse" when the push is blocked (the detail
    # names which refusal classes fired), "circuit-break" when the §543/§605
    # degraded verdict allowed a push whose paths were NOT line-scanned.
    # Fail-open end to end: a telemetry failure must never alter the verdict
    # or reach the guard's stderr.
    if log_firing is not None:
        try:
            classes = []
            if found:
                # H4342: the paths, not just the counts. Ten days of
                # "stale-base lines=1 paths=1" records could establish that the
                # guard fired 3222 times and nothing at all about WHICH file or
                # which rival commit, so no recurrence could be diagnosed from
                # the record the log exists to be. Names only, capped — this
                # file is gitignored local evidence, same as the main-line
                # witness, and a path list is what a census can group by.
                classes.append("stale-base lines=%d paths=%d [%s]" % (
                    sum(len(v) for v in found.values()), len(found),
                    ",".join(sorted(found))[:400]))
            if warned:
                classes.append("same-lane-warn lines=%d paths=%d" % (
                    sum(len(v) for v in warned.values()), len(warned)))
            if row_credits:
                classes.append("row-rewrite lines=%d paths=%d" % (
                    sum(len(v) for v in row_credits.values()), len(row_credits)))
            if drift:
                classes.append("changelog-tag-drift sections=%d" % len(drift))
            if structural:
                classes.append("changelog-structure paths=%d" % len(structural))
            if uncheckable:
                classes.append("circuit-break paths=%d ref=%s" % (
                    len(uncheckable),
                    "fast-forward" if ref_ok else "non-fast-forward"))
            toplevel = git("rev-parse", "--show-toplevel").strip()
            if blocked:
                log_firing(toplevel, "stale-base", "refuse",
                           "; ".join(classes) or "blocked")
            elif warned:
                log_firing(toplevel, "stale-base", "warn",
                           "allowed; " + "; ".join(classes))
            elif row_credits:
                log_firing(toplevel, "stale-base", "row-rewrite-allow",
                           "allowed; " + "; ".join(classes))
            elif uncheckable:
                log_firing(toplevel, "stale-base", "circuit-break",
                           "allowed; " + "; ".join(classes))
        except Exception as exc:  # noqa: SE3 -- telemetry must never break the guard
            print(f"warn: stale-base telemetry (decision log_firing) failed: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps({
            "result": "block" if blocked else "ok",
            "paths": sorted(found),
            "lines": sum(len(v) for v in found.values()),
            "modified": {p: len(v) for p, v in modified.items()},
            "lane_warnings": {p: len(v) for p, v in warned.items()},
            "row_rewrites": {p: len(v) for p, v in row_credits.items()},
            "truncated": truncated,
            "circuit_break": uncheckable,
            "circuit_ref_level": "fast-forward" if ref_ok else "non-fast-forward",
            "changelog_tag_drift": drift,
            "changelog_structure": [{"path": p, "findings": f}
                                    for p, f in structural],
        }))
        return 1 if blocked else 0

    if uncheckable:
        report_circuit_break(uncheckable, ref_ok, args.remote_ref)
    report(found, modified, args.remote_ref, args.recent_days, truncated,
           args.max_paths, warned, row_credits)
    if drift:
        report_tag_drift(drift)
    for p, f in structural:
        report_structure_drift(f, p)
    if not blocked:
        return 0
    # BLOCKS by default (MG 16-08-2026, reversing the demotion below). The push is
    # refused; the escape hatch in the banner is the single way through. STRICT_ENV
    # is kept as an accepted no-op so older callers and docs do not break.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
