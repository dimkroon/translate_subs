# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from test.support import fixtures
fixtures.global_setup()

from unittest import TestCase

from resources.lib import utils

from test.support.testutils import doc_path

# noinspection PyMethodMayBeStatic
class VttToSrt(TestCase):
    def test_1_cue_timestamps(self):
        # convert decimal dot to comma
        srt = utils.vtt_to_srt('01:02:03.234 --> 02:03:04.567')
        self.assertEqual('\n1\n01:02:03,234 --> 02:03:04,567\n', srt)
        # add missing hours
        srt = utils.vtt_to_srt('02:03.234 --> 03:04.567')
        self.assertEqual('\n1\n00:02:03,234 --> 00:03:04,567\n', srt)

    def test_2_add_sequence_numbers(self):
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n\n01:03:03.234 --> 01:03:04.567')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n\n2\n01:03:03,234 --> 01:03:04,567\n', srt)

    def test_other_style_new_lines(self):
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\r\n\r\n01:03:03.234 --> 01:03:04.567')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n\n2\n01:03:03,234 --> 01:03:04,567\n', srt)
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\r\r01:03:03.234 --> 01:03:04.567')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n\n2\n01:03:03,234 --> 01:03:04,567\n', srt)

    def test_remove_non_cue_blocks(self):
        srt = utils.vtt_to_srt('WEBVTT\n\n01:02:03.234 --> 01:02:04.567')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n', srt)
        # from https://developer.mozilla.org/en-US/docs/Web/API/WebVTT_API:
        vtt = """
WEBVTT

STYLE
::cue {
  background-image: linear-gradient(to bottom, dimgray, lightgray);
  color: papayawhip;
}

NOTE comment blocks can be used between style blocks.

STYLE
::cue(b) {
  color: peachpuff;
}

00:00:00.000 --> 00:00:10.000
- Hello <b>world</b>"""
        srt = utils.vtt_to_srt(vtt)
        self.assertEqual('\n1\n00:00:00,000 --> 00:00:10,000\n- Hello <b>world</b>\n', srt)

    def test_write_cue_payload(self):
        # Single line
        srt = utils.vtt_to_srt(
            '01:02:03.234 --> 02:03:04.234\n'
            'text 1\n\n'
            '04:05:06.456 --> 04:05:07.457\n'
            'text 2'
        )
        self.assertEqual(
            '\n1\n01:02:03,234 --> 02:03:04,234\n'
            'text 1\n'
            '\n2\n04:05:06,456 --> 04:05:07,457\n'
            'text 2\n', srt)
        # Multiline
        srt = utils.vtt_to_srt(
            '01:02:03.234 --> 02:03:04.234\n'
            'Text 1 line1\nline2\n\n'
            '04:05:06.456 --> 04:05:07.457\n'
            'Text 2 line1\nline2'
        )
        self.assertEqual(
            '\n1\n01:02:03,234 --> 02:03:04,234\n'
            'Text 1 line1\nline2\n'
            '\n2\n04:05:06,456 --> 04:05:07,457\n'
            'Text 2 line1\nline2\n', srt
        )

    def test_remove_cue_settings(self):
        srt = utils.vtt_to_srt('01:02:03.234 --> 02:03:04.567 line:0 position:20% size:60%')
        self.assertEqual('\n1\n01:02:03,234 --> 02:03:04,567\n', srt)

    def test_remove_vtt_identifier(self):
        srt = utils.vtt_to_srt('some id\n02:03.234 --> 02:04.567\ntext 1')
        self.assertEqual('\n1\n00:02:03,234 --> 00:02:04,567\ntext 1\n', srt)

    def test_remove_unsupported_markup_tags(self):
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<v Julie>text 1</v>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\ntext 1\n', srt)
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<c.whispering>text 1</c>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\ntext 1\n', srt)
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<ruby>text 1</ruby>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\ntext 1\n', srt)
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<rt>text 1</rt>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\ntext 1\n', srt)

    def test_keep_supported_markup_tags(self):
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<b>text 1</b>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n<b>text 1</b>\n', srt)
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<i>text 1</i>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n<i>text 1</i>\n', srt)
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<u>text 1</u>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n<u>text 1</u>\n', srt)

    def test_convert_colour_tags(self):
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<c.yellow>text 1</c>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n<font color="yellow">text 1</font>\n', srt)
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<c.yellow>text 1</c>', False)
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\ntext 1\n', srt)

    def test_convert_named_colours(self):
        for colour in ('white', 'yellow', 'green', 'cyan', 'red'):
            srt = utils.vtt_to_srt(f'01:02:03.234 --> 01:02:04.567\n<c.{colour}>text 1</c>')
            self.assertEqual(f'\n1\n01:02:03,234 --> 01:02:04,567\n<font color="{colour}">text 1</font>\n', srt)

    def test_rgb_colours(self):
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<c.color008000>text 1</c>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n<font color="#008000">text 1</font>\n', srt)
        srt = utils.vtt_to_srt('01:02:03.234 --> 01:02:04.567\n<c.color008000ff>text 1</c>')
        self.assertEqual('\n1\n01:02:03,234 --> 01:02:04,567\n<font color="#008000">text 1</font>\n', srt)

    def test_convert_whole_file(self):
        for subtitle in (
                'vtt/subtitles_1_ok.vtt',
                'vtt/subtitles_doc_martin.vtt'
                ):
            with open(doc_path(subtitle)) as f:
                vtt = f.read()
            srt = utils.vtt_to_srt(vtt)
            self.assertGreater(len(srt), 100)
