# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2025 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import os
import sys
from typing import Dict, List, Tuple

from unittest.mock import patch

import xbmcvfs

patch_g = None


def global_setup():
    """Fixture required for all test.
    Ensure this is imported and called in every test module first thing. At least before
    importing any other module from the project or other kodi related module.

    As it is global for all tests there is no need to tear down.

    """
    global patch_g
    if patch_g is None:
        # Ensure that this addon's profile dir refers to a predefined folder.
        profile_dir = translate_path_mock('special://addon_data')
        patch_g = patch('xbmcaddon.Addon.getAddonInfo',
                         new=lambda self, item: profile_dir if item == 'profile' else '')
        patch_g.start()

        # Translate path with special:// protocol to a path in the kodifs directory on the
        # top of out test folder.
        xbmcvfs.translatePath = translate_path_mock
        # Enable logging to file during tests with a new file each test run.
        try:
            os.remove(os.path.join(profile_dir, 'addon.log'))
        except FileNotFoundError:
            pass
        patch('xbmcaddon.Addon.getSettingString',
              new=lambda self, item: 'file' if item == 'log-handler' else '').start()
        # Import module to setup logging
        from resources.lib.translatesubs import addon_log

        # Use an xbmcgui.ListItem that stores the values which have been set.
        patch_listitem()

        # Ensure an addon handle is define
        if len(sys.argv) > 1:
            sys.argv[1] = '1'
        else:
            sys.argv.append('1')


patch_1 = None


class RealWebRequestMadeError(Exception):
    pass


def setup_local_tests():
    """Module level fixture for all local tests. Ensures that no unintentional real
    web requests can occur.

    """
    global patch_1
    patch_1 = patch('requests.sessions.Session.send', side_effect=RealWebRequestMadeError)
    patch_1.start()


def tear_down_local_tests():
    global patch_1

    if patch_1:
        patch_1.stop()
        patch_1 = None


def patch_listitem():
    import xbmcgui

    class LI(xbmcgui.ListItem):
        def __init__(self, label: str = "",
                     label2: str = "",
                     path: str = "",
                     offscreen: bool = False) -> None:
            super().__init__()
            assert isinstance(label, str)
            assert isinstance(label2, str)
            assert isinstance(path, str)
            assert isinstance(offscreen, bool)
            self._label = label
            self._label2 = label2
            self._path = path
            self._offscreen = offscreen
            self._is_folder = False
            self._art = {}
            self._info = {}
            self._props = {}

        def getLabel(self) -> str:
            return self._label

        def getLabel2(self) -> str:
            return self._label2

        def setLabel(self, label: str) -> None:
            assert isinstance(label, str), "Argument 'label' must be a string."
            self._label = label

        def setLabel2(self, label: str) -> None:
            assert isinstance(label, str), "Argument 'label' must be a string."
            self._label2 = label

        def setArt(self, dictionary: Dict[str, str]) -> None:
            assert isinstance(dictionary, dict), "Argument 'dictionary' must be a dict."
            self._art.update(dictionary)

        def setIsFolder(self, isFolder: bool) -> None:
            assert isinstance(isFolder, bool), "Argument 'isFolder' must be a boolean."
            self._is_folder = isFolder

        def setInfo(self, type: str, infoLabels: Dict[str, str]) -> None:
            assert isinstance(type, str), "Argument 'type' must be a string."
            assert isinstance(infoLabels, dict), "Argument 'infoLabels' must be a dict."
            assert type in ('video', 'music', 'pictures', 'game')
            info_dict = self._info.setdefault(type, {})
            info_dict.update(infoLabels)

        def setProperty(self, key: str, value: str) -> None:
            assert isinstance(key, str), "Argument 'key' must be a string."
            assert isinstance(value, str), "Argument 'value' must be a string."
            self._props[key] = value

        def setProperties(self, dictionary: Dict[str, str]) -> None:
            assert isinstance(dictionary, dict), "Argument 'dictionary' must be a dict."
            self._props.update(dictionary)

        def getProperty(self, key: str) -> str:
            assert isinstance(key, str), "Argument 'key' must be a string."
            return self._props['key']

        def setPath(self, path: str) -> None:
            assert isinstance(path, str), "Argument 'path' must be a string."
            self._path = path

        def setMimeType(self, mimetype: str) -> None:
            assert isinstance(mimetype, str), "Argument 'mimetype' must be a string."
            self._mimetype = mimetype

        def setContentLookup(self, enable: bool) -> None:
            assert isinstance(enable, bool), "Argument 'enable' must be a boolean."
            self._content_lookup = enable

        def setSubtitles(self, subtitleFiles: List[str]) -> None:
            assert isinstance(subtitleFiles, (list, tuple)), "Argument 'subtitleFiles' must be a tuple or a list."
            self._subtitles = subtitleFiles

        def getPath(self) -> str:
            return self._path

    xbmcgui.ListItem = LI


def translate_path_mock(path: str):
    """Translate 'special://' paths to folders in a directory named 'kodifs' in the top
    test directory, assuming this file is in a folder directly under test/.

    It is not accurate enough to reliably translate every possible special path, but it's
    enough to suit our needs right now.
    """
    if not path.startswith('special://'):
        return path
    special_path = path[10:]
    test_base = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'kodifs'))
    special_base_dir = special_path.split('/', 1)[0]
    os.makedirs(os.path.join(test_base, special_base_dir), exist_ok=True)
    local_dir = os.path.join(test_base, special_path)
    return local_dir
