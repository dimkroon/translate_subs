# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations

import json
import logging
import os


import xbmc
import xbmcgui
from xbmcvfs import translatePath
import xbmcaddon


__version__ = "0.2.0"


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


def mark_error():
    from datetime import datetime
    import shutil

    player = xbmc.Player()
    try:
        playing_file = player.getPlayingFile()
        play_time = player.getTime()
        orig_subs = player.getPlayingItem().getProperty('subtitles.translate.file')
    except (RuntimeError, OSError):
        return

    if not orig_subs or not playing_file:
        return

    try:
        with open(os.path.join(addon_info.profile, 'subtitles', 'last_translation'), 'r') as f:
            translated_subs = f.read().strip()
    except FileNotFoundError:
        translated_subs = ''

    current_dt = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    error_dir = os.path.join(addon_info.profile, 'errors', current_dt)
    os.makedirs(error_dir, exist_ok=True)

    shutil.copy(orig_subs, error_dir)
    # shutil.copy(translated_subs, error_dir)
    try:
        shutil.copy(os.path.join(addon_info.profile, 'subtitles', 'orig.txt'), error_dir)
        shutil.copy(os.path.join(addon_info.profile, 'subtitles', 'srt_filtered.txt'), error_dir)
        shutil.copy(os.path.join(addon_info.profile, 'subtitles', 'translated.txt'), error_dir)
        source = 'web'
    except FileNotFoundError:
        source = 'cache'

    try:
        shutil.copy(translated_subs, error_dir)
    except OSError:
        pass

    with open(os.path.join(error_dir, 'manifest.json'), 'w') as f:
        json.dump({'video_file': playing_file,
                   'playtime': play_time,
                   'orig_subs': orig_subs,
                   'translated_subs': translated_subs,
                   'source': source,
                   'version': __version__},
                  f, indent=4)

    xbmcgui.Dialog().notification(addon_info.localise(30100),
                                  addon_info.localise(30901),
                                  sound=False)
