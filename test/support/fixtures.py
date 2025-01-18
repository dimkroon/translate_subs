# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2022-2025 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
import os
import re
import sys

from collections.abc import Iterable
from unittest.mock import patch, Mock

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui

patch_g = None


# noinspection PyUnresolvedReferences
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
        xbmcvfs.File = FileMock
        xbmcaddon.Addon.getLocalizedString = localise_mock

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

    # noinspection PyPep8Naming,PyAttributeOutsideInit
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

        def setArt(self, dictionary: dict[str, str]) -> None:
            assert isinstance(dictionary, dict), "Argument 'dictionary' must be a dict."
            self._art.update(dictionary)

        def setIsFolder(self, isFolder: bool) -> None:
            assert isinstance(isFolder, bool), "Argument 'isFolder' must be a boolean."
            self._is_folder = isFolder

        # noinspection PyShadowingBuiltins
        def setInfo(self, type: str, infoLabels: dict[str, str]) -> None:
            assert isinstance(type, str), "Argument 'type' must be a string."
            assert isinstance(infoLabels, dict), "Argument 'infoLabels' must be a dict."
            assert type in ('video', 'music', 'pictures', 'game')
            info_dict = self._info.setdefault(type, {})
            info_dict.update(infoLabels)

        def setProperty(self, key: str, value: str) -> None:
            assert isinstance(key, str), "Argument 'key' must be a string."
            assert isinstance(value, str), "Argument 'value' must be a string."
            self._props[key] = value

        def setProperties(self, dictionary: dict[str, str]) -> None:
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

        def setSubtitles(self, subtitleFiles: list[str]) -> None:
            assert isinstance(subtitleFiles, (list, tuple)), "Argument 'subtitleFiles' must be a tuple or a list."
            self._subtitles = subtitleFiles

        def getPath(self) -> str:
            return self._path

    xbmcgui.ListItem = LI


# noinspection PyPep8Naming
class ListItemCollector:
    """Objected intended to patch xbmcplugin.addDirectoryItem(s) to store calls
    and provide easier access to all added data than a standard Mock.

    When used as context manager it will patch both addDirectoryItem() (singular)
    and addDirectoryItems() (plural).

    **Example**::

        with ListItemCollector() as li_collector:
             xbmcplugin.addDirectoryItem(int(sys.argv[1]), liz, True)
             xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_list)
        num_calls = len(li_collector)
        first_url = li_collector.url(0)
        all_urls = li_collector.urls
        first_ListItem = li_collector.list_item(0)
        all_ListItems = li_collector.list_items
        url, listitem, isfolder = li_collector[0]
        for li_data in li_collector:
            url, listitem, isfolder = li_data

    """
    def __init__(self):
        self._call_args = []
        self._patches = []

    @property
    def urls(self) -> list[str]:
        """A list of tuples with all added items."""
        return [call[0] for call in self._call_args]

    def url(self, index) -> str:
        """Return the url of added item at index `index`."""
        return self._call_args[index][0]

    @property
    def list_items(self) -> list[xbmcgui.ListItem]:
        """A list of all added xbmcgui.ListItem object."""
        return [call[1] for call in self._call_args]

    def list_item(self, index) -> xbmcgui.ListItem:
        """The xbmcgui.ListItem object of the item at index `index`."""
        return self._call_args[index][1]

    def _multi_call(self,
                    handle: int,
                    items: list,
                    totalItems: int = 0) -> bool:
        # Handle calls to xbmcplugin.addDirectoryItems()
        assert isinstance(totalItems, int), f"Argument 'totalItems' must be an int, not '{type(totalItems).__name__}'."
        for item in items:
            assert len(item) == 3, ("The list passed to addDirectoryItems() should consist of tuples "
                                    "with 3 elements: 'url', listItem' and 'isFolder'.")
            self._single_call(handle, *item)
        return True

    # noinspection PyUnusedLocal
    def _single_call(self,
                     handle: int,
                     url: str,
                     listitem: xbmcgui.ListItem,
                     isFolder: bool = False,
                     totalItems: int = 0) -> bool:
        # Handle calls to xbmcplugin.addDirectoryItem()
        assert isinstance(url, str), f"'url' must be a str, not '{type(url).__name__}'."
        assert isinstance(listitem, xbmcgui.ListItem), \
            f"listitem must be an instance of xbmcgui.ListItem, not '{type(listitem).__name__}'."
        assert isinstance(isFolder, bool), f"isFolder must be a bool, not '{type(isFolder).__name__}'."
        assert isinstance(totalItems, int), f"totalItems must be an int, not '{type(totalItems).__name__}'."
        self._call_args.append((url, listitem, isFolder))
        return True

    def __call__(self, handle, *args, **kwargs) -> bool:
        """Make a decent attempt to handle both addDirectoryItem() and addDirectoryItems()
        and dispatch to the appropriate handler. If that fails the call is invalid any way.
        """
        if not isinstance(handle, int):
            raise TypeError(f"Argument 'handle' must be an int, not '{type(handle).__name__}'")
        try:
            if 'url' in kwargs or (args and isinstance(args[0], str)):
                return self._single_call(handle, *args, **kwargs)
            elif 'items' in kwargs or (args and isinstance(args[0], (tuple, list))):
                # Kodi only accepts argument listitems of type tuple or list.
                return self._multi_call(handle, *args, **kwargs)
        except Exception as err:
            descr = str(err).replace('ListItemCollector._single_call', 'xbmcplugin.addDirectoryItem')
            descr = descr.replace('ListItemCollector._multi_call', 'xbmcplugin.addDirectoryItems')
            raise type(err)(descr) from None
        raise TypeError("Invalid argument(s) passed to either addDirectoryItem() or addDirectorItems()")

    def __len__(self):
        return len(self._call_args)

    def __iter__(self):
        return iter(self._call_args)

    def __getitem__(self, item) -> tuple[str, xbmcgui.ListItem, bool]:
        return self._call_args[item]

    def __enter__(self):
        """Context manager entry point.
        Patch both xbmcplugin.addDirectoryItem, and xbmcplugin.addDirectoryItems

        :return: self

        """
        self._patches.append(patch('xbmcplugin.addDirectoryItem', self))
        self._patches.append(patch('xbmcplugin.addDirectoryItems', self))
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for p in self._patches:
            p.stop()


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


# noinspection PyUnusedLocal
def localise_mock(self, str_id):
    """Return the text corresponding to str_id in the original language file.
    Returns only the text of the first line in the file.

    """
    pattern = f'msgctxt "#{str_id}"\nmsgid "([^"]*)"'
    test_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '../'))
    lang_file = os.path.join(
        test_dir,
        '../service.subtitles.translate/resources/language/resource.language.en_gb/strings.po')
    with open(lang_file) as f:
        lang_texts = f.read()
    match = re.search(pattern, lang_texts)
    if match:
        return match[1]
    return ''


def keyb_mock(text: str | Iterable[str], confirmed: bool | Iterable[bool] = True):
    """Return a Mock object to replace xbmc.Keyboards that, when called, returns instance
    of KeybMock. KeybMock acts as mocked instances of xbmc.Keyboard that returns text and
    isConfirmed as defined by parameters `text` and `confirmed`.
    KeybMock derives from unittest's Mock and as such all methods, like isConfirmed() and
    getText(), are Mocks themselves and their calls can be examined like any other Mock.

    Like Kodi's keyboard, each new instance of the mocked keyboard must first be opened
    with `doModal()` before `isConfirmed()` and `getText()` will return the specified values.

    When `text` and/or `confirmed` are sequences of values, each time after a keyboard is
    opened with `doModal()` the next value in the sequence will be returned, regardless of
    whether it is on the same keyboard object, or a new instance.
    When a sequence is exhausted, each subsequent call will return the last value.

    When testing code that uses keyboard entry you can patch xbmc.Keybaord by either pass the
    return value of `keyb_mock(...)` to parameter `new`, or pass `keyb_mock` to `new_callable`.
    Use the latter if patch is used as a decorator and you want to inspect the instantiation
    of keyboards.

    example::

        @patch('xbmc.Keyboard', new=fixtures.keyb_mock(text='1234'))
        def test_log_in(self):
            log_in()    # Function that opens a keyboard with heading 'Enter password'.

        @patch('xbmc.Keyboard', new_callable=fixtures.keyb_mock, text='1234')
        def test_log_in(self, patched_keyboard):
            log_in()        # Function that opens a keyboard with heading 'Enter password'.
            patched_keyboard.assert_called_once_with(heading="Enter password")

        def test_log_in(self):
            with patch('xbmc.Keyboard', keyb_mock(text='1234')) as patched_keyb:
                log_in()       # Function that opens a keyboard with heading 'Enter password'.
                patched_keyboard.assert_called_once_with(heading="Enter password")


    :param text: The text, or sequence of texts Keyboard.getText() is to return.
    :param confirmed: [Opt] The status, or sequence of statuses Keyboard.isConfirmed()
        will return. Default is True.

    """
    orig_keyboard = xbmc.Keyboard

    if isinstance(text, str):
        _text_iter = iter((text, ))
    else:
        try:
            _text_iter = iter(text)
        except TypeError:
            raise TypeError('Mock Error: Keyboard texts must be either a single string, or a sequence of strings')

    if isinstance(confirmed, bool):
        _confirmed_iter = iter((confirmed, ))
    else:
        try:
            _confirmed_iter = iter(confirmed)
        except TypeError:
            raise TypeError(
                "Mock Error: Keyboard 'confirmed' value must be either a single bool, or a sequence of bools")
    _last_text = None
    _last_confirm = None

    class KeybMock(Mock):
        def __init__(self, line, heading, hidden, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.init_line = line
            self.heading = heading
            self.hidden = hidden
            # Create as instance attributes to ensure each KeybMock instance
            # has its own return_value.
            self.getText = Mock(return_value='')
            self.isConfirmed = Mock(return_value=False)

        def doModal(self, _: int = 0):
            """Load new return values."""
            nonlocal _last_text
            nonlocal _last_confirm

            try:
                new_txt = next(_text_iter)
                if not isinstance(new_txt, str):
                    raise ValueError(f"Mock Error: All keyboard texts must be of "
                                     f"type str, not '{type(new_txt).__name__}'")
                self.getText.return_value = _last_text = new_txt
            except StopIteration:
                if _last_text is None:
                    raise ValueError('Mock Error: Keyboard has an empty sequence of texts')
                self.getText.return_value = _last_text

            try:
                new_conf = next(_confirmed_iter)
                if not isinstance(new_conf, bool):
                    raise ValueError(f"Mock Error: All 'isConfirmed' values must be of "
                                     f"type bool, not '{type(new_conf).__name__}'")
                self.isConfirmed.return_value = _last_confirm = new_conf
            except StopIteration:
                if _last_confirm is None:
                    raise ValueError("Mock Error: Keyboard has an empty sequence of 'isConfirmed' values")
                self.isConfirmed.return_value = _last_confirm

    return Mock(side_effect=lambda line='', heading='', hidden=False: KeybMock(line=line,
                                                                               heading=heading,
                                                                               hidden=hidden,
                                                                               spec=orig_keyboard))


class FileMock(xbmcvfs.File):
    def __init__(self, filepath: str, mode: str | None = None) -> None:
        super().__init__(filepath, mode)    # doesn't do anything, but keeps pycharm happy.
        if mode is None:
            mode = 'r'
        self._file = open(translate_path_mock(filepath), mode)

    def read(self, numBytes: int = 0) -> str:
        # For some reason Kodi's default numBytes == 0, while python requires -1 to read all content.
        if numBytes == 0:
            numBytes = -1
        return self._file.read(numBytes)

    def write(self, buffer: str | bytes | bytearray) -> bool:
        return bool(self._file.write(buffer))

    def close(self) -> None:
        self._file.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
