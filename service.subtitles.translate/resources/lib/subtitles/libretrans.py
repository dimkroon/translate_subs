# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import os.path

import requests
import logging
from ..utils import logger_id

LT_URL = 'http://127.0.0.1:5000'
LT_API_KEY = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'


logger = logging.getLogger('.'.join((logger_id, __name__.split('.', 2)[-1])))


def detect(text):
    resp = requests.post(LT_URL, params={'q': text, 'api_key': LT_API_KEY})
    try:
        data = resp.json()
        err_str = data.get('error')
        if err_str:
            logger.error("Server detecting language: '%s'", err_str)
            return None
        else:
            return data.get('language')
    except Exception:
        logger.warning('Failed to detect language:', exc_info=True)
        return None


def translate(src_filepath, src_lang, dest_lang):
    try:
        filename = os.path.basename(src_filepath)
        with open(src_filepath, 'rb') as f:
            resp = requests.post(LT_URL + '/translate_file',
                                 data={'source': src_lang, 'target': dest_lang, 'api_key': LT_API_KEY},
                                 files={'file': (filename, f, 'text/plain')})
        data = resp.json()
        err_str = data.get('error')
        if err_str:
            logger.error("Server error translating file '%s': '%s'", filename, err_str)
            return None
        file_url = data['translatedFileUrl']

        resp = requests.get(file_url)
        resp.raise_for_status()
        return resp.text

    except Exception:
        logger.error("Unexpected error translating file '%s':", src_filepath, exc_info=True)
        return None
