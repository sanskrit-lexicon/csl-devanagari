# coding=utf-8
"""Pins for bughunt 26-10-2026 finding 3: the csl-orig carry script must refuse.

Until 26-10-2026 `carry_changes_to_cslorig.sh` was nine unconditional lines that
`cp`-ed 40 converted dictionaries into the canonical csl-orig clone. These tests
build a throwaway pair of repositories and check every gate: deliberate intent,
clean target, target at origin/main, empty round-trip diffs, mirror not older
than the source — plus the one happy path where the copy may happen.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'carry_changes_to_cslorig.sh'

STUB_CONVERTER = '''\
import pathlib, sys
d = sys.argv[1]
root = pathlib.Path(__file__).resolve().parent.parent
(root / "slp1").mkdir(exist_ok=True)
body = (root / "v02" / d / (d + ".txt")).read_text(encoding="utf-8")
(root / "slp1" / (d + ".txt")).write_text("SLP1:" + body, encoding="utf-8")
'''

GIT_ENV = {
    'GIT_AUTHOR_NAME': 'test', 'GIT_AUTHOR_EMAIL': 'test@example.com',
    'GIT_COMMITTER_NAME': 'test', 'GIT_COMMITTER_EMAIL': 'test@example.com',
}


def dictionaries():
    text = SCRIPT.read_text(encoding='utf-8')
    m = re.search(r'^dicts=\((.*?)\)', text, re.M)
    return m.group(1).split()


class CarryGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='carry-gate-'))
        self.repo = self.tmp / 'csl-devanagari'
        self.scripts = self.repo / 'scripts'
        self.scripts.mkdir(parents=True)
        shutil.copy(SCRIPT, self.scripts / SCRIPT.name)
        (self.scripts / 'to_slp1.py').write_text(STUB_CONVERTER, encoding='utf-8')

        self.dicts = dictionaries()
        self.assertTrue(self.dicts, 'dict list not found in the script')
        old = time.time() - 600
        now = time.time()
        for d in self.dicts:
            (self.repo / 'v02' / d).mkdir(parents=True, exist_ok=True)
            (self.repo / 'diff').mkdir(exist_ok=True)
            (self.repo / 'slp1').mkdir(exist_ok=True)
            mirror = self.repo / 'v02' / d / (d + '.txt')
            mirror.write_text('mirror-' + d + '\n', encoding='utf-8')
            (self.repo / 'diff' / (d + '.txt')).write_text('', encoding='utf-8')
            source = self.tmp / 'csl-orig' / 'v02' / d / (d + '.txt')
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('source-' + d + '\n', encoding='utf-8')
            os.utime(source, (old, old))
            os.utime(mirror, (now, now))

        self.csl_orig = self.tmp / 'csl-orig'
        self.git('init', '-q')
        self.git('add', '-A')
        self.git('commit', '-qm', 'source')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        env = os.environ.copy()
        env.update(GIT_ENV)
        return subprocess.run(['git', '-C', str(self.csl_orig), *args],
                              capture_output=True, text=True, env=env, check=False)

    def run_carry(self, *args, allow=True):
        env = os.environ.copy()
        env.pop('ALLOW_CARRY', None)
        if allow:
            env['ALLOW_CARRY'] = '1'
        return subprocess.run(['bash', SCRIPT.name, *args], cwd=str(self.scripts),
                              env=env, capture_output=True, text=True)

    def source_text(self, d='mw'):
        return (self.csl_orig / 'v02' / d / (d + '.txt')).read_text(encoding='utf-8')

    # ---- gates ------------------------------------------------------------
    def test_refuses_without_allow_flag(self):
        r = self.run_carry(allow=False)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('ALLOW_CARRY=1', r.stderr)

    def test_refuses_a_dirty_csl_orig(self):
        (self.csl_orig / 'v02' / 'mw' / 'mw.txt').write_text('edited\n', encoding='utf-8')
        r = self.run_carry()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('uncommitted changes', r.stderr)

    def test_refuses_when_csl_orig_is_not_at_origin_main(self):
        (self.csl_orig / 'extra.txt').write_text('x\n', encoding='utf-8')
        self.git('add', '-A')
        self.git('commit', '-qm', 'ahead')
        r = self.run_carry()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('not at origin/main', r.stderr)

    def test_refuses_a_non_empty_round_trip_diff(self):
        (self.repo / 'diff' / 'skd.txt').write_text('21357c21357\n', encoding='utf-8')
        r = self.run_carry()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('skd', r.stderr)

    def test_refuses_a_stale_mirror(self):
        source = self.csl_orig / 'v02' / 'gra' / 'gra.txt'
        # bash 3.2 compares whole seconds: make the source unambiguously newer.
        future = time.time() + 120
        os.utime(source, (future, future))
        r = self.run_carry()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('gra', r.stderr)

    def test_refuses_outside_scripts_dir(self):
        env = os.environ.copy()
        env['ALLOW_CARRY'] = '1'
        r = subprocess.run(['bash', str(self.scripts / SCRIPT.name)], cwd=str(self.tmp),
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    # ---- the one path that may write --------------------------------------
    def test_dry_run_prints_the_plan_and_writes_nothing(self):
        r = self.run_carry('--dry-run')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('dry run', r.stdout)
        self.assertEqual(self.source_text('mw'), 'source-mw\n')

    def test_happy_path_copies_every_dictionary(self):
        r = self.run_carry()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.source_text('mw'), 'SLP1:mirror-mw\n')
        self.assertEqual(self.source_text('gra'), 'SLP1:mirror-gra\n')


if __name__ == '__main__':
    unittest.main()
