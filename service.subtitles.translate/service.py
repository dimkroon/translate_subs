
# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from resources.lib import addon_log
from resources.lib import main
from resources.lib import utils


if __name__ == '__main__':
    utils.addon_info.initialise()
    main.run()
    addon_log.shutdown_log()
