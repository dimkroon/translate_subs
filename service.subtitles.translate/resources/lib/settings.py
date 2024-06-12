# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import logging

from resources.lib import kodi_utils
from resources.lib import addon_log
from resources.lib import utils

logger = logging.getLogger('.'.join((utils.logger_id, __name__)))


def change_logger():
    """Callback for settings->generic->log_to.
    Let the user choose between logging to kodi log, to our own file, or no logging at all.

    """
    handlers = (addon_log.KodiLogHandler, addon_log.CtFileHandler, addon_log.DummyHandler)

    try:
        curr_hndlr_idx = handlers.index(type(addon_log.logger.handlers[0]))
    except (ValueError, IndexError):
        curr_hndlr_idx = 0

    new_hndlr_idx, handler_name = kodi_utils.ask_log_handler(curr_hndlr_idx)
    handler_type = handlers[new_hndlr_idx]

    addon_log.set_log_handler(handler_type)
    utils.addon_info.addon.setSetting('log-handler', handler_name)


def clear_cache():
    pass