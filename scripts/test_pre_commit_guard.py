# coding=utf-8
"""Pin for bughunt 26-10-2026 finding 1: the main-tree guard must actually FIRE.

Until 26-10-2026 the hook compared against a hardcoded Windows path only, so on
every macOS/Linux clone it exited 0 — an inert guard that read as protection
(§263/§333). These tests run the real hook against throwaway repos:

* the canonical checkout (via CANONICAL_MAIN_TREE / ..._HOME) must be refused;
* a linked worktree must pass;
* the ALLOW_MAIN_TREE_COMMIT escape must keep working.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / '.githooks' / 'pre-commit'


class MainTreeGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='csl-dev-guard-'))
        self.main = self.tmp / 'main'
        self.worktree = self.tmp / 'linked-worktree'
        for d in (self.main, self.worktree):
            d.mkdir()
            subprocess.run(['git', '-C', str(d), 'init', '-q'], check=True)
        # git resolves symlinks in --show-toplevel (macOS /var -> /private/var),
        # and the hook compares plain strings: feed it what git itself reports.
        self.main_top = self.toplevel(self.main)
        self.worktree_top = self.toplevel(self.worktree)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def toplevel(path):
        out = subprocess.run(['git', '-C', str(path), 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()

    def hook(self, cwd, **env_extra):
        env = os.environ.copy()
        for name in ('ALLOW_MAIN_TREE_COMMIT', 'CANONICAL_MAIN_TREE',
                     'CANONICAL_MAIN_TREE_HOME'):
            env.pop(name, None)
        env.update(env_extra)
        return subprocess.run(['bash', str(HOOK)], cwd=str(cwd), env=env,
                              capture_output=True, text=True)

    def test_refuses_the_canonical_checkout(self):
        r = self.hook(self.main, CANONICAL_MAIN_TREE=self.main_top)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn('BLOCKED', r.stderr)

    def test_home_twin_is_honoured(self):
        r = self.hook(self.main,
                      CANONICAL_MAIN_TREE='/nonexistent/windows/checkout',
                      CANONICAL_MAIN_TREE_HOME=self.main_top)
        self.assertEqual(r.returncode, 1, r.stderr)

    def test_allows_a_linked_worktree(self):
        r = self.hook(self.worktree, CANONICAL_MAIN_TREE=self.main_top)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_escape_hatch_still_works(self):
        r = self.hook(self.main, CANONICAL_MAIN_TREE=self.main_top,
                      ALLOW_MAIN_TREE_COMMIT='1')
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == '__main__':
    unittest.main()
