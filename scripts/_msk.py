"""Standalone portability primitives for the Uprava tool fleet (H5714 items 7+9).

Mirrors claude-config's scripts/_msk.py + hooks/hook_util.py (now_msk/today_msk)
semantics one-to-one — the two estates share one scheduling vocabulary.

- Time: the estate plans in MSK (the 9–21 МСК drain window); naive local time
  breaks at a DST boundary or a cross-box move. Two call shapes:
    * ``now_msk()``            — aware stamp, isoformat() carries +03:00
    * ``now_msk().replace(tzinfo=None)`` — MSK WALL projection for worlds that
      store naive stamps and compare them as strings / subtract them (the
      projection keeps the stored format byte-identical while pinning the tz).
  ``today_msk()`` for date stamps. Stored timestamps stay ISO-8601; the offset
  is the handoff's allowed format delta.

- Binaries: launchd strips PATH to /usr/bin:/bin:/usr/sbin:/sbin, and the
  Windows Task Scheduler lane runs with its own minimal set — a bare
  ``["git", ...]`` argv resolves differently (or not at all) per context.
  ``which_bin`` resolves via shutil.which, then an explicit absolute fallback
  list, and fails loud (SystemExit) only when BOTH miss — that fail-loud is
  what makes the drain tooling boot under ``env -i`` (H5714 item 9 verify).

Standalone rule (same as _cli.py): imports nothing from tools/, importable in
a minimal clone — ``sys.path[0]`` is tools/ for any ``python tools/x.py`` run,
and backup_w2/* insert the parent dir before importing.
"""
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    MSK = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    # Windows has no system IANA db; a minimal runner without the `tzdata`
    # wheel raises at IMPORT time and took down every CI gate that imports
    # this module (guards registry-counts step + changelog lint, all PRs and
    # main, 03-10-2026 — first surfaced on PR #3968 run 37130468188).
    # Europe/Moscow is a fixed UTC+03:00 zone (no DST since 2014), so a
    # fixed-offset fallback is semantically exact, not an approximation.
    MSK = timezone(timedelta(hours=3), name="Europe/Moscow")

#: Absolute fallbacks probed in order when shutil.which comes up empty
#: (stripped-PATH launchd / ``env -i`` / Task Scheduler minimal env).
_BIN_FALLBACKS = {
    # Mac
    "git": ("/opt/homebrew/bin/git", "/usr/local/bin/git", "/usr/bin/git"),
    "gh": ("/opt/homebrew/bin/gh", "/usr/local/bin/gh"),
    "python3": ("/opt/homebrew/bin/python3", "/usr/bin/python3"),
    "osascript": ("/usr/bin/osascript",),
    "ssh": ("/usr/bin/ssh",),
    "rsync": ("/usr/bin/rsync",),
    "rclone": ("/opt/homebrew/bin/rclone", "/usr/local/bin/rclone"),
    "restic": ("/opt/homebrew/bin/restic", "/usr/local/bin/restic"),
    "launchctl": ("/bin/launchctl",),
    "ps": ("/bin/ps",),
    "bash": ("/bin/bash",),
    "id": ("/usr/bin/id",),
    "pgrep": ("/usr/bin/pgrep",),
    "crontab": ("/usr/bin/crontab",),
    "curl": ("/usr/bin/curl",),
    "node": ("/opt/homebrew/bin/node", "/usr/local/bin/node"),
    "tgrep": ("/opt/homebrew/bin/tgrep", "/usr/local/bin/tgrep"),
    # Windows lane (the MSI box; present only there)
    "schtasks": (r"C:\Windows\System32\schtasks.exe",),
    "powershell": (r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",),
    "tasklist": (r"C:\Windows\System32\tasklist.exe",),
    "wmic": (r"C:\Windows\System32\wbem\WMIC.exe",),
    # H5715 residue sweep: names surfaced by the S607 corpus pass
    "xattr": ("/usr/bin/xattr",),
    "rg": ("/opt/homebrew/bin/rg", "/usr/local/bin/rg"),
    "df": ("/bin/df",),
    "dig": ("/usr/bin/dig",),
    "say": ("/usr/bin/say",),
    "scp": ("/usr/bin/scp",),
    "lsof": ("/usr/sbin/lsof",),
    "opencode": ("/opt/homebrew/bin/opencode", "/usr/local/bin/opencode"),
    "pandoc": ("/opt/homebrew/bin/pandoc", "/usr/local/bin/pandoc"),
    "mysql": ("/opt/homebrew/bin/mysql", "/usr/local/bin/mysql"),
    "pdftotext": ("/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext"),
    "cmd": (r"C:\Windows\System32\cmd.exe",),
    "where": (r"C:\Windows\System32\where.exe",),
    "icacls": (r"C:\Windows\System32\icacls.exe",),
    "msg": (r"C:\Windows\System32\msg.exe",),
    "taskkill": (r"C:\Windows\System32\taskkill.exe",),
}


def now_msk():
    """Timezone-aware ``datetime.now`` pinned to Europe/Moscow (H5714 item 7)."""
    return datetime.now(MSK)


def today_msk():
    """Timezone-aware ``date.today`` pinned to Europe/Moscow (H5714 item 7)."""
    return datetime.now(MSK).date()


#: A day-first date inside an artifact NAME — `05-09-2026`, `05.09.26`,
#: `05_09_2026`. Year-first names (`2026-10-19`, `20261019`) are deliberately
#: NOT matched: they already sort correctly as strings and need no help.
_NAME_DATE_RE = re.compile(r"(?<!\d)(\d{2})[-._](\d{2})[-._](\d{2}|\d{4})(?!\d)")


def parse_name_date(name, century=2000):
    """``(year, month, day)`` from a day-first date in ``name``, else ``None``.

    FINDINGS §820(a) (GTD WE4, 24-10-2026): ``sorted()`` over day-first date
    names is NOT date order — ``payments_export_25-08-2026.tsv`` sorts AFTER
    ``payments_export_05-09-2026.tsv`` and ``digest_30.09.26.md`` after
    ``digest_24.10.26.md``. Every "newest artifact" pick parses the date first;
    two money tools already carry the correct form
    (``money_ledger_unified.export_stamp_key``,
    ``build_revenue_monthly.newest_export``) and this is the shared one.
    """
    m = _NAME_DATE_RE.search(name or "")
    if not m:
        return None
    day, month, year = (int(g) for g in m.groups())
    if year < 100:
        year += century
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return (year, month, day)


def newest_dated(items, key=None):
    """The newest item by the date in its NAME; an undated item never wins.

    ``items`` may be paths or strings; ``key`` maps an item to its name when it
    is neither (a bare filename string is used as-is). An item with no
    parseable date sorts BELOW every dated one — it cannot claim "newest" —
    and ties fall back to the name so the pick stays deterministic.
    """
    best, best_key = None, None
    for item in items:
        name = key(item) if key else getattr(item, "name", None) or str(item)
        parsed = parse_name_date(name)
        candidate = (parsed is not None, parsed or (), str(name))
        if best_key is None or candidate > best_key:
            best, best_key = item, candidate
    return best


def which_bin(name):
    """Resolve a bare binary name to an absolute path (H5714 item 9).

    shutil.which against the live PATH first; then the pinned fallback list;
    then SystemExit naming the binary — fail loud, a silent fallthrough would
    put a half-resolved argv into subprocess.
    """
    found = shutil.which(name)
    if found:
        return found
    for cand in _BIN_FALLBACKS.get(name, ()):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    raise SystemExit("required executable not found (PATH + fallbacks): %s" % name)
