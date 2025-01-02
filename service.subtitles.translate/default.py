# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2025 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import sys

import xbmc
import xbmcaddon

from resources.lib.translatesubs import utils


if __name__ == '__main__':
    xbmc.log("[translatepy] called with :{}".format(sys.argv), xbmc.LOGWARNING)
    if len(sys.argv) == 1:
        xbmcaddon.Addon().openSettings()
    elif len(sys.argv) == 2:
        if sys.argv[1] == 'mark_error':
            utils.mark_error()
