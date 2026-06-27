# coding=utf-8
import unittest

from to_devanagari import (
    convert_partially_to_devanagari,
    convert_to_devanagari,
    transliterate_text_preserving_xml_tags,
)


class ToDevanagariMarkupTest(unittest.TestCase):
    def test_plain_slp1_text_converts(self):
        self.assertEqual(
            transliterate_text_preserving_xml_tags('rAma gacCati', 'slp1_accented'),
            'राम गच्छति',
        )

    def test_segment_tags_are_preserved(self):
        self.assertEqual(
            convert_partially_to_devanagari('<s>', '</s>', 'slp1_accented', '<s>rAma</s>'),
            '<s>राम</s>',
        )

    def test_embedded_xml_tags_are_preserved_inside_segment(self):
        self.assertEqual(
            convert_partially_to_devanagari(
                '<s>',
                '</s>',
                'slp1_accented',
                '<s>rAma <ab>deva</ab> gacCati</s>',
            ),
            '<s>राम <ab>देव</ab> गच्छति</s>',
        )

    def test_whole_line_conversion_preserves_xml_tags(self):
        self.assertEqual(
            convert_to_devanagari('rAma <info n="1">gacCati</info><lex>deva</lex><lb/>'),
            'राम <info n="1">गच्छति</info><lex>देव</lex><lb/>',
        )

    def test_skip_lines_remain_unchanged(self):
        data = '\n'.join([
            '<L>1<pc>1<k1>rAma<k2>rAma',
            '[Page1-a+ 1]',
            '<H>rAma',
            '<LEND>',
        ])
        self.assertEqual(convert_to_devanagari(data), data)


if __name__ == '__main__':
    unittest.main()
