# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import logging

import xbmc
from codequick import run as cc_run
from codequick import route

from resources.lib import utils
from resources.lib import settings


logger = logging.getLogger(utils.logger_id + '.main')
logger.critical('-------------------------------------')
logger.critical('--- version: %s', utils.addon_info.addon.getAddonInfo('version'))


TXT_SEARCH = 30807
TXT_NO_ITEMS_FOUND = 30608
TXT_PLAY_FROM_START = 30620
TXT_PREMIUM_CONTENT = 30622

def run():
    import sys
    sys.argv.insert(1, '99999')
    xbmc.log("[translatepy] called with :{}".format(sys.argv), xbmc.LOGWARNING)
    cc_run()


