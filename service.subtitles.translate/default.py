# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import sys
import xbmc
import xbmcplugin
from resources.lib import utils

utils.log("called with :{}", sys.argv, level=xbmc.LOGWARNING)


if len(sys.argv) <= 1:
    import xbmcaddon
    xbmcaddon.Addon().openSettings()
    sys.exit(0)

if len(sys.argv) == 2:
    if sys.argv[1] == 'mark_error':
        utils.mark_error()
    sys.exit(0)


from urllib.parse import parse_qsl
from resources.lib import manual

handle = int(sys.argv[1])
result = False

args = dict(parse_qsl(sys.argv[2].lstrip('?')))
utils.log("cmdline arguments: '{}'", args)

action = args.pop('action', None)

if action == 'search':
    result = manual.search(args, handle)
elif action == 'manual-search':
    result = manual.manual_search(args, handle)
elif action == 'translate':
    result = manual.translate(handle=handle, **args)
else:
    utils.log("Unknown action: '{}.", action)
    sys.exit(1)

xbmcplugin.endOfDirectory(handle, bool(result))