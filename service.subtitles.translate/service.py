# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023-2025 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------
import os.path
import threading

from resources.lib.translatesubs import addon_log
from resources.lib.translatesubs import utils
from resources.lib.translatesubs import translate
from resources.lib.translatesubs import monitor

logger = addon_log.logging.getLogger('.'.join((utils.logger_id, __name__.split('.', 2)[-1])))

INDENT = ' ' * 60


def run_service():
    logger.debug("Running translate service from thead %s", threading.current_thread().native_id)
    translate.cleanup_cached_files()
    system_monitor = monitor.SystemMonitor()
    try:
        player = monitor.PlayerMonitor()
        while system_monitor.waitForAbort(86400) is False:
            logger.info("Abort requested")
            translate.cleanup_cached_files()
    except Exception as e:
        logger.error("Unhandled exception: %r:", e, exc_info=True)
    logger.info("Ended service")


if __name__ == '__main__':
    run_service()