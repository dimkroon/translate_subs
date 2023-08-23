"""
Yandex Translate

This implementation was made specifically for translatepy from 'Zhymabek Roman', based on 'Anime no Sekai' version.
"""

import uuid

from ..exceptions import UnsupportedMethod
from ..language import Language
from ..translators.base import BaseTranslateException, BaseTranslator
from ..utils.lru_cacher import timed_lru_cache
from ..utils.request import Request


class YandexTranslateException(BaseTranslateException):
    """
    Default Yandex Translate exception
    """

    error_codes = {
        401: "ERR_KEY_INVALID",
        402: "ERR_KEY_BLOCKED",
        403: "ERR_DAILY_REQ_LIMIT_EXCEEDED",
        404: "ERR_DAILY_CHAR_LIMIT_EXCEEDED",
        408: "ERR_MONTHLY_CHAR_LIMIT_EXCEEDED",
        413: "ERR_TEXT_TOO_LONG",
        422: "ERR_UNPROCESSABLE_TEXT",
        501: "ERR_LANG_NOT_SUPPORTED",
        503: "ERR_SERVICE_NOT_AVAIBLE",
    }


class YandexTranslate(BaseTranslator):
    """
    Yandex Translation Implementation
    """

    _api_url = "https://translate.yandex.net/api/v1/tr.json/{endpoint}"
    _supported_languages = {'auto', 'af', 'sq', 'am', 'ar', 'hy', 'az', 'ba', 'eu', 'be', 'bn', 'bs', 'bg', 'my', 'ca', 'ca', 'ceb', 'zh', 'cv', 'cs', 'da', 'nl', 'nl', 'en', 'eo', 'et', 'fi', 'fr', 'ka', 'de', 'gd', 'gd', 'ga', 'gl', 'el', 'gu', 'ht', 'ht', 'he', 'hi', 'hr', 'hu', 'is', 'id', 'it', 'jv', 'ja', 'kn', 'kk', 'km', 'ky', 'ky', 'ko', 'lo', 'la', 'lv', 'lt', 'lb', 'lb', 'mk', 'ml', 'mi', 'mr', 'ms', 'mg', 'mt', 'mn', 'mrj', 'mhr', 'ne', 'no', 'pa', 'pa', 'pap', 'fa', 'pl', 'pt', 'ro', 'ro', 'ro', 'ru', 'sah', 'si', 'si', 'sk', 'sl', 'es', 'es', 'sr', 'sjn', 'su', 'sw', 'sv', 'ta', 'tt', 'te', 'tg', 'tl', 'th', 'tr', 'udm', 'uk', 'ur', 'uz', 'vi', 'cy', 'xh', 'yi', 'zu', 'kazlat', 'uzbcyr', 'emj'}
    # _language_aliases = {"zho": "zh"}  # TODO: Feat: instead of declaring the _language_normalize and _language_denormalize methods every time in each class, we can simply put the value of the language codes aliases used by service to the _language_aliases class attribute. Syntax: {official_iso639_lang_code: service used_code}

    def __init__(self, request: Request = Request()):
        self.session = request
        self.session.header = {"User-Agent": "ru.yandex.translate/3.20.2024"}

    @timed_lru_cache(360)  # Store UUID value within 360 seconds
    def _ucid(self) -> str:
        """
        Generates UUID (UCID) for Yandex Translate API requests (USID analogue)

        Args:

        Returns:
            str --> new generated UUID value
        """
        # Yandex Translate generally generates UUID V5, but API can accepts UUID V4 (bug or feature !?)
        _uuid = str(uuid.uuid4())
        _ucid = _uuid.replace("-", "")
        return _ucid

    def _translate(self, text: str, destination_language: str, source_language: str) -> str:
        if source_language == "auto":
            source_language = self._language(text)

        url = self._api_url.format(endpoint="translate")
        params = {"ucid": self._ucid(), "srv": "android", "format": "text"}
        data = {"text": text, "lang": source_language + "-" + destination_language}
        request = self.session.post(url, params=params, data=data)
        response = request.json()

        if request.status_code < 400 and response["code"] == 200:
            try:
                _detected_language = str(data["lang"]).split("-")[0]
            except Exception:
                _detected_language = source_language
            return _detected_language, response["text"][0]
        else:
            raise YandexTranslateException(response["code"])

    def _language(self, text: str):
        url = self._api_url.format(endpoint="detect")
        params = {"ucid": self._ucid(), "srv": "android"}
        data = {'text': text, 'hint': "en"}
        request = self.session.get(url, params=params, data=data)
        response = request.json()

        if request.status_code < 400 and response["code"] == 200:
            return response["lang"]
        else:
            raise YandexTranslateException(response["code"])

    def _text_to_speech(self, text: str, speed: int, gender: str, source_language: str):
        # TODO: Use Yandex Alice text to speech (Premium voices)

        if source_language == "auto":
            source_language = self._language(text)

        speech_lang_voices = {
            "male": {"ru": ["ru_RU", "filipp"], "tr": ["tr_TR", "erkanyavas"], "en": ["en_US", "nick"]},
            "female": {"ru": ["ru_RU", "alena"], "tr": ["tr_TR", "silaerkan"], "en": ["en_US", "alyss"]}
        }

        lang = speech_lang_voices[gender].get(source_language)

        if lang is None:
            raise UnsupportedMethod("Yandex SpeechKit doesn't support {source_lang} language".format(source_lang=source_language))

        url = "https://tts.voicetech.yandex.net/tts"
        params = {"format": "mp3", "quality": "hi", "chunked": 0, "platform": "web", "mock-ranges": 1, "application": "translate", "lang": lang[0], "text": text, "voice": lang[1], "speed": speed / 100}
        response = self.session.get(url, params=params, headers={"Content-Type": None})

        if response.status_code < 400:
            return source_language, response.content
        else:
            raise YandexTranslateException(response.status_code, response.text)

    def _language_normalize(self, language):
        if language.id == "zho":
            return "zh"
        elif language.id == "srd":
            return "sjn"
        return language.alpha2

    def _language_denormalize(self, language_code):
        if str(language_code).lower() in {"zh", "zh-cn"}:
            return Language("zho")
        elif str(language_code).lower() == "sjn":
            return Language("srd")
        return Language(language_code)

    """
    def _language_normalize(self, language):
        return self._language_aliases.get(language.id, language.alpha2)
        # return language.alpha2

    def _language_denormalize(self, language_code):
        for _language_code, _service_code in self._language_aliases.items():
            if _service_code.lower() == language_code.lower():
                language_code = _language_code
                break
        return Language(language_code)
    """

    def __str__(self) -> str:
        return "Yandex"
