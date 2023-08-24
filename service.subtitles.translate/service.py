# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------
import os.path
import threading

import xbmc
from xbmc import Player, Monitor

from resources.lib import addon_log
from resources.lib import utils
from resources.lib.subtitles import translate


logger = addon_log.logging.getLogger('.'.join((utils.logger_id, __name__.split('.', 2)[-1])))

INDENT = ' ' * 60


class PlayerMonitor(Player):
    def __init__(self):
        super(PlayerMonitor, self).__init__()
        self.monitor = Monitor()
        self._cur_file = None

    def onAVStarted(self) -> None:
        # noinspection PyBroadException
        logger.debug("onAVStarted, playing file\n"
                     "%s file: %s\n"
                     "%s video streams: %s\n"
                     "%s audio streams: %s\n"
                     "%s subtitles: %s",
                     INDENT, self.getPlayingFile(),
                     INDENT, self.getAvailableVideoStreams(),
                     INDENT, self.getAvailableAudioStreams(),
                     INDENT, self.getSubtitles())

        li = self.getPlayingItem()
        file_name = li.getProperty('subtitles.translate.file')
        if not file_name:
            return

        utils.addon_info.initialise()
        if not utils.addon_info.addon.getSettingBool('subtitles_translate'):
            logger.debug("Automatic translation disabled in settings.")
            return

        base_name, file_extension = os.path.splitext(file_name)
        subs_type = li.getProperty('subtitles.translate.type')
        orig_lang = li.getProperty('subtitles.translate.orig_lang')
        filter_flags = li.getProperty('subtitles.translate.filter_flags')

        logger.info("Property file: '%s'", file_name)
        logger.info("Property type: '%s'", subs_type)
        logger.info("Property original language: '%s'", orig_lang)
        logger.info("Property filter_flags: '%s'", filter_flags)

        if not subs_type:
            subs_type = file_extension
        if subs_type not in translate.supported_types:
            logger.info("Unsupported subtitle type '%s'", subs_type)
            return

        # Get the original langauge by property, or by a langauge id in the filename. Default to 'auto'
        if not orig_lang:
            orig_lang = os.path.splitext(base_name)[1] or 'auto'

        try:
            filter_flags = int(filter_flags)
        except ValueError:
            filter_flags = -1

        # Strip the querystring from the video url, because it may contain items unique to every instance played.
        video_file = self.getPlayingFile().split('?')[0]

        logger.info("Subtitles file: '%s'", file_name)
        logger.info("Subtitles type: '%s'", subs_type)
        logger.info("Subtitles original language: '%'", orig_lang)
        logger.info("Subtitles filter_flags: '%s'", filter_flags)
        logger.info("Video ID: %s", video_file)

        translated_fname = translate.translate_file(video_file, file_name, subs_type,
                                                    src_lang=orig_lang, filter_flags=filter_flags)
        if not translated_fname:
            return
        # Translating can take some time, check if the file is still playing
        if video_file not in self.getPlayingFile():
            logger.info("Abort. It looks like another file has been started while translation was in progress.")
            return
        logger.debug("Using translated subtitles: '%s'", translated_fname)
        self.setSubtitles(translated_fname)


if __name__ == '__main__':
    logger.debug("Running translate service from thead %s", threading.current_thread().native_id)
    translate.cleanup_cached_files()
    system_monitor = xbmc.Monitor()
    while system_monitor.abortRequested() is False:
        try:
            player = PlayerMonitor()
            while system_monitor.abortRequested() is False:
                system_monitor.waitForAbort(86400)
                translate.cleanup_cached_files()
        except Exception as e:
            logger.error("Unhandled exception: %r:", e, exc_info=True)
