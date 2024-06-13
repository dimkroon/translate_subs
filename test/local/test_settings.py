# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from test.support import fixtures
fixtures.global_setup()

import logging as py_logging

import unittest
from unittest.mock import MagicMock, patch

from resources.lib import settings
from resources.lib import addon_log


class TestSettings(unittest.TestCase):
    @patch("resources.lib.addon_log.set_log_handler")
    def test_change_logger(self, p_set_log):
        logger = addon_log.logger

        with patch("resources.lib.kodi_utils.ask_log_handler", return_value=(0, 'kodi log')):
            settings.change_logger()
            p_set_log.assert_called_with(addon_log.KodiLogHandler)

        with patch("resources.lib.kodi_utils.ask_log_handler", return_value=(1, 'file log')):
            settings.change_logger()
            p_set_log.assert_called_with(addon_log.CtFileHandler)

        with patch("resources.lib.kodi_utils.ask_log_handler", return_value=(2, 'no log')) as p_ask:
            with patch.object(logger, 'handlers', new=[addon_log.CtFileHandler()]):
                settings.change_logger()
                p_set_log.assert_called_with(addon_log.DummyHandler)
                p_ask.assert_called_with(1)

        # Test default values passed to ask_log_handler().
        # logger not properly initialised
        with patch("resources.lib.kodi_utils.ask_log_handler", return_value=(1, 'file log')) as p_ask:
            with patch.object(logger, 'handlers', new=[]):
                settings.change_logger()
                p_ask.assert_called_with(0)

        # Current handler is of an unknown type
        with patch("resources.lib.kodi_utils.ask_log_handler", return_value=(1, 'file log')):
            with patch.object(logger, 'handlers', new=[py_logging.Handler()]):
                settings.change_logger()
                p_ask.assert_called_with(0)
