# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2023 Dimitri Kroon.
#  This file is part of plugin.video.viwx.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import sys

from resources.lib import addon_log
from resources.lib import main
from resources.lib import utils



if __name__ == '__main__':
    utils.addon_info.initialise()
    module, sep, function = sys.argv[1].rpartition('/')
    if not sep or not function or function.startswith('_'):
        addon_log.logger.warning("Path '%s' provides no valid route.", sys.argv[1])
        sys.exit(1)

    import importlib
    mod = importlib.import_module(module.replace('/', '.'))
    func = getattr(mod, function)
    func()
    addon_log.shutdown_log()
