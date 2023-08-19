# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from test.support import fixtures
fixtures.global_setup()

import os
import unittest
from unittest.mock import patch

from resources.lib.subtitles import translate

from test.support.testutils import open_doc, doc_path


@patch("resources.lib.subtitles.translate.get_filter_flags", return_value=7)
class TranslateDoc(unittest.TestCase):
    def test_translate_atomic_blonde(self, p_get_filters):
        with patch("resources.lib.subtitles.translate.read_subtitles_file", new=open_doc('srt/atomic blonde.en.srt')):
            translated_fname = translate.translate_file('tst_file', 'blabla', 'srt', 'nl', 'en', -1)
        p_get_filters.assert_called_once_with(-1)
        self.assertTrue(os.path.isfile(translated_fname))