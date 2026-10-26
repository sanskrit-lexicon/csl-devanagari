# coding=utf-8
"""Pins for bughunt 26-10-2026 findings 4 and 5.

Finding 4 — a metaline may repeat a tag (`<e>,ulapya/<e>2B` in MW). The old
`parseheadline` -> dict -> reserialise path kept only the LAST value per tag, so
every earlier duplicate silently vanished from the mirror. `transliterate_metaline_keys`
converts the two text fields in place and touches nothing else.

Finding 5 — `convert_partially_to_slp1` built its split pattern from raw
start/end marks while the forward converter escaped them; a mark carrying a
regex metacharacter silently mis-split.
"""
import unittest

from to_devanagari import transliterate_metaline_keys
from to_slp1 import convert_partially_to_slp1


class MetalineInPlaceTest(unittest.TestCase):
    def test_duplicate_tags_survive(self):
        line = '<L>37448.1<pc>218,2<k1>ulapya<k2>ulapya^<e>,ulapya/<e>2B'
        out = transliterate_metaline_keys(line, 'slp1')
        self.assertEqual(out.count('<e>'), 2, out)      # the dict rebuild kept one
        self.assertIn('<k1>उलप्य', out)                  # k1 still converted
        self.assertIn(',ulapya/', out)                   # first <e> value kept
        self.assertTrue(out.endswith('2B'), out)

    def test_plain_metaline_matches_former_output(self):
        self.assertEqual(
            transliterate_metaline_keys('<L>1<pc>1,1<k1>rAma<k2>rAma<h>a<e>1', 'slp1'),
            '<L>1<pc>1,1<k1>राम<k2>राम<h>a<e>1',
        )

    def test_trailing_space_is_not_dropped(self):
        line = '<L>16582<pc>94,2<k1>alaMjuza<k2>ala/M-juza<h>a<e>1 '
        self.assertTrue(transliterate_metaline_keys(line, 'slp1').endswith('<e>1 '))

    def test_bytes_outside_k1_k2_are_untouched(self):
        line = '<L>9<pc>1,1<k1>aMS<k2>aMS<e>1<X-future>rAma</X-future>'
        out = transliterate_metaline_keys(line, 'slp1')
        self.assertIn('<X-future>rAma</X-future>', out)


class EscapedMarksTest(unittest.TestCase):
    def test_regex_metachar_marks_are_literal(self):
        # '(' + ')' as marks: unescaped, the pattern `(.*?)` matches the empty
        # string at every position and the segment is mangled.
        self.assertEqual(
            convert_partially_to_slp1('(', ')', 'slp1_accented', '(राम)'),
            '(rAma)',
        )

    def test_real_marks_still_work(self):
        self.assertEqual(
            convert_partially_to_slp1('{#', '#}', 'slp1_accented', '{#राम#}'),
            '{#rAma#}',
        )


if __name__ == '__main__':
    unittest.main()
