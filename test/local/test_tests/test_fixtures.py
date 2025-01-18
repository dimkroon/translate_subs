# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2025 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------
import io
from unittest import TestCase
from unittest.mock import patch, call

import xbmc
import xbmcgui
import xbmcplugin

from support import fixtures
from support.testutils import doc_path


class TestListitemCollector(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.patch_listitem()

    def test_add_single_item(self):
        li = xbmcgui.ListItem()
        path = 'my/callback/path'
        li_coll = fixtures.ListItemCollector()
        result = li_coll(1, path, li)
        self.assertIs(result, True)
        result = li_coll(1, path, li)
        self.assertIs(result, True)
        self.assertEqual(2, len(li_coll))

    def test_add_single_item_with_keywords(self):
        li = xbmcgui.ListItem()
        path = 'my/callback/path'
        li_coll = fixtures.ListItemCollector()
        result = li_coll(handle=1, url=path, listitem=li)
        self.assertIs(result, True)
        self.assertEqual(1, len(li_coll))
        # mixed positional en keyword
        result = li_coll(1, path, listitem=li, isFolder=False)
        self.assertIs(result, True)
        self.assertEqual(2, len(li_coll))

    def test_single_item_invalid_args(self):
        li = xbmcgui.ListItem()
        path = 'my/callback/path'
        li_coll = fixtures.ListItemCollector()
        # Invalid argument 'handle' with positional args.
        self.assertRaises(TypeError, li_coll, path, li)
        # Invalid argument 'path' (args li and path swapped).
        self.assertRaises(TypeError, li_coll, 1, li, path)
        # Missing argument 'listitem' with positional args.
        self.assertRaises(TypeError, li_coll, 1, path)
        # Missing argument 'handle' with keyword args.
        self.assertRaises(TypeError, li_coll, url=path, listitem=li)
        # Missing argument 'listitem' with keyword args.
        self.assertRaises(TypeError, li_coll, 1, path, isFolder=False)
        # Missing argument 'path' with keyword args.
        self.assertRaises(TypeError, li_coll, 1, listitem=li)
        self.assertRaises(AssertionError, li_coll, 1, path, path)
        self.assertRaises(AssertionError, li_coll, 1, path, li, 3)
        self.assertRaises(AssertionError, li_coll, 1, path, li, False, '10')

    def test_add_multiple_items(self):
        li_list = [('url'+str(i), xbmcgui.ListItem(), True) for i in range(10)]
        li_coll = fixtures.ListItemCollector()
        result = li_coll(1, li_list)
        self.assertIs(result, True)
        self.assertEqual(10, len(li_coll))

    def test_add_multiple_items_with_keywords(self):
        li_list = [('url'+str(i), xbmcgui.ListItem(), True) for i in range(10)]
        li_coll = fixtures.ListItemCollector()
        result = li_coll(handle=1, items=li_list, totalItems=10)
        self.assertIs(result, True)
        self.assertEqual(10, len(li_coll))

    def test_multi_item_invalid_args(self):
        li = xbmcgui.ListItem()
        path = 'my/callback/path'
        li_coll = fixtures.ListItemCollector()
        self.assertRaises(AssertionError, li_coll, 1, [()])
        self.assertRaises(AssertionError, li_coll, 1, [(path, )])
        self.assertRaises(AssertionError, li_coll, 1, [(path, li)])
        self.assertRaises(AssertionError, li_coll, 1, [(li, path, True)])
        self.assertRaises(AssertionError, li_coll, 1, [(path, li, 'true')])
        self.assertRaises(TypeError, li_coll, '1', [(path, li, True)])
        self.assertRaises(AssertionError, li_coll, 1, [(path, li, True)], '10')

    def test_patching_with_context_mgr(self):
        """ListItemCollector used as context manager should patch both
        addDirectoryItem() and addDirectoryItems()
        """
        li_list = [('url' + str(i), xbmcgui.ListItem(), True) for i in range(10)]
        with fixtures.ListItemCollector() as li_coll:
            xbmcplugin.addDirectoryItem(1, 'url', xbmcgui.ListItem(), True)
            xbmcplugin.addDirectoryItems(1, li_list)
            self.assertEqual(11, len(li_coll))
        # Since the patches have stopped now, these items should not be collected.
        xbmcplugin.addDirectoryItem(1, 'url', xbmcgui.ListItem(), True)
        xbmcplugin.addDirectoryItems(1, li_list)
        self.assertEqual(11, len(li_coll))

    def test_stored_data_type(self):
        """Assert data is stored as tuple[str, ListItem, bool]."""
        li_coll = fixtures.ListItemCollector()
        li_coll(1, [(f'url', xbmcgui.ListItem(), True)])    # add list of items
        li_coll(2, f'url', xbmcgui.ListItem(), False)       # add single items
        self.assertEqual(2, len(li_coll))
        for li_data in li_coll:
            self.assertIsInstance(li_data, tuple)
            self.assertEqual(3, len(li_data))
            self.assertIsInstance(li_data[0], str)
            self.assertIsInstance(li_data[1], xbmcgui.ListItem)
            self.assertIsInstance(li_data[2], bool)

    def test_item_access(self):
        li_coll = fixtures.ListItemCollector()
        li_coll(1, [(f'url{i}', xbmcgui.ListItem(f'label{i}'), True) for i in range(10)])

        for i in range(10):
            self.assertEqual(f'label{i}', li_coll[i][1].getLabel())
            self.assertEqual(f'url{i}', li_coll.url(i))
            self.assertEqual(f'label{i}', li_coll.list_item(i).getLabel())

    def test_url_property(self):
        li_coll = fixtures.ListItemCollector()
        li_coll(1, [(f'url{i}', xbmcgui.ListItem(f'label{i}'), True) for i in range(10)])

        self.assertIsInstance(li_coll.urls, list)
        self.assertEqual(10, len(li_coll.urls))
        i = 0
        for url in li_coll.urls:
            self.assertEqual(f'url{i}', url)
            i += 1

    def test_list_item_property(self):
        li_coll = fixtures.ListItemCollector()
        li_coll(1, [(f'url{i}', xbmcgui.ListItem(f'label{i}'), True) for i in range(10)])

        self.assertIsInstance(li_coll.list_items, list)
        self.assertEqual(10, len(li_coll.list_items))
        i = 0
        for li in li_coll.list_items:
            self.assertIsInstance(li, xbmcgui.ListItem)
            self.assertEqual(f'label{i}', li.getLabel())
            i += 1


class TestLocaliseMock(TestCase):
    def test_localise_mock(self):
        t = fixtures.localise_mock(None, 30100)
        self.assertEqual('Translation', t)


class TestKeybMock(TestCase):
    def test_keyb_mock_not_opened(self):
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text='user entry', confirmed=True)):
            kb = xbmc.Keyboard()
            self.assertEqual('', kb.getText())
            self.assertIs(False, kb.isConfirmed())

    def test_keyb_mock_single_value(self):
        """Returns the same values each time it's opened."""
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text='user entry', confirmed=False)):
            kb = xbmc.Keyboard()
            kb.doModal()
            self.assertEqual('user entry', kb.getText())
            self.assertIs(False, kb.isConfirmed())
            kb.doModal()
            self.assertEqual('user entry', kb.getText())
            self.assertIs(False, kb.isConfirmed())

    def test_keyb_mock_sequences_of_values(self):
        """Returns the next value each time it's opened."""
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text=('1', '2'), confirmed=(True, False))):
            kb = xbmc.Keyboard()
            kb.doModal()
            self.assertEqual('1', kb.getText())
            self.assertIs(True, kb.isConfirmed())
            kb.doModal()
            self.assertEqual('2', kb.getText())
            self.assertIs(False, kb.isConfirmed())

    def test_keyb_mock_not_re_opened(self):
        """Keeps returning the same values when it's not re-opened."""
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text=('1', '2'), confirmed=(True, False))):
            kb = xbmc.Keyboard()
            kb.doModal()
            self.assertEqual('1', kb.getText())
            self.assertIs(True, kb.isConfirmed())
            self.assertEqual('1', kb.getText())
            self.assertIs(True, kb.isConfirmed())

    def test_keyb_open_new_values_even_when_not_read(self):
        """Even when a value is not read, after re-opening the next wil be returned."""
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text=('1', '2'), confirmed=(True, False))):
            kb = xbmc.Keyboard()
            kb.doModal()
            kb.doModal()
            self.assertEqual('2', kb.getText())
            self.assertIs(False, kb.isConfirmed())

    def test_keyb_last_value_when_list_exhausts(self):
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text=('1', '2'), confirmed=(True, False))):
            kb = xbmc.Keyboard()
            kb.doModal()
            kb.doModal()
            kb.doModal()
            kb.doModal()
            self.assertEqual('2', kb.getText())
            self.assertIs(False, kb.isConfirmed())

    def test_keyb_with_generator_values(self):
        with patch('xbmc.Keyboard', fixtures.keyb_mock(
                   text=(str(i) for i in range(2)), confirmed=(b for b in (True, False)))):
            kb = xbmc.Keyboard()
            kb.doModal()
            self.assertEqual('0', kb.getText())
            self.assertIs(True, kb.isConfirmed())
            kb.doModal()
            self.assertEqual('1', kb.getText())
            self.assertIs(False, kb.isConfirmed())
            kb.doModal()
            # exhausted, returns the last values again
            self.assertEqual('1', kb.getText())
            self.assertIs(False, kb.isConfirmed())

    def test_keyb_with_invalid_values(self):
        # Single values of the wrong type
        with self.assertRaises(TypeError):
            patch('xbmc.Keyboard', fixtures.keyb_mock(text=125, confirmed=True))
        with self.assertRaises(TypeError):
            patch('xbmc.Keyboard', fixtures.keyb_mock(text='abc', confirmed=123))

        # Sequences with a value of the wrong type
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text=['abc', 125], confirmed=True)):
            kb = xbmc.Keyboard()
            kb.doModal()
            self.assertRaises(ValueError, kb.doModal)
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text='abc', confirmed=[True, 125])):
            kb = xbmc.Keyboard()
            kb.doModal()
            self.assertRaises(ValueError, kb.doModal)

        # Empty sequences
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text=[], confirmed=True)):
            kb = xbmc.Keyboard()
            self.assertRaises(ValueError, kb.doModal)
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text='abc', confirmed=[])):
            kb = xbmc.Keyboard()
            self.assertRaises(ValueError, kb.doModal)

    def test_methods_are_mocks(self):
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text='1')) as mkb:
            kb = xbmc.Keyboard()
            kb.getText()
            kb.isConfirmed()
            kb.getText.assert_called_once()
            kb.isConfirmed.assert_called_once()
            self.assertEqual(1, mkb.call_count)
            xbmc.Keyboard()
            xbmc.Keyboard()
            self.assertEqual(3, mkb.call_count)  # Number times a Keyboard has been instantiated.

    def test_instantiate_multiple_keyboards(self):
        """All instances of xbmc.Keyboard should be a different mock object
         Tests some edge-case scenario's that will, or should, probably never
         occur in a real-life addon, but the important part is that each
         keyboard instance is to be opened first before it returns non-empty
         values.

        """
        with patch('xbmc.Keyboard', fixtures.keyb_mock(
                text=['1', '2', '3'],
                confirmed=[True, False, False])):
            kb1 = xbmc.Keyboard()
            kb2 = xbmc.Keyboard()
            kb3 = xbmc.Keyboard()
            self.assertIsNot(kb1, kb2)
            self.assertIsNot(kb2, kb3)

            kb1.doModal()
            self.assertIs(kb1.isConfirmed(), True)
            self.assertEqual('1', kb1.getText())

            # Keyboard-2 is not opened
            self.assertEqual('', kb2.getText())
            kb2.doModal()
            self.assertIs(kb2.isConfirmed(), False)
            self.assertEqual('2', kb2.getText())

            # keyboard 1 still reads it's original values until it's opened again.
            self.assertIs(kb1.isConfirmed(), True)
            self.assertEqual('1', kb1.getText())

            # Re-opening keyboard-1 will trigger a new set of values
            kb1.doModal()
            self.assertIs(kb1.isConfirmed(), False)
            self.assertEqual('3', kb1.getText())

            # Lists exhausted; return the last values again
            kb2.doModal()
            self.assertIs(kb2.isConfirmed(), False)
            self.assertEqual('3', kb2.getText())

    def test_inspect_instantiation_with_context_manager(self):
        with patch('xbmc.Keyboard', fixtures.keyb_mock(text="my text")) as p_keyb:
            kb1 = xbmc.Keyboard(line='init text', heading='header')
            p_keyb.assert_called_once_with(line='init text', heading='header')

    @patch('xbmc.Keyboard', new_callable=fixtures.keyb_mock, text='0', confirmed=True)
    def test_inspect_instantiation_with_decorator(self, p_kb):
        """With the use of `new_callable` `patch` passes the created mock as argument to the
        test function. This Mock object's mock_calls and call_args allows the
        inspection of arguments passed to instantiated keyboards.
        """
        kb = xbmc.Keyboard(line="init text", heading="my keyboard")
        # Check get the same mocked keyboards are produced.
        kb.doModal()
        self.assertEqual('0', kb.getText())
        self.assertIs(True, kb.isConfirmed())
        kb.getText.assert_called_once()
        kb.isConfirmed.assert_called_once()
        # Instantiation of keyboard objects can be checked by inspecting p_kb
        kb2 = xbmc.Keyboard(line="other text", heading="your keyboard")
        self.assertEqual(2, p_kb.call_count)
        self.assertEqual(call(line="init text", heading="my keyboard"), p_kb.mock_calls[0])
        self.assertEqual(call(line="other text", heading="your keyboard"), p_kb.mock_calls[1])

    @patch('xbmc.Keyboard', new=fixtures.keyb_mock(text='0', confirmed=True))
    def test_keyb_mock_decorated_as_new(self):
        """Call `keyb_mock()` and pass the result to `new`.
        """
        kb = xbmc.Keyboard(line="init text", heading="my keyboard")
        # Check get the same mocked keyboards are produced
        kb.doModal()
        self.assertEqual('0', kb.getText())
        self.assertIs(True, kb.isConfirmed())
        kb.getText.assert_called_once()
        kb.isConfirmed.assert_called_once()


class TestFileMock(TestCase):
    TEST_FILE = doc_path('test_file.txt')

    @classmethod
    def setUpClass(cls):
        cls.ensure_default_content(cls)

    def ensure_default_content(self):
        with open(self.TEST_FILE, 'w') as f:
            f.write("Just to test I'm here")

    def test_file_read_write(self):
        self.addCleanup(self.ensure_default_content)

        with fixtures.FileMock(self.TEST_FILE) as f:
            content = f.read()
        self.assertEqual("Just to test I'm here", content)

        with fixtures.FileMock(self.TEST_FILE, 'r') as f:
            content = f.read()
        self.assertEqual("Just to test I'm here", content)

        with fixtures.FileMock(self.TEST_FILE, 'w') as f:
            self.assertRaises(io.UnsupportedOperation, f.read)
        with fixtures.FileMock(self.TEST_FILE, 'w') as f:
            f.write('testing write')
        with fixtures.FileMock(self.TEST_FILE, 'a') as f:
            f.write(', write again')
        with fixtures.FileMock(self.TEST_FILE, 'r') as f:
            self.assertEqual('testing write, write again', f.read())
