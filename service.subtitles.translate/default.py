# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2023 Dimitri Kroon.
#  This file is part of plugin.video.viwx.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import sys


from resources.lib import utils


if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] == 'mark_error':
            utils.mark_error()
