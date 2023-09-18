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

from resources.lib.subtitles import merge
from resources.lib.subtitles.subtitle import SrtFrase, SrtDoc

from test.support.testutils import open_doc


class TestSentence(unittest.TestCase):
    def test_1_instantiate(self):
        s = merge.Sentence()
        self.assertListEqual([], s.orig_frases)
        s = merge.Sentence(SrtFrase('', '', ''))
        self.assertEqual(1, len(s.orig_frases))
        s = merge.Sentence(SrtFrase('', '', ''), SrtFrase('', '', ''), SrtFrase('', '', ''))
        self.assertEqual(3, len(s.orig_frases))

    def test_relative_line_lengths(self):
        s = merge.Sentence(SrtFrase('a', '', ''), SrtFrase('bc', '', ''), SrtFrase('dw', '', ''))
        self.assertListEqual([0.2, 0.5, 1], s._relative_line_lengths())
        s = merge.Sentence(SrtFrase('a', '', ''), SrtFrase('b', '', ''), SrtFrase('c', '', ''))
        self.assertListEqual([1/3, 0.5, 1], s._relative_line_lengths())
        s = merge.Sentence(SrtFrase('a line', '', ''))
        self.assertListEqual([1], s._relative_line_lengths())


class TestSplitLIneOnCharacter(unittest.TestCase):
    def test_split_line_on_char_before_preferred_pos(self):
        line = 'this is, a short line'
        result = merge._split_line_on_character(line, ',', 10, 3)
        self.assertTupleEqual(('this is,', 'a short line'), result)
        result = merge._split_line_on_character(line, ',', 10, 2)
        self.assertTupleEqual(('', line), result)

    def test_split_line_on_char_after_preferred_pos(self):
        line = 'this is a short, line'
        result = merge._split_line_on_character(line, ',', 10, 6)
        self.assertTupleEqual(('this is a short,', 'line'), result)
        result = merge._split_line_on_character(line, ',', 10, 5)
        self.assertTupleEqual(('', line), result)

    def test_split_exactly_on_preferred_pos(self):
        result = merge._split_line_on_character('this is an, short line', ',', 10, 4)
        self.assertTupleEqual(('this is an,', 'short line'), result)

    def test_default_deviation(self):
        result = merge._split_line_on_character('this is ,a bit of a longer line', ',', 16) # 32 chars
        self.assertTupleEqual(('this is ,', 'a bit of a longer line'), result)
        line = 'this is, a bit of a longer line'
        result = merge._split_line_on_character(line, ',', 16) # 32 chars
        self.assertTupleEqual(('', line), result)


class TestDocumentMerge(unittest.TestCase):
    def test_merge_doc(self):
        srt_text = open_doc('srt/merge_test.srt')()
        srt_doc = SrtDoc(srt_text)
        merged_doc = merge.MergedDoc(srt_doc)
        merged_text = merged_doc.text
        merged_doc.text = merged_text
        self.assertEqual(srt_text, str(srt_doc))
        # Just to ensure that we have completed the whole cycle,
        # a slightly changed merged text should not compare equal.
        srt_doc = SrtDoc(srt_text)
        merged_doc = merge.MergedDoc(srt_doc)
        merged_text = merged_doc.text
        merged_text = merged_text[:15] + 'xxx' + merged_text[18:]
        merged_doc.text = merged_text
        self.assertNotEqual(srt_text, str(srt_doc))