# coding=utf-8
import unittest

from to_slp1 import (
    convert_partially_to_slp1,
    convert_to_slp1,
    transliterate_text_preserving_xml_tags,
)


class ToSlp1MarkupTest(unittest.TestCase):
    def test_plain_devanagari_text_converts(self):
        self.assertEqual(
            transliterate_text_preserving_xml_tags('राम गच्छति', 'slp1_accented'),
            'rAma gacCati',
        )

    def test_segment_tags_are_preserved(self):
        self.assertEqual(
            convert_partially_to_slp1('<s>', '</s>', 'slp1_accented', '<s>राम</s>'),
            '<s>rAma</s>',
        )

    def test_embedded_xml_tags_are_preserved_inside_segment(self):
        self.assertEqual(
            convert_partially_to_slp1(
                '<s>',
                '</s>',
                'slp1_accented',
                '<s>राम <ab>देव</ab> गच्छति</s>',
            ),
            '<s>rAma <ab>deva</ab> gacCati</s>',
        )

    def test_whole_line_conversion_preserves_xml_tags(self):
        self.assertEqual(
            convert_to_slp1('राम <info n="1">गच्छति</info><lex>देव</lex><lb/>'),
            'rAma <info n="1">gacCati</info><lex>deva</lex><lb/>',
        )

    def test_metaline_tags_are_preserved(self):
        self.assertEqual(
            transliterate_text_preserving_xml_tags(
                '<L>1<pc>1<k1>राम<k2>राꣳम<e>1',
                'slp1_accented',
            ),
            '<L>1<pc>1<k1>rAma<k2>rAM£ma<e>1',
        )

    def test_skip_lines_remain_unchanged(self):
        data = '\n'.join([
            '<L>1<pc>1<k1>राम<k2>राम',
            '[Page1-a+ 1]',
            '<H>राम',
            '<LEND>',
        ])
        self.assertEqual(convert_to_slp1(data), data)

    def test_vedic_anusvara_marker_converts_to_accented_slp1(self):
        self.assertEqual(
            transliterate_text_preserving_xml_tags('देवाꣳसो', 'slp1_accented'),
            'devAM£so',
        )


if __name__ == '__main__':
    unittest.main()
