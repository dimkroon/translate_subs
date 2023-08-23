
from ..exceptions import UnsupportedMethod
from ..language import Language
from ..translators.base import BaseTranslator
from ..utils.annotations import Tuple
from ..utils.request import Request


class TranslateComTranslate(BaseTranslator):
    """
    translatepy's implementation of translate.com
    """

    def __init__(self, request: Request = Request()):
        self.session = request
        self.translate_url = "https://www.translate.com/translator/ajax_translate"
        self.langdetect_url = "https://www.translate.com/translator/ajax_lang_auto_detect"

    def _translate(self, text: str, destination_language: str, source_language: str) -> Tuple[str, str]:
        """
        This is the translating endpoint

        Must return a tuple with (detected_language, result)
        """
        if source_language == "auto":
            source_language = self._language(text)
        request = self.session.post(self.translate_url, data={"text_to_translate": text, "source_lang": source_language, "translated_lang": destination_language, "use_cache_only": "false"})
        if request.status_code < 400:
            result = request.json()["translated_text"]
            return source_language, result

    def _language(self, text: str) -> str:
        """
        This is the language detection endpoint

        Must return a string with the language code
        """
        # You could use `self.session` to make a request to the endpoint, with all of the parameters
        request = self.session.post(self.langdetect_url, data={"text_to_translate": text})
        request.raise_for_status()
        return request.json()["language"]

    def _language_normalize(self, language: Language) -> str:
        """
        This is the language validation function
        It receives a "translatepy.language.Language" object and returns the correct language code

        Must return a string with the correct language code
        """
        return language.alpha2

    def _language_denormalize(self, language_code) -> str:
        """
        This is the language denormalization function
        It receives a string with the translator language code and returns a "translatepy.language.Language" object

        Must return a string with the correct language code
        """
        if str(language_code).lower() in {"zh-cn", "zh"}:
            return Language("zho")
        return Language(language_code)

    def __str__(self) -> str:
        return "Translate.com"
