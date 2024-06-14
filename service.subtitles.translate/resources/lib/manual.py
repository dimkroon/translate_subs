# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import os
import sys
import re

import xbmc
import xbmcplugin
import xbmcvfs
import xbmcgui

from urllib import parse

from . import utils
from . kodi_utils import get_system_setting


SUPPORTED_SUBTITLE_FORMATS = ('srt', 'vtt', 'ttml')
addon_handle = int(sys.argv[1])


def scan_folder(folder, video_file, video_title=None):
    # get all files in the folder
    _, files = xbmcvfs.listdir(folder)
    video_name, _ = os.path.splitext(video_file)

    for subtitle_file in files:
        subtitle_name, ext = os.path.splitext(subtitle_file)
        ext = ext.lstrip('.')
        if ext not in SUPPORTED_SUBTITLE_FORMATS:
            continue

        subs_name, lang = os.path.splitext(subtitle_name)
        lang_full = xbmc.convertLanguage(lang.lstrip('.'), xbmc.ENGLISH_NAME)
        utils.log("detected language: {}: {}", lang, lang_full)

        if not lang_full:
            subs_name = subtitle_name

        utils.log("video_name = {}", video_name)
        utils.log("subs_name = {}", subs_name)

        if subs_name == video_name:
            rating = 5
        elif subs_name.startswith(video_name):
            rating = 4
        elif video_title and video_title in subs_name:
            rating = 3
        elif video_name in subs_name:
            rating = 2
        else:
            continue
        if ext != 'srt':
            rating *= 0.8
        if not lang_full:
            rating *= 0.5


        item = {
            'path': os.path.join(folder, subtitle_file),
            'file': subtitle_file,
            'type': ext,
            'lang': lang_full,
            'rating': int(rating)
        }
        utils.log("found subtitle: {}", item)
        yield item


def use_preferred_language(file_path):
    msg = "It looks like the file\n'{}'\nis already a subtitle in your preferred language.\n\n" \
          "Use this file?".format(file_path)
    if xbmcgui.Dialog().yesno(utils.addon_info.name, msg):
        xbmc.Player().setSubtitles(file_path)
        xbmc.executebuiltin('Dialog.Close(all)')
        return True
    else:
        return False


def search(args, handle):
    video_folder = xbmc.getInfoLabel('Player.Folderpath')
    subs_folder = get_system_setting('subtitles.custompath')
    video_file = xbmc.getInfoLabel('Player.Filename')
    video_title = xbmc.getInfoLabel('Player.Title')
    preferred_lang = args.get('preferredlanguage')

    utils.log("video file name: '{}'", video_file)
    utils.log("video title: '{}'", video_title)
    utils.log("video folder: '{}'", video_folder)
    utils.log("custom subtitles folder: '{}'", subs_folder)
    utils.log("preferred language: {}", preferred_lang)

    subtitles = []
    for folder in (video_folder, subs_folder):
        if not re.match(r'^(?:plugin|https?|pvr)://', video_folder):
            subtitles.extend(scan_folder(folder, video_file, video_title))

    subtitles.sort(key=lambda x: x['rating'], reverse=True)

    for file_info in subtitles:
        if file_info['lang'] == preferred_lang:
            if use_preferred_language(file_info['path']):
                return True
            else:
                continue
        li = xbmcgui.ListItem(label=preferred_lang, label2=file_info['file'])
        li.setArt({
            'icon': str(int(file_info['rating'])),  # rating for the subtitle, string 0-5
            'thumb': xbmc.convertLanguage(file_info['lang'], xbmc.ISO_639_1)  # language flag, ISO_639_1 language
        })
        querystring = parse.urlencode({
            'action': 'translate',
            'path': file_info['path'],
            'orig_lang': file_info['lang'],
            'dest_lang': preferred_lang,
            'type': file_info['type']
        })
        xbmcplugin.addDirectoryItem(
            handle,
            ''.join(('plugin://', utils.addon_info.id, '?', querystring)),
            li
        )

    # Add an extra item to manually search for an existing subtitle file on the file system. .
    li = xbmcgui.ListItem(label=preferred_lang, label2='Manually search for an existing subtitle to translate')
    li.setArt({'icon': '0',})
    xbmcplugin.addDirectoryItem(
        handle,
        ''.join(('plugin://', utils.addon_info.id, '?action=manual-search&preferredlanguage=', preferred_lang)),
        li
    )
    return True


def manual_search(args, handle):
    file = xbmcgui.Dialog().browseSingle(
        1,
        "Select Subtitle File",
        "video",
        '|'.join('.' + ext for ext in SUPPORTED_SUBTITLE_FORMATS)
    )
    if not file or re.match(r'^(?:plugin|pvr)://', file):
        return False
    utils.log("Manual search found file {}", file)

    fname, ext = os.path.splitext(file)
    _, lang = os.path.splitext(fname)
    utils.log("File extension = {}, language = {}", ext, lang)

    lang_full = xbmc.convertLanguage(lang.lstrip('.'), xbmc.ENGLISH_NAME)
    preferred_lang = args.get('preferredlanguage')
    utils.log('Full language: {}, preferred language: {}', lang_full, preferred_lang)
    if lang_full == preferred_lang:
        return use_preferred_language(file)
    return translate(path=file, orig_lang=lang_full, dest_lang=preferred_lang, type=ext, handle=handle)


def translate(path, orig_lang, dest_lang, type, handle):
    from resources.lib.subtitles.translate import translate_file

    utils.log('Manual translation of file {} from {} to {}', path, orig_lang, dest_lang)
    orig_lang = xbmc.convertLanguage(orig_lang, xbmc.ISO_639_1)
    dest_lang = xbmc.convertLanguage(dest_lang, xbmc.ISO_639_1)
    translated_file = translate_file(
        path,
        type,
        dest_lang,
        orig_lang,
        display_time=utils.addon_info.addon.getSettingNumber('display_time')
    )
    li = xbmcgui.ListItem(label=translated_file)
    xbmcplugin.addDirectoryItem(handle, translated_file, li, isFolder=False)
    xbmc.Player().getPlayingItem().setProperty('subtitle.translate.byaddon', translated_file)
    return True
