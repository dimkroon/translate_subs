
# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------


from test.support import fixtures
fixtures.global_setup()

from unittest import TestCase

from resources.lib import utils

from test.support.testutils import doc_path


setUpModule = fixtures.setup_local_tests
tearDownModule = fixtures.tear_down_local_tests


class Generic(TestCase):
    def test_addon_info(self):
        info = utils.addon_info
        info.initialise()
        for attr_name in ('addon', 'name', 'id', 'localise', 'profile'):
            self.assertTrue(hasattr(info, attr_name))

    def test_get_os(self):
        cur_os = utils.get_os()
        self.assertIsInstance(cur_os, tuple)
        self.assertEqual(2, len(cur_os))
