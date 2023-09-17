# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023 Dimitri Kroon.
#  This file is part of plugin.video.viewx.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from test.support import fixtures
fixtures.global_setup()

import os
import time

from unittest import TestCase
from unittest.mock import patch

from resources.lib.subtitles import translate
from resources.lib.subtitles import subtitle

from test.support.testutils import doc_path, open_doc, save_doc


setUpModule = fixtures.setup_local_tests
tearDownModule = fixtures.tear_down_local_tests


class General(TestCase):
    def test_constants(self):
        subs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../addon_profile_dir/subtitles'))
        self.assertEqual(subs_dir, translate.SUBS_CACHE_DIR)

    def test_get_language_id(self):
        self.assertEqual('nld', translate.get_language_id('Dutch'))
        self.assertEqual('nld', translate.get_language_id('dutch'))
        self.assertEqual('nld', translate.get_language_id('nl'))
        self.assertEqual('nld', translate.get_language_id('nld'))
        self.assertRaises(translate.TranslatepyException, translate.get_language_id, 'nl_NL')
        self.assertRaises(translate.TranslatepyException, translate.get_language_id, 'nl_nl')


class AaTestCleanCache(TestCase):
    def test_01_clean_cache(self):
        """Since we rely on this function in some classes' setUp(), this is the first test to run.

        """
        # Ensure dir exists, should have been made by the module if it didn't before importing translate.
        self.assertTrue(os.path.isdir(translate.SUBS_CACHE_DIR))
        # clear the directory
        for item in os.listdir(translate.SUBS_CACHE_DIR):
            # There should not be subdirectories
            fullpath = os.path.join(translate.SUBS_CACHE_DIR, item)
            self.assertTrue(os.path.isfile(fullpath))
            os.remove(fullpath)
        # create test file
        test_file = os.path.join(translate.SUBS_CACHE_DIR, 'test_file')
        with open(test_file, 'w') as f:
            f.write("this is a test")
        # Wait a little because ctime may not have a resolution smaller than 1 second.
        time.sleep(1.1)
        self.assertTrue(os.path.isfile(test_file))
        translate.cleanup_cached_files()        # using default cache time (60 days).
        self.assertTrue(os.path.isfile(test_file))
        translate.cleanup_cached_files(max_age=0)
        self.assertFalse(os.path.exists(test_file))


class MergeSentences(TestCase):
    def test_merge_real_doc(self):
        orig_srt = open_doc('srt/atomic blonde.en.srt')()
        doc_object = subtitle.SrtDoc(orig_srt)
        orig_sentences = '\n'.join(s for s in doc_object.sentences())
        print (orig_sentences)


class TransTagged(TestCase):
    def test_parse_tagged(self):
        text = """
<a b=1 l=0>(TV clicks on) </a><a b=2 l=0>RONALD REAGAN: </a><a b=2 l=0>East and West </a><a b=3 l=0>do not mistrust each other </a><a b=3 l=0>because we're armed. </a>
<a b=4 l=0>We're armed because </a><a b=4 l=0>we mistrust each other. </a>
<a b=5 l=0>Mr. Gorbachev, </a><a b=6 l=0>tear down this wall. </a>
<a b=7 l=0>(cheering and applause) </a><a b=8 l=0>("Blue Monday '88" </a><a b=8 l=0>by New Order plays) </a><a b=9 l=0>(grunting and panting) </a><a b=10 l=0>-(grunting) </a><a b=10 l=0>-(tires squealing nearby) </a><a b=11 l=0>## # </a><a b=12 l=0>(tires squealing) </a><a b=13 l=0>(grunting) </a><a b=14 l=0>## How does it feel # </a><a b=15 l=0>## To treat me like you do? # </a><a b=16 l=0>(yells, grunts) </a><a b=17 l=0>## When you've laid your hands </a><a b=17 l=0>upon me # </a><a b=18 l=0>-(engine revving) </a><a b=18 l=0>-## And told me who you are # </a><a b=19 l=0>(tires squealing) </a><a b=20 l=0>-(yelling) </a><a b=20 l=0>-## I thought I was mistaken # </a><a b=21 l=0>## I thought I heard # </a><a b=22 l=0>-## Your words # </a><a b=22 l=0>-(yelling in pain) </a><a b=23 l=0>## Tell me, how </a><a b=23 l=0>do I feel? # </a><a b=24 l=0>(playing over car stereo): </a><a b=24 l=0>## Tell me now, how do... # </a><a b=25 l=0>MAN (laughing): </a><a b=25 l=0>James fucking Gascoigne. </a>
<a b=26 l=0>How did you find me? </a>
<a b=27 l=0>Maybe you're not as good </a><a b=27 l=0>at this spy shit as you think. </a>
<a b=28 l=0>It was Satchel, wasn't it? </a>"""
        td = subtitle.TransDoc(text, html=True)
        td.blocks

    def test_parse_whole_tagged_file(self):
        trans_txt = open_doc('translated/aromic blonde_tagged_3.nld.txt')()
        td = subtitle.TransDoc(trans_txt, html=True)
        self.assertGreater(len(td.blocks), 100)


class SplitText(TestCase):
    def test_split_srt_doc(self):
        t = '123\n\n456\n\n789\n\nabcd\n\nefg\n\n'
        s = translate.split_srt_doc(t, 13)
        self.assertListEqual(['123\n\n456', '\n\n789\n\nabcd','\n\nefg\n\n'], s)

    def test_split_srt_doc_without_trailing_newlines(self):
        t = '123\n\n456\n\n789\n\nabcd\n\nefg'
        s = translate.split_srt_doc(t, 13)
        self.assertListEqual(['123\n\n456', '\n\n789\n\nabcd','\n\nefg'], s)

    def test_split_srt_doc_without_boundry_on_max_length(self):
        t = '123\n\n456\n\n789895\n\n'
        s = translate.split_srt_doc(t, 10)
        self.assertListEqual(['123\n\n456', '\n\n789895\n\n'], s)

    def test_split_srt_doc_with_extra_trailing_newline(self):
        t = '123\n\n456\n\n789895\n\n\n\n'
        s = translate.split_srt_doc(t, 10)
        self.assertListEqual(['123\n\n456', '\n\n789895', '\n\n\n\n'], s)

    def test_split_srt_doc_with_too_large_block(self):
        t = '123\n\n456\n\n123456789'
        self.assertRaises(ValueError, translate.split_srt_doc, t, 10)


class TestSrtLine(TestCase):
    def test_text_line(self):
        txt = 'This is text'
        l = translate.SrtLine('', txt, '')
        self.assertEqual('', l.lead)
        self.assertEqual(txt, l.text)
        self.assertEqual('', l.tail)

    def test_text_with_colour(self):
        txt = 'This is text'
        l = translate.SrtLine('<font color="cyan">', txt, '</font>')
        self.assertEqual('<font color="cyan">', l.lead)
        self.assertEqual(txt, l.text)
        self.assertEqual('</font>', l.tail)

    def test_line_strips_whitespace(self):
        l = translate.SrtLine('', ' This is text  ', '')
        self.assertEqual('This is text', l.text)
        l = translate.SrtLine('<font color="cyan">', ' This is text ', '</font>')
        self.assertEqual('This is text', l.text)

    def test_text_without_lead(self):
        txt = 'This is text'
        tail = '</font>'
        l = translate.SrtLine('', txt, tail)
        self.assertEqual('', l.lead)
        self.assertEqual(txt + tail, l.text)
        self.assertEqual('', l.tail)

    def test_text_without_tail(self):
        lead = '<i>'
        txt = 'This is text'
        l = translate.SrtLine(lead, txt, '')
        self.assertEqual('', l.lead)
        self.assertEqual(lead + txt, l.text)
        self.assertEqual('', l.tail)


class SrtBlock(TestCase):
    def test_block_single_line(self):
        t = '101\n00:07:17,960 --> 00:07:18,960\nYeah.'
        b = translate.SrtBlock(t)
        self.assertEqual(1, len(b.lines))
        self.assertEqual('Yeah.', b.lines[0].text)

    def test_block_multiline(self):
        t = '101\n00:07:17,960 --> 00:07:18,960\nYeah.\n<font color="blue">duh</font>'
        b = translate.SrtBlock(t)
        self.assertEqual(2, len(b.lines))
        self.assertEqual('Yeah.', b.lines[0].text)
        self.assertEqual('duh', b.lines[1].text)

    def test_block_with_empty_lines(self):
        t = '101\n00:07:17,960 --> 00:07:18,960\n\n'
        b = translate.SrtBlock(t)
        self.assertEqual(0, len(b.lines))
        t = '101\n00:07:17,960 --> 00:07:18,960\n\nYeah.'
        b = translate.SrtBlock(t)
        self.assertEqual(1, len(b.lines))
        self.assertEqual('Yeah.', b.lines[0].text)

    def test_block_with_lines_of_whitespace(self):
        t = '101\n00:07:17,960 --> 00:07:18,960\n  \n \n'
        b = translate.SrtBlock(t)
        self.assertEqual(0, len(b.lines))
        t = '101\n00:07:17,960 --> 00:07:18,960\n  \nYeah.'
        b = translate.SrtBlock(t)
        self.assertEqual(1, len(b.lines))
        self.assertEqual('Yeah.', b.lines[0].text)
        t = '101\n00:07:17,960 --> 00:07:18,960\nYeah.  \n'
        b = translate.SrtBlock(t)
        self.assertEqual(1, len(b.lines))
        self.assertEqual('Yeah.', b.lines[0].text)

    def test_block_with_inline_markup(self):
        t = '101\n00:07:17,960 --> 00:07:18,960\nBut this is <i>magic</i>.'
        b = translate.SrtBlock(t)
        self.assertEqual(1, len(b.lines))
        self.assertEqual('But this is <i>magic</i>.', b.lines[0].text)

    def test_bool(self):
        """Block without lines evaluate to False."""
        t = '101\n00:07:17,960 --> 00:07:18,960\nBut this is magic.'
        b = translate.SrtBlock(t)
        self.assertTrue(b)
        t = '101\n00:07:17,960 --> 00:07:18,960\n \n '
        b = translate.SrtBlock(t)
        self.assertFalse(b)


class TranslateDocObject(TestCase):
    def test_def_create_obj(self):
        orig_subs = open_doc('srt/atomic blonde.en.srt')()
        orig_doc = translate.SrtDoc(orig_subs)
        self.assertIsInstance(orig_doc, translate.SrtDoc)
        text = orig_doc.text
        # save_doc(orig_doc.text, 'srt/subs_brackets_orig.txt')
        self.assertIsInstance(text, str)

    def test_filtered_file(self):
        srt = open_doc('srt/atomic blonde.en.srt')()
        filtered_doc = translate.filter_doc(srt, translate.FILTER_CAPS | translate.FILTER_BRACKETS | translate.FILTER_HASHTAGS)
        doc_obj = translate.SrtDoc(filtered_doc)
        doc_text = doc_obj.text
        self.assertTrue('\n\n' in doc_text)


@patch("resources.lib.subtitles.translate.translate_file", new=open_doc('srt/orig_nl.txt'))
class TranslateFile(TestCase):
    def setUp(self) -> None:
        translate.cleanup_cached_files(0)

    def test_translate_file(self,):
        prod_id = '10_1822.001'
        trans_file_name = translate.translate_file(prod_id, doc_path('srt/subtitles.srt'), 'nl', 'en')
        self.assertTrue(os.path.basename(trans_file_name).startswith(prod_id))
        self.assertTrue(os.path.isfile(trans_file_name))

    def test_reserved_characters_in_production_id(self,):
        """Reserved characters in `production_id` are percent encoded in the file name"""
        prod_id = '10:1822/Afd556#001'
        trans_file_name = translate.translate_file(prod_id, doc_path('srt/subtitles.srt'), 'nl', 'en')
        self.assertFalse(os.path.basename(trans_file_name).startswith(prod_id))
        self.assertEqual(3, trans_file_name.count('%'))
        self.assertTrue(os.path.isfile(trans_file_name))

    def test_file_with_sounds_descriptions_in_brackets(self):
        prod_id = '10_1822.002'
        trans_file_name = translate.translate_file(prod_id, doc_path('srt/subs_brackets.srt'), 'nl', 'en',
                                                   filter_flags=translate.FILTER_BRACKETS)
        self.assertTrue(os.path.basename(trans_file_name).startswith(prod_id))
        self.assertTrue(os.path.isfile(trans_file_name))


class FilterDoc(TestCase):
    def test_no_filter(self):
        # Without filter the original document is returned
        test_doc = """
1
00:03:20,960 --> 00:03:22,960
You'd be the best charge of that.

2
00:06:18,160 --> 00:06:21,960
(gears clicking) (bell tolling)

3
00:07:32,960 --> 00:07:33,960
DOOR SLAMS

4
00:07:43,960 --> 00:07:46,960
Oh damn. (phone ringing)
"""
        result = translate.filter_doc(test_doc)
        self.assertIs(result, test_doc)

    def test_filter_brackets(self):
        srt = '1\n(Door slamed)\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, translate.FILTER_BRACKETS))
        srt = '\noh (grunted)\n'
        self.assertEqual('\noh  \n', translate.filter_doc(srt, translate.FILTER_BRACKETS))
        srt = '\n(grunted) (rings)\n'
        self.assertEqual(' \n', translate.filter_doc(srt, translate.FILTER_BRACKETS))
        srt = '\n(whispers):\nhow are you?\n'
        self.assertEqual(' \nhow are you?\n', translate.filter_doc(srt, translate.FILTER_BRACKETS))
        srt = '\n<font color="#ffffff">(whispers)</font>\n'
        self.assertEqual('\n<font color="#ffffff"> </font>\n', translate.filter_doc(srt, translate.FILTER_BRACKETS))

    def test_filter_all_caps(self):
        srt = '1\nDOOR SLAMMED\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, translate.FILTER_CAPS))
        srt = '\noh GRUNTED\n'
        self.assertEqual('\noh GRUNTED\n', translate.filter_doc(srt, translate.FILTER_CAPS))
        srt = '\nGRUNTED RINGS\n'
        self.assertEqual(' \n', translate.filter_doc(srt, translate.FILTER_CAPS))
        srt = '\nGRUNTED, RINGS:\n'
        self.assertEqual(' \n', translate.filter_doc(srt, translate.FILTER_CAPS))
        srt = '\n<font color="#ffffff">GRUNTED</font>\n'
        self.assertEqual('\n<font color="#ffffff"> </font>\n', translate.filter_doc(srt, translate.FILTER_CAPS))
        srt = '\nMAN: <font color="#ffffff">What is this?</font>\n'
        self.assertEqual('\n <font color="#ffffff">What is this?</font>\n', translate.filter_doc(srt, translate.FILTER_CAPS))
        srt = '<font color="#ffffff">What is this?</font> SHOUTING\n'
        self.assertEqual('<font color="#ffffff">What is this?</font> \n', translate.filter_doc(srt, translate.FILTER_CAPS))

    def test_filter_both(self):
        flags = translate.FILTER_BRACKETS | translate.FILTER_CAPS
        srt = '1\nDOOR SLAMMED\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n(Door slamed)\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, flags))
        srt = '\noh (grunted)\n'
        self.assertEqual('\noh  \n', translate.filter_doc(srt, flags))
        srt = '\noh GRUNTED\n'
        self.assertEqual('\noh GRUNTED\n', translate.filter_doc(srt, flags))
        srt = '\n(grunted) (rings)\n'
        self.assertEqual(' \n', translate.filter_doc(srt, flags))
        srt = '\nGRUNTED RINGS\n'
        self.assertEqual(' \n', translate.filter_doc(srt, flags))

    def test_filter_hashtags(self):
        flags = translate.FILTER_HASHTAGS
        srt = '1\n# I Love You #\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n# I Love You\n# so much #\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n#I Love You\n# so much#\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n# I Love You\n\n2\n so much #\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '\n<font color="#ffffff"># I Love You</font>\n<font color="#ffffff"> so much #</font>\n'
        self.assertEqual('\n<font color="#ffffff"> </font>\n', translate.filter_doc(srt, flags))

    def test_filter_all(self):
        flags = translate.FILTER_BRACKETS | translate.FILTER_CAPS | translate.FILTER_HASHTAGS
        srt = '1\nDOOR SLAMMED\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n(Door slamed)\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, flags))
        srt = '\noh (grunted)\n'
        self.assertEqual('\noh  \n', translate.filter_doc(srt, flags))
        srt = '\noh GRUNTED\n'
        self.assertEqual('\noh GRUNTED\n', translate.filter_doc(srt, flags))
        srt = '\n(grunted) (rings)\n'
        self.assertEqual(' \n', translate.filter_doc(srt, flags))
        srt = '\nGRUNTED RINGS\n'
        self.assertEqual(' \n', translate.filter_doc(srt, flags))
        srt = '\nMAN: <font color="#ffffff">What is this?</font>\n'
        self.assertEqual('\n <font color="#ffffff">What is this?</font>\n', translate.filter_doc(srt, translate.FILTER_CAPS))
        srt = '''

1
00:00:26,960 --> 00:00:28,960
LILY THOMAS: <font color="yellow">January the 8th, 1963.</font>
'''
        self.assertEqual('\n1\n00:00:26,960 --> 00:00:28,960\n <font color="yellow">January the 8th, 1963.</font>\n',
                         translate.filter_doc(srt, translate.FILTER_CAPS))

    def test_filter_whole_file(self):
        # srt_doc = open_doc('srt/atomic blonde.en.srt')()
        srt_doc = open_doc('srt/spy_among_friends.en.srt')()
        filtered = translate.filter_doc(srt_doc, translate.FILTER_CAPS)
        filtered = translate.filter_doc(srt_doc, translate.FILTER_BRACKETS)
        filtered = translate.filter_doc(srt_doc, translate.FILTER_HASHTAGS)
        filtered = translate.filter_doc(srt_doc, translate.FILTER_COLOURS)
        filtered = translate.filter_doc(srt_doc,
                                        translate.FILTER_HASHTAGS |
                                        translate.FILTER_CAPS |
                                        translate.FILTER_BRACKETS |
                                        translate.FILTER_COLOURS)
        print(filtered)
