# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
import logging
import os


import xbmc
from xbmcvfs import translatePath
import xbmcaddon


class AddonInfo:
    def __init__(self):
        self.initialise()
        self.name = self.addon.getAddonInfo("name")
        self.id = self.addon.getAddonInfo("id")
        self.profile = translatePath(self.addon.getAddonInfo('profile'))
        self.addon_dir = os.path.join(translatePath('special://home'), self.id)
        self.temp_dir = os.path.join(translatePath('special://temp'), 'translated_subs')
        os.makedirs(self.temp_dir, exist_ok=True)

    # noinspection PyAttributeOutsideInit
    def initialise(self):
        self.addon = addon = xbmcaddon.Addon()
        self.localise = addon.getLocalizedString


addon_info = AddonInfo()
logger_id = addon_info.name.replace(' ', '-').replace('.', '-')
logger = logging.getLogger(logger_id + '.utils')


def get_os():
    import platform
    return platform.system(), platform.machine()


def log(message, *args, **kwargs):
    xbmc.log('[subtitles.translate] ' + message.format(*args, **kwargs), xbmc.LOGDEBUG)

