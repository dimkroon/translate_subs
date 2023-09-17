# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from test.support import fixtures
fixtures.global_setup()

import unittest
from unittest.mock import MagicMock, patch

from resources.lib.subtitles import subtitle

from test.support.testutils import open_doc



class TestLine(unittest.TestCase):
    def test_text_line(self):
        txt = 'This is text'
        l = subtitle.SrtLine(txt)
        frase = l._frases[0]
        self.assertEqual('', frase.open_tags)
        self.assertEqual(txt, frase.text)
        self.assertEqual('', frase.closing_tags)

    def test_text_with_colour(self):
        txt = '<font color="cyan">This is text</font>'
        l = subtitle.SrtLine(txt)
        frase = l._frases[0]
        self.assertEqual('<font color="cyan">', frase.open_tags)
        self.assertEqual('This is text', frase.text)
        self.assertEqual('</font>', frase.closing_tags)

    def test_text_before_colour(self):
        txt = 'Something else <font color="cyan">This is text</font>'
        l = subtitle.SrtLine(txt)
        frase = l._frases[0]
        self.assertEqual('', frase.open_tags)
        self.assertEqual('Something else', frase.text)
        self.assertEqual('', frase.closing_tags)
        frase = l._frases[1]
        self.assertEqual('<font color="cyan">', frase.open_tags)
        self.assertEqual('This is text', frase.text)
        self.assertEqual('</font>', frase.closing_tags)

    def test_text_with_colour_not_at_start_of_line(self):
        txt = ' <font color="cyan">This is text</font>'
        l = subtitle.SrtLine(txt)
        frase = l._frases[0]
        self.assertEqual('<font color="cyan">', frase.open_tags)
        self.assertEqual('This is text', frase.text)
        self.assertEqual('</font>', frase.closing_tags)

    def test_line_strips_whitespace(self):
        l = subtitle.SrtLine(' This is text  ')
        self.assertEqual('This is text', l._frases[0].text)
        l = subtitle.SrtLine('<font color="cyan"> This is text </font>')
        self.assertEqual('This is text', l._frases[0].text)

    def test_text_without_open_tag(self):
        txt = 'This is text</font>'
        frase = subtitle.SrtLine(txt)._frases[0]
        self.assertEqual('',  frase.open_tags)
        self.assertEqual('This is text', frase.text)
        self.assertEqual('', frase.closing_tags)

    def test_text_without_closing_tag(self):
        txt = '<i>This is text'
        frase = subtitle.SrtLine(txt)._frases[0]
        self.assertEqual('', frase.open_tags)
        self.assertEqual('This is text', frase.text)
        self.assertEqual('', frase.closing_tags)

    def test_empty_line(self):
        line = subtitle.SrtLine('')
        self.assertEqual(0, len(line._frases))
        line = subtitle.SrtLine(' ')
        self.assertEqual(0, len(line._frases))
        line = subtitle.SrtLine('<font color="cyan"></font>')
        self.assertEqual(0, len(line._frases))
        line = subtitle.SrtLine('<font color="cyan"> </font>')
        self.assertEqual(0, len(line._frases))


test_block ="""
1
00:03:20,960 --> 00:03:22,960

"""


class TestSrtBlock(unittest.TestCase):
    def test_single_line_of_text(self):
        block = subtitle.SrtBlock(test_block + 'This is one line')
        self.assertTrue(block)
        self.assertEqual(1, len(block.lines))
        self.assertEqual(1, len(list(block)))

    def test_double_line_of_text(self):
        block = subtitle.SrtBlock(test_block + 'This is one line\nand this is the second')
        self.assertTrue(block)
        self.assertEqual(2, len(block.lines))
        self.assertEqual(2, len(list(block)))
