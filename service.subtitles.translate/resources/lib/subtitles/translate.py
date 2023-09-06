# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
import os
import re
import shutil
import time
import json
import logging
from hashlib import md5
from concurrent import futures

import requests
import xbmcvfs

from resources.lib.translatepy import Translator, Language
from resources.lib.translatepy.exceptions import UnknownLanguage, TranslatepyException
from resources.lib.translatepy.exceptions import NoResult

from resources.lib import utils
from resources.lib.subtitles import subtitle, merge
from .convert import convert_subs

import xbmc
import xbmcaddon


logger = logging.getLogger('.'.join((utils.logger_id, __name__.split('.', 2)[-1])))


TXT_TRANSLATED = 30501

FILTER_NONE = 0
FILTER_BRACKETS = 1
FILTER_CAPS = 2
FILTER_HASHTAGS = 4
FILTER_COLOURS = 1024

MAX_CHARS_PER_LINE = 42
FILE_CACHE_TIME = 60 * 86400
SUBS_CACHE_DIR = os.path.join(utils.addon_info.profile, 'subtitles')
os.makedirs(SUBS_CACHE_DIR, exist_ok=True)


supported_types = ('srt', '.srt')


class SrtLine:
    def __init__(self, lead: str, text: str, tail: str, ignore_colours: bool = False):
        self._ignore_col = ignore_colours
        if lead and tail:
            self.lead = lead
            self._text = text.strip()
            self.tail = tail
        else:
            self.lead = ''
            self._text = ''.join((lead, text.strip(), tail))
            self.tail = ''
        self.merged = False

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    def __str__(self):
        if self._text:
            if self._ignore_col:
                return self._text
            else:
                return ''.join((self.lead, self._text, self.tail))
        else:
            return ''

    def __bool__(self):
        return bool(self._text)


class SrtBlock:
    def __init__(self, block_str, ignore_colours=False):
        self._idx = ''
        self._time = ''
        self.lines = []
        self._parse(block_str, ignore_colours)

    def _parse(self, block_str: str, ignore_col):
        lines = block_str.strip().split('\n', maxsplit=2)
        self._idx = lines[0]
        self._time = lines[1]
        try:
            matches = re.findall(r'(^<[^/<>]+>)?(.+?)(</[^<>]+>)?$', lines[2], re.MULTILINE)
            self.lines = list(filter(None, (SrtLine(*match, ignore_colours=ignore_col) for match in matches)))
        except IndexError:
            # A block with index, (possibly empty) time, but no text. Does happen...
            self.lines = []

    def __str__(self):
        if self._idx and self._time:
            return '\n'.join((self._idx, self._time, *(str(line) for line in self.lines if line), '\n'))
        else:
            return ''

    @property
    def text(self):
        # return '\n'.join((self._idx, *(line.text for line in self.lines),'\n'))
        lines = self.lines
        if not lines:
            return '\n'.join((self._idx, '\n'))
        texts = [lines[0].text]
        for i in range(1, len(lines)):
            prev_line = lines[i-1]
            cur_line = lines[i]
            # Merge lines of the same actor (same text colour) when the previous line was not the end of a sentence.
            if cur_line.lead == prev_line.lead and prev_line.text[-1] not in ('.', '!', '?'):
                cur_line.merged = True
                texts[-1] = ' '.join((texts[-1], cur_line.text))
            else:
                texts.append(cur_line.text)
        return '\n'.join((self._idx, *texts, '\n'))

    @text.setter
    def text(self, trans_block):
        orig_lines = self.lines
        num_orig_lines = len(orig_lines)
        trans_lines = trans_block.lines

        try:
            if num_orig_lines == len(trans_lines):
                for i in range(num_orig_lines):
                    orig_lines[i].text = trans_lines[i]
            else:
                j = 0
                for line in trans_lines:
                    # find the all corresponding original lines
                    lines_list = [orig_lines[j]]
                    j += 1
                    while j < num_orig_lines and orig_lines[j].merged:
                        lines_list.append(orig_lines[j])
                        j += 1
                    # split the translated line into the same number of parts
                    num_merged_lines = len(lines_list)
                    new_texts = split_line(line, num_merged_lines)
                    # and apply the translated text to the original line.
                    for i in range(num_merged_lines):
                        lines_list[i].text = new_texts[i]
        except IndexError:
            logger.error("Error applying translation to block %s: List index out of range", self._idx)

    def __bool__(self):
        return bool(self.lines)


class SrtDoc:
    def __init__(self, srt_doc: str, ignore_colours=False):
        blocks = srt_doc.split('\n\n')
        self.blocks = list(filter(None, (SrtBlock(block, ignore_colours) for block in blocks if block)))

    @property
    def text(self):
        return ''.join(block.text for block in self.blocks)

    @text.setter
    def text(self, value):
        for orig, trans in zip(self.blocks, value.blocks):
            orig.text = trans

    def __str__(self):
        return ''.join(str(block) for block in self.blocks)


class TransBlock:
    def __init__(self, block_str):
        self._idx = ''
        self.lines = []
        self._parse(block_str)

    def _parse(self, block_str: str):
        block_str = block_str.strip()
        lines = block_str.split('\n')
        if lines:
            self._idx = lines[0]
            self.lines = lines[1:]


class TransDoc:
    def __init__(self, doc_str: str):
        self.blocks = [TransBlock(block) for block in doc_str.split('\n\n')]


def filter_doc(srt_txt: str, filter_flags: int = 0) -> str:
    """Remove non-spoken items, like sound descriptions.

    There are various ways of subtitling environmental sounds. Some subtitle producers
    use lines written in all capital letters, some put sound description in bracket, and
    there are probably a lot of other methods.

    This function supports removing text enclosed in bracket and lines consisting entirely
    of capitals. Choose which by setting the appropriate filter flags. If no filter flags
    are set, the srt document is returned unaltered.

    :param srt_txt: The original srt document as string.
    :param filter_flags: Bitmask of flags FILTER_BRACKETS and FILTER_CAPS

    """
    if not filter_flags:
        return srt_txt

    filter_patterns = []
    if filter_flags & FILTER_BRACKETS:
        # Pattern to remove everything enclosed in brackets, including the brackets.
        filter_patterns.append(r'(\([^)]*\)(?:$|\W?))')
    if filter_flags & FILTER_CAPS:
        # Pattern to remove lines written entirely in uppercase letters.
        filter_patterns.append(r'(^[A-Z :,]{3,}$)')
    if filter_flags & FILTER_HASHTAGS:
        # Pattern to remove text between hashtags, or from a hashtag to the end of the line.
        # Often used to show the lyrics of a song.
        filter_patterns.append(r'(^#+.*?#$)')
    pattern = '|'.join(filter_patterns)
    if pattern:
        # Replace with a space to prevent sounds collapsing into double new-lines,
        # which will mess up splitting the doc into srt blocks later on.
        new_txt = re.sub(pattern, ' ', srt_txt, flags=re.MULTILINE | re.S)
        # Cleanup artifacts by removing lines consisting only of non-word characters
        new_txt = re.sub(r'(^\W+?$)', ' ', new_txt, flags=re.MULTILINE)
        logger.info("Filter '%s' applied", filter_flags)
        return new_txt
    else:
        logger.info("No filter to apply")
        return srt_txt


def split_line(line: str, splits: int):
    result = _split_line_on_comma(line, splits)
    if not result:
        result = _split_line_equal(line, splits)
    return result


def _split_line_on_comma(line: str, splits: int):
    # Try to split on the occurrence of ', ' keeping the comma and removing the space.
    parts = re.split(r'(?<=,) ', line)

    if len(parts) == 1:
        return False

    while len(parts) > splits:
        # merge the smallest parts
        min_len = MAX_CHARS_PER_LINE
        merge_idx = 0
        for i in range(len(parts) - 1):
            new_len = len(parts[i]) + len(parts[i+1])
            if new_len < min_len:
                min_len = new_len
                merge_idx = i
        parts[merge_idx] = ' '.join(parts[merge_idx:merge_idx + 2])
        parts.pop(merge_idx + 1)

    for part in parts:
        if len(part) > MAX_CHARS_PER_LINE:
            return False

    if len(parts) < splits:
        parts += [''] * (splits - len(parts))
    return parts


def _split_line_equal(line: str, splits: int):
    parts = []
    while splits > 1:
        part_len = len(line) // splits
        part, line = _split_on_word(line, part_len)
        parts.append(part)
        splits -= 1
    parts.append(line)
    return parts


def _split_on_word(line: str, pos: int):
    """ Search for a word boundary closest to 'pos' and split the line there.

    :param line: the line to be split
    :param pos: the preferred position of the split
    :return: tuple[str, str]

    """
    pos_before = line.rfind(' ', 0, pos + 1)
    if pos_before == -1:
        pos_before = 0

    pos_after = line.find(' ', pos)
    if pos_after == -1:
        pos_after = len(line)

    if pos_before and pos - pos_before < pos_after - pos:
        return line[:pos_before], line[pos_before + 1:]
    else:
        return line[:pos_after], line[pos_after + 1:]


def split_doc(src_txt: str, max_len):
    """Split string `src_txt` into pieces of text with no more than `max_len` characters in such a way that
    each part contains full sentences.

    Returns a list of strings.

    """
    txt_len = len(src_txt)
    if txt_len <= max_len:
        return [src_txt]

    splits = []
    start_pos = 0

    while txt_len - start_pos > max_len:
        split_pos = src_txt.rfind('\n', start_pos, start_pos + max_len)
        if split_pos <= start_pos:
            raise ValueError("No position to split available in src_str")
        splits.append(src_txt[start_pos:split_pos])
        start_pos = split_pos
    splits.append(src_txt[start_pos:])
    return splits


def translate_text(subs: str,
                   target_lang: str | Language,
                   src_lang: str | Language = 'auto') -> str:
    """Translate the text `subs` and return the translated text as string.
    """
    logger.debug("Translating subtitles doc of %s chars from %s to %s", len(subs), src_lang, target_lang)

    def send_translate(txt):
        try:
            translator = Translator()
            trans_result = translator.translate(txt, target_lang, src_lang)
            logger.debug("%s characters translated by %s", len(txt), trans_result.service)
            return trans_result.result.strip()
        except NoResult:
            logger.info("No translator returned any results for text starting with '%s'", txt[:100])

    with futures.ThreadPoolExecutor() as executor:  # optimally defined number of threads
        res = [executor.submit(send_translate, txt) for txt in split_doc(subs, 3500)]
        futures.wait(res)

    translation = '\n'.join((r.result() for r in res))
    # Re-insert spaces after punctuation marks that are lost in translation.
    translation = re.sub(r'([a-z][.?!])([A-Z])', r'\1 \2', translation)
    # Remove the space the translator inserted in an html encode ampersand
    translation = translation.replace('& amp;', '&amp;')
    return translation


def translate_file(video_file: str,
                   file_path: str,
                   file_type: str,
                   target_lang: str = 'auto',
                   src_lang: str = 'auto',
                   filter_flags: int = -1) -> str | None:
    """
    Translate an srt file into target_lang and return the path to the translated document.
    Returns an already saved document if it is found in the cache. If not, an online translation
    service is used to perform the translation and the result is stored on disc for a while for
    subsequent use.

    :param video_file: URL or name of the associate video file. Used for caching translated subtitles.
    :param file_path: Path to the srt file in the original language.
    :param file_type: Type of subtitle file (srt, vtt, etc).
    :param target_lang: Language of the translation.
    :param src_lang: Language of the original subtitles. Can be 'auto' tot let the translation
        service auto-detect the langauge.
    :return: The path to the translated srt document on success, or None on failure.
    :param filter_flags: Bitmask of FILTER_xxxx flags.

    """
    # delete previously stored intermediate files
    for fname in ('orig.txt', 'srt_filtered.txt', 'translated.txt'):
        fpath = os.path.join(SUBS_CACHE_DIR, fname)
        try:
            os.remove(fpath)
        except OSError:
            pass

    # noinspection PyBroadException
    try:
        if target_lang == 'auto':
            target_lang = get_preferred_subtitle_lang()
            if not target_lang:
                logger.info("No result auto-detecting target language; skipping translation.")
                return

        trans_lang = Language(target_lang)
        filter_flags = get_filter_flags(filter_flags)

        # Create a unique file name based on the video file, language and filter options.
        cache_file_name = os.path.join(
                SUBS_CACHE_DIR,
                ''.join((md5(video_file.encode('utf8')).hexdigest(),
                         '_',
                         str(filter_flags),
                         '.',
                         trans_lang.id,
                         '.srt')))
        # Use a different file name to pass on to Kodi to get more informative
        # descriptions in subtitle dialogs in the UI.
        kodi_file_name = os.path.join(utils.addon_info.temp_dir,
                                      '.'.join((utils.addon_info.localise(TXT_TRANSLATED), trans_lang.id, 'srt')))
        if os.path.isfile(cache_file_name):
            logger.info("Used translation from cache: '%s'", cache_file_name)
            shutil.copy(cache_file_name, kodi_file_name)
            return kodi_file_name

        logger.info("Translating subtitles file %s from %s to %s", file_path, src_lang, trans_lang.id)
        t_start = time.monotonic()

        orig_subs = read_subtitles_file(file_path)
        if file_type.lstrip('.') != 'srt':
            orig_subs = convert_subs(orig_subs, file_type)

        filtered_subs = filter_doc(orig_subs, filter_flags)
        with open(os.path.join(SUBS_CACHE_DIR, 'srt_filtered.txt'), 'w') as f:
            f.write(filtered_subs)

        orig_subs_obj = subtitle.SrtDoc(filtered_subs, bool(filter_flags & FILTER_COLOURS))
        merged_obj = merge.MergedDoc(orig_subs_obj)
        orig_plain_txt = merged_obj.text
        with open(os.path.join(SUBS_CACHE_DIR, 'orig.txt'), 'w') as f:
            f.write(orig_plain_txt)

        new_txt = translate_text(orig_plain_txt, trans_lang, src_lang)
        with open(os.path.join(SUBS_CACHE_DIR, 'translated.txt'), 'w') as f:
            f.write(new_txt)
        if not new_txt:
            logger.info("No translation received.")
            return

        merged_obj.text = new_txt
        translated_srt = str(orig_subs_obj)
        with open(cache_file_name, 'w') as f:
            f.write(translated_srt)
        logger.info("Translated subtitles in '%s' sec, output: '%s'", time.monotonic() - t_start, cache_file_name)

        with open(kodi_file_name, 'w') as f:
            f.write(translated_srt)
        return kodi_file_name
    except:
        # Translating on free public services can fail for a number of reasons. Ensure not to crash the
        # calling thread, just because of that.
        logger.error("Error translating subtitles file '%s' from '%s' into '%s':",
                     file_path, src_lang, target_lang, exc_info=True)


def cleanup_cached_files(max_age: int = FILE_CACHE_TIME):
    """Remove old subtitle files"""
    # noinspection PyBroadException
    try:
        expire_time = time.time() - max_age
        with os.scandir(SUBS_CACHE_DIR) as dir_content:
            for entry in dir_content:
                if not entry.is_file():
                    continue
                if entry.stat().st_ctime < expire_time:
                    os.remove(entry.path)
                    logger.debug("Removed expired subtitle file '%s'", entry.path)
    except:
        logger.error("Error cleaning up cached subtitles:", exc_info=True)


def get_language_id(lang: str):
    lang_obj = Language(lang)
    return lang_obj.id


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
        lang_id = get_kodi_ui_language()
        logger.debug("Using Kodi ui language '%s' for translated subtitles.", lang_id)
        return lang_id
    else:
        return data


def get_kodi_ui_language():
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


def get_filter_flags(init_flags: int) -> int:
    """Read filter options in the addon's settings and return a bit mask with
    the enabled options set.

    init_flags are optional flags set by the addon that provides the original subtitles.

    """
    addon = xbmcaddon.Addon()
    if init_flags >= 0:
        filter_flags = init_flags & (FILTER_BRACKETS | FILTER_CAPS | FILTER_HASHTAGS)
    else:
        # use filters set in the add-on's settings
        filter_flags = FILTER_NONE
        f_brackets = addon.getSetting('filter_brackets')
        logger.debug("Filter brackets = %s", f_brackets)
        if f_brackets == 'true':
            filter_flags |= FILTER_BRACKETS

        f_caps = addon.getSetting('filter_all_caps')
        logger.debug("Filter capitals = %s", f_caps)
        if f_caps == 'true':
            filter_flags |= FILTER_CAPS

        f_hashtags = addon.getSetting('filter_hashtags')
        logger.debug("Filter hastags = %s", f_hashtags)
        if f_hashtags == 'true':
            filter_flags |= FILTER_HASHTAGS

    f_colour = addon.getSetting('subtitles_color')
    logger.debug("Filter colour = %s", f_colour)
    if f_colour == 'true':
        filter_flags |= FILTER_COLOURS
    return filter_flags


def read_subtitles_file(file_path):
    # noinspection HttpUrlsUsage
    if file_path.startswith('http://') or file_path.startswith('https://'):
        resp = requests.get(file_path)
        resp.raise_for_status()
        subs_text = resp.text
    else:
        with xbmcvfs.File(file_path, 'r') as f:
            subs_text = f.read()
    return subs_text
