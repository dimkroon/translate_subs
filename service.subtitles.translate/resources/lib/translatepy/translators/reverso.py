
import base64

from ..exceptions import UnsupportedMethod
from ..language import Language
from ..translators.base import BaseTranslator
from ..utils.request import Request


class ReversoTranslate(BaseTranslator):
    """
    A Python implementation of Reverso's API
    """

    _supported_languages = {'auto', 'ara', 'chi', 'dut', 'dut', 'eng', 'fra', 'ger', 'heb', 'ita', 'jpn', 'pol', 'por', 'rum', 'rum', 'rum', 'rus', 'spa', 'spa', 'tur'}

    def __init__(self, request: Request = Request()):
        self.session = request

    def _translate(self, text: str, destination_language: str, source_language: str) -> str:
        if source_language == "auto":
            source_language = self._language(text)

        request = self.session.post(
            "https://api.reverso.net/translate/v1/translation",
            json={
                "input": text,
                "from": source_language,
                "to": destination_language,
                "format": "text",
                "options": {
                    "origin": "translation.web",
                    "sentenceSplitter": False,
                    "contextResults": False,
                    "languageDetection": False
                }
            },
            headers={"Content-Type": "application/json; charset=UTF-8"},
            verify=False
        )
        if request.status_code < 400:
            response = request.json()
            try:
                _detected_language = response["languageDetection"]["detectedLanguage"]
            except Exception:
                _detected_language = source_language
            return _detected_language, response["translation"][0]

    def _language(self, text: str) -> str:
        request = self.session.post(
            "https://api.reverso.net/translate/v1/translation",
            json={
                "input": text,
                "from": "eng",
                "to": "fra",
                "format": "text",
                "options": {
                    "origin": "translation.web",
                    "sentenceSplitter": False,
                    "contextResults": False,
                    "languageDetection": True
                }
            },
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
        response = request.json()
        if request.status_code < 400:
            try:
                return response["languageDetection"]["detectedLanguage"]
            except Exception:
                return response["from"]

    def _text_to_speech(self, text, speed, gender, source_language):
        if source_language == "auto":
            source_language = self._language(text)

        _supported_langs_url = "https://voice.reverso.net/RestPronunciation.svc/v1/output=json/GetAvailableVoices"
        _supported_langs_result = self.session.get(_supported_langs_url, verify=False)
        _supported_langs_list = _supported_langs_result.json()["Voices"]

        _gender = "M" if gender == "male" else "F"
        _text = base64.b64encode(text.encode()).decode()
        _source_language = "US English".lower() if source_language == "eng" else Language.by_reverso(source_language).name.lower()

        for _supported_lang in _supported_langs_list:
            if _supported_lang["Language"].lower() == _source_language and _supported_lang["Gender"] == _gender:
                voice = _supported_lang["Name"]
                break
        else:
            raise UnsupportedMethod("{source_lang} language not supported by Reverso".format(source_lang=source_language))

        url = "https://voice.reverso.net/RestPronunciation.svc/v1/output=json/GetVoiceStream/voiceName={}?voiceSpeed={}&inputText={}".format(voice, speed, _text)
        response = self.session.get(url, verify=False)
        if response.status_code < 400:
            return source_language, response.content

    def _language_normalize(self, language: Language) -> str:
        if language.id == "zho":
            return "chi"
        return language.alpha3

    def _language_denormalize(self, language_code):
        if str(language_code).lower() in {"chi", "zh-cn"}:
            return Language("zho")
        return Language(language_code)

    def __str__(self) -> str:
        return "Reverso"
