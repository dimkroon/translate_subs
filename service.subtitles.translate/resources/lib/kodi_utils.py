# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------
import json
import logging

import xbmc
import xbmcgui

from codequick import Script, utils
from codequick.support import addon_data


from . utils import addon_info, logger_id

logger = logging.getLogger(logger_id + '.kodi_utils')


TXT_LOG_TARGETS = 30192


def ask_log_handler(default):
    options = Script.localize(TXT_LOG_TARGETS).split(',')
    dlg = xbmcgui.Dialog()
    result = dlg.contextmenu(options)
    if result == -1:
        result = default
    try:
        return result, options[result]
    except IndexError:
        # default value is not necessarily a valid index.
        return result, ''


def msg_dlg(msg, title=None):
    if not isinstance(msg, str) or not isinstance(title, (type(None), str)):
        logger.error("Invalid argument passed to message dialog: '%s', '%s'", msg, title)
        raise ValueError('Arguments must be of type string')

    dlg = xbmcgui.Dialog()
    if title is None:
        title = addon_info.name
    dlg.ok(title, msg)


def get_system_setting(setting_id):
    json_str = '{{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": ["{}"], "id": 1}}'.format(setting_id)
    response = xbmc.executeJSONRPC(json_str)
    data = json.loads(response)
    try:
        return data['result']['value']
    except KeyError:
        msg = data.get('message') or "Failed to get setting"
        logger.error("Failed to get system setting '%s': '%s'", setting_id, msg)
        raise ValueError('System setting error: {}'.format(msg))


def get_ui_language():
    """Return the 2-letter language code of the language used in the Kodi user interface.

    The region part is stripped from the ID returned by Kodi, because translatepy can
    handle a variety of language identifiers, but cannot handle language_Region type of
    id's used in Kodi, like 'en_GB'.

    """
    response = xbmc.executeJSONRPC(
        '{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": ["locale.language"], "id": 1}')
    data = json.loads(response)['result']['value']
    # The data value returned is in a format like 'resources.language.en_GB'
    return data.split('.')[-1].split('_')[0]


def get_preferred_subtitle_lang():
    """Get the preferred subtitle language from Kodi settings."""
    response = xbmc.executeJSONRPC(
        '{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": ["locale.subtitlelanguage"], "id": 1}')
    try:
        data = json.loads(response)['result']['value']
    except:
        logger.error("Error getting preferred subtitle language. Response='%s'", response)
        raise
    if data in ('none', 'forced_only', 'original'):
        logger.debug("No subtitles translation, since preferred subtitle language is '%s'", data)
        return None
    if data == 'default':
        lang_id = get_ui_language()
        logger.debug("Using Kodi ui language '%s' for translated subtitles.", lang_id)
        return lang_id
    else:
        return data
