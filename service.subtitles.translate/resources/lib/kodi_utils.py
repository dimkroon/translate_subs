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
