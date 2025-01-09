# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023-2025 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from test.support import fixtures
fixtures.global_setup()

import os
import time

from unittest import TestCase
from unittest.mock import patch

from resources.lib.translatesubs import translate
from resources.lib.translatesubs.subtitle import subtitle

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
        self.assertRaises(translate.UnknownLanguage, translate.get_language_id, 'nl_NL')
        self.assertRaises(translate.UnknownLanguage, translate.get_language_id, 'nl_nl')


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


class SplitText(TestCase):
    def test_split_doc(self):
        t = '12345678\n12345678\n12345678\n'
        s = translate.split_doc(t, 8)
        self.assertListEqual(['12345678', '12345678', '12345678',], s)

    def test_split_doc_without_trailing_newlines(self):
        t = '123\n456\n789\nabcd\nefg'
        s = translate.split_doc(t, 13)
        self.assertListEqual(['123\n456\n789', '\nabcd\nefg'], s)

    def test_split_doc_without_boundry_on_max_length(self):
        t = '123\n456\n789895\n'
        s = translate.split_doc(t, 10)
        self.assertListEqual(['123\n456', '\n789895\n'], s)

    def test_split_doc_with_extra_trailing_newline(self):
        t = '123\n\n456\n\n789895\n\n\n\n'
        s = translate.split_doc(t, 10)
        self.assertListEqual(['123\n\n456\n', '\n789895\n\n', '\n\n'], s)

    def test_split_doc_with_too_large_a_block(self):
        t = '123\n456\n1234567890'
        self.assertRaises(ValueError, translate.split_doc, t, 10)


class TranslateDocObject(TestCase):
    def test_def_create_obj(self):
        orig_subs = open_doc('srt/atomic blonde.en.srt')()
        orig_doc = subtitle.SrtDoc(orig_subs)
        self.assertIsInstance(orig_doc, subtitle.SrtDoc)
        text = orig_doc.text
        # save_doc(orig_doc.text, 'srt/subs_brackets_orig.txt')
        self.assertIsInstance(text, str)

    def test_filtered_file(self):
        srt = open_doc('srt/atomic blonde.en.srt')()
        filtered_doc = translate.filter_doc(srt, translate.FILTER_CAPS | translate.FILTER_BRACKETS | translate.FILTER_HASHTAGS)
        doc_obj = subtitle.SrtDoc(filtered_doc)
        doc_text = doc_obj.text
        self.assertTrue('\n\n' in doc_text)


@patch("resources.lib.translatesubs.translate.translate_file", new=open_doc('srt/merge_test.srt'))
class TranslateFileCache(TestCase):
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
        self.assertEqual(result, test_doc)

    def test_filter_space_on_separating_lines(self):
        """ Some srt docs have a space on the line that separates blocks.
        We rely on blocks being separated by a double newline, so filter will by default
        remove those spaces
        """
        test_doc = 'line 1\n \nline 2'
        result = translate.filter_doc(test_doc)
        self.assertEqual(result, 'line 1\n\nline 2')

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

    def test_filter_asterisk(self):
        flags = translate.FILTER_ASTERISK
        srt = '1\n* I Love You *\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n* I Love You\n* so much *\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n*I Love You\n* so much*\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n* I Love You\n\n2\n so much *\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '\n<font color="*ffffff">* I Love You</font>\n<font color="*ffffff"> so much *</font>\n'
        self.assertEqual('\n<font color="*ffffff"> </font>\n', translate.filter_doc(srt, flags))

    def test_filter_music_note(self):
        flags = translate.FILTER_MUSIC_NOTE
        srt = '1\n♪ I Love You ♪\n\n2\nthis is a string'
        self.assertEqual('1\n \n\n2\nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n♪ I Love You\n♪ so much ♪\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n♪I Love You\n♪ so much♪\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '1\n♪ I Love You\n\n2\n so much ♪\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))
        srt = '\n<font color="♪ffffff">♪ I Love You</font>\n<font color="♪ffffff"> so much ♪</font>\n'
        self.assertEqual('\n<font color="♪ffffff"> </font>\n', translate.filter_doc(srt, flags))

    def test_filter_all_lyrics(self):
        flags = (translate.FILTER_HASHTAGS | translate.FILTER_ASTERISK | translate.FILTER_MUSIC_NOTE)
        srt = '1\n♪ I Love You #\n'
        self.assertEqual('1\n♪ I Love You #\n', translate.filter_doc(srt, flags))
        srt = '1\n♪ I Love my #1 ♪\n'
        self.assertEqual('1\n \n', translate.filter_doc(srt, flags))
        srt = '1\n♪ I Love **\n\n2\n #14 times ♪\nthis is a string'
        self.assertEqual('1\n \nthis is a string', translate.filter_doc(srt, flags))

    def test_filter_all(self):
        flags = (translate.FILTER_BRACKETS | translate.FILTER_CAPS | translate.FILTER_HASHTAGS |
                 translate.FILTER_ASTERISK | translate.FILTER_MUSIC_NOTE )
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


class TestReadSubtitles(TestCase):
    def test_read_file(self):
        for f_name in ('atomic blonde.en.srt', 'Auf dem Grund.de.srt'):
            f_path = doc_path('srt/' + f_name)
            subs = translate.read_subtitles_file(f_path)
            self.assertIsInstance(subs, str)
            self.assertGreater(len(subs), 1000)

    def test_universal_newlines(self):
        doc = "1\n\n2\r\r3\r\n\r\n4"
        with patch('xbmcvfs.File', spec=True) as mocked_file:
            mocked_file.return_value.__enter__.return_value.read.return_value = doc
            subs = translate.read_subtitles_file('test doc')
        self.assertEqual(subs, '1\n\n2\n\n3\n\n4')
