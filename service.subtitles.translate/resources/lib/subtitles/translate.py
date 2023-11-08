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
import logging
from hashlib import md5
from concurrent import futures

import requests
import xbmcvfs

from resources.lib.translatepy import Translator, Language
from resources.lib.translatepy.translators.google import GoogleTranslateV2
from resources.lib.translatepy.exceptions import UnknownLanguage, TranslatepyException
from resources.lib.translatepy.exceptions import NoResult

from resources.lib import utils
from resources.lib import kodi_utils
from resources.lib.subtitles import subtitle, merge
from .convert import convert_subs

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
        # Includes dummy groups at the start and end to ensure it has the 3 groups
        # re.sub() expects later on.
        filter_patterns.append(r'(\([^)]*\)(?:$|[ :;-]?))')
    if filter_flags & FILTER_CAPS:
        # Pattern to remove lines written entirely in uppercase letters.
        filter_patterns.append(r'(?<=\n|>)([A-Z :,]{3,})(?=$|<)')
    if filter_flags & FILTER_HASHTAGS:
        # Pattern to remove text between hashtags.
        # Often used to show the lyrics of a song.
        filter_patterns.append(r'(?<=\n|>)(#+.*?#)(?=$|<)')
    pattern = '|'.join(filter_patterns)
    if pattern:
        # Replace with a space to prevent sounds collapsing into double new-lines,
        # which will mess up splitting the doc into srt blocks later on.
        new_txt = re.sub(pattern, r' ', srt_txt, flags=re.MULTILINE | re.S)
        # Cleanup artifacts by removing lines consisting only of non-word characters
        new_txt = re.sub(r'(^\W+?$)', ' ', new_txt, flags=re.MULTILINE)
        logger.info("Filter '%s' applied", filter_flags)
        return new_txt
    else:
        logger.info("No filter to apply")
        return srt_txt


def split_doc(src_txt: str, max_len: int) -> list[str]:
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
            # translator = Translator()
            translator = GoogleTranslateV2()
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
                   filter_flags: int = -1,
                   display_time: float = 0) -> str | None:
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
    :param filter_flags: Bitmask of FILTER_xxxx flags.
    :param display_time: Preferred number of seconds a subtitle block should remain visible.
    :return: The path to the translated srt document on success, or None on failure.

    """
    # delete previously stored intermediate files
    for fname in ('orig.txt', 'srt_filtered.txt', 'translated.txt', 'last_translation'):
        fpath = os.path.join(SUBS_CACHE_DIR, fname)
        try:
            os.remove(fpath)
        except OSError:
            pass

    # noinspection PyBroadException
    try:
        if target_lang == 'auto':
            target_lang = kodi_utils.get_preferred_subtitle_lang()
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
            save_last_translated_filename(cache_file_name)
            return kodi_file_name

        logger.info("Translating subtitles file %s from %s to %s", file_path, src_lang, trans_lang.id)
        t_start = time.monotonic()

        orig_subs = read_subtitles_file(file_path)
        if file_type.lstrip('.') != 'srt':
            orig_subs = convert_subs(orig_subs, file_type)

        filtered_subs = filter_doc(orig_subs, filter_flags)
        with open(os.path.join(SUBS_CACHE_DIR, 'srt_filtered.txt'), 'w', encoding='utf8') as f:
            f.write(filtered_subs)

        orig_subs_obj = subtitle.SrtDoc(filtered_subs, bool(filter_flags & FILTER_COLOURS))
        merged_obj = merge.MergedDoc(orig_subs_obj)
        orig_plain_txt = merged_obj.text
        with open(os.path.join(SUBS_CACHE_DIR, 'orig.txt'), 'w', encoding='utf8') as f:
            f.write(orig_plain_txt)

        new_txt = translate_text(orig_plain_txt, trans_lang, src_lang)
        with open(os.path.join(SUBS_CACHE_DIR, 'translated.txt'), 'w', encoding='utf8') as f:
            f.write(new_txt)
        if not new_txt:
            logger.info("No translation received.")
            return

        merged_obj.text = new_txt
        if display_time:
            orig_subs_obj.stretch_time(display_time)
        translated_srt = str(orig_subs_obj)
        with open(cache_file_name, 'w', encoding='utf8') as f:
            f.write(translated_srt)
        logger.info("Translated subtitles in '%s' sec, output: '%s'", time.monotonic() - t_start, cache_file_name)

        with open(kodi_file_name, 'w', encoding='utf8') as f:
            f.write(translated_srt)
        save_last_translated_filename(cache_file_name)
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

    f_colour = addon.getSetting('filter_colour')
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


def save_last_translated_filename(filepath):
    """Store path to the last translated srt file.
    To be used by error marker.

    """
    with open(os.path.join(SUBS_CACHE_DIR, 'last_translation'), 'w') as f:
        f.write(filepath)
