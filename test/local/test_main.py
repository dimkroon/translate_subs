# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from test.support import fixtures
fixtures.global_setup()

import os
import shutil
import unittest
from unittest.mock import MagicMock, patch


from resources.lib import manual
from test.support import testutils


def _create_test_dir():
    test_dir = testutils.doc_path('test_dir')
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.mkdir(test_dir)
    return test_dir


def listdir_mock(path):
    folders = []
    files = []
    for entry in os.listdir(path):
        if os.path.isdir(os.path.join(path, entry)):
            folders.append(entry)
        else:
            files.append(entry)
    return folders, files


@patch('xbmcvfs.listdir', new=listdir_mock)
class TestScanFolder(unittest.TestCase):
    def test_scan_folder_with_multiple_srt_files(self):
        test_dir = _create_test_dir()
        video_file_name = "my_video_file"

        # create some test files
        for i in range(4):
            fpath = os.path.join(test_dir, '{}-{}.srt'.format(video_file_name, i))
            with open(fpath, 'w') as f:
                f.write('aszdgfvsdf')

        result = list(main.scan_folder(test_dir, video_file_name + '.mov'))
        self.assertEqual(4, len(result))
