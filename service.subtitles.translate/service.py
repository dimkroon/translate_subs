# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------
import os.path
import threading

import xbmc
import xbmcgui
from xbmc import Player, Monitor
from resources.lib.translatepy import Language

from resources.lib import addon_log
from resources.lib import utils
from resources.lib import kodi_utils
from resources.lib.subtitles import translate


logger = addon_log.logging.getLogger('.'.join((utils.logger_id, __name__.split('.', 2)[-1])))

INDENT = ' ' * 60


class PlayerMonitor(Player):
    def __init__(self):
        super(PlayerMonitor, self).__init__()
        self.monitor = Monitor()
        self._cur_file = None
        self._subtitles_may_be_downloaded = False

    def onAVStarted(self) -> None:
        self._execute_subtitles_translation()

    def onPlayBackPaused(self) -> None:
        if utils.addon_info.addon.getSettingBool('run_on_pause'):
            if xbmc.getCondVisibility('Window.IsActive(subtitlesearch)'):
                logger.debug("Paused for subtitles selection. Skipping execution as most likely correct subtitles will be downloaded")
                self._subtitles_may_be_downloaded = True
            else:
                self._execute_subtitles_translation()
    
    def onPlayBackResumed(self) -> None:
        if utils.addon_info.addon.getSettingBool('run_on_pause') and self._subtitles_may_be_downloaded:
            self._subtitles_may_be_downloaded = False
            self._execute_subtitles_translation()

        

    def _execute_subtitles_translation(self) -> None:
        # noinspection PyBroadException
        logger.debug("_execute_subtitles_translation, playing file\n"
                     "%s file: %s\n"
                     "%s video streams: %s\n"
                     "%s audio streams: %s\n"
                     "%s subtitle streams: %s\n"
                     "%s subtitles: %s",
                     INDENT, self.getPlayingFile(),
                     INDENT, self.getAvailableVideoStreams(),
                     INDENT, self.getAvailableAudioStreams(),
                     INDENT, self.getAvailableSubtitleStreams(),
                     INDENT, self.getSubtitles())
            
        utils.addon_info.initialise()
        if not utils.addon_info.addon.getSettingBool('subtitles_translate'):
            logger.debug("Automatic translation disabled in settings.")
            return
        preferred_lang = Language(kodi_utils.get_preferred_subtitle_lang()).id

        li = self.getPlayingItem()
        file_name = li.getProperty('subtitles.translate.file')
        if not file_name:
            file_name = f"{os.path.splitext(self.getPlayingFile())[0]}.{Language(self.getSubtitles()).alpha2}.srt"
            logger.debug(f"file_name is empty. Trying to find '{file_name=}' in the movie's directory")
            if not os.path.exists(file_name):
                logger.debug(f"The {file_name=} does not exist")
                return

        if preferred_lang != self.getSubtitles():
            logger.debug(f"Language of active subtitles {self.getSubtitles()} differs from {preferred_lang=}. Asking user input")
            if not xbmcgui.Dialog().yesno("Translate subtitles?", f"The current active subtitle language {self.getSubtitles()} differs from preferred {preferred_lang}. Translate?"):
                logger.debug("User does not want to translate")
                return
            logger.debug("User wants translation")
        else:
            logger.debug("Already in expected language")
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
            orig_lang = self.getSubtitles()
            logger.debug(f"Original language not detected. Assuming {orig_lang}")

        try:
            filter_flags = int(filter_flags)
        except ValueError:
            filter_flags = -1

        # Strip the querystring from the video url, because it may contain items unique to every instance played.
        video_file = self.getPlayingFile().split('?')[0]
        preferred_display_time = utils.addon_info.addon.getSettingNumber('display_time')

        logger.info("Subtitles file: '%s'", file_name)
        logger.info("Subtitles type: '%s'", subs_type)
        logger.info("Subtitles original language: '%s'", orig_lang)
        logger.info("Subtitles filter_flags: '%s'", filter_flags)
        logger.info("Video ID: %s", video_file)
        logger.info("Display time: %s", preferred_display_time)

        xbmcgui.Dialog().notification("Auto Translate Subtitles", f"Translation starting {orig_lang}", xbmcgui.NOTIFICATION_INFO, 5000)
        translated_fname = translate.translate_file(video_file, file_name, subs_type,
                                                    src_lang=orig_lang, filter_flags=filter_flags,
                                                    display_time=preferred_display_time)
        if not translated_fname:
            logger.debug("No translated file name. Exit")
            xbmcgui.Dialog().notification("Auto Translate Subtitles", "Translation failed.", xbmcgui.NOTIFICATION_ERROR, 5000)
            return
        else:
            logger.debug(f"Loading file {translated_fname=}")
            xbmcgui.Dialog().notification("Auto Translate Subtitles", f"Loading file {translated_fname=}", xbmcgui.NOTIFICATION_INFO, 5000)
        # Translating can take some time, check if the file is still playing
        if video_file not in self.getPlayingFile():
            logger.info("Abort. It looks like another file has been started while translation was in progress.")
            return
        # it is also possible that other subtitle of the desired target language as downloaded meanwhile
        if preferred_lang == self.getSubtitles():
            logger.info("Abort. Subtitles of the desired language are already active. It is possible that other subtitle of the desired target language as downloaded meanwhile")
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
                logger.info("Abort requested")
                translate.cleanup_cached_files()
        except Exception as e:
            logger.error("Unhandled exception: %r:", e, exc_info=True)
    logger.info("Ended service")