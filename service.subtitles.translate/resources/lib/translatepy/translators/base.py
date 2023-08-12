
from abc import ABCMeta, abstractmethod
from multiprocessing.pool import ThreadPool
from typing import Union

from ..exceptions import ParameterTypeError, ParameterValueError, TranslatepyException, UnsupportedMethod, UnsupportedLanguage
from ..language import Language
from ..models import LanguageResult, TextToSpechResult, TranslationResult
from ..utils.annotations import List
from ..utils.lru_cacher import LRUDictCache
from ..utils.sanitize import remove_spaces


# copied from abc.ABC (Python 3.9.5)
class ABC(metaclass=ABCMeta):
    """Helper class that provides a standard way to create an ABC using
    inheritance.

    Added in the ABC module in Python 3.4
    """
    __slots__ = ()


class BaseTranslateException(TranslatepyException):
    error_codes = {}

    def __init__(self, status_code: int = -1, message=None):
        unknown_status_code_msg = "Unknown error. Error code: {}".format(status_code)
        if message is None:
            self.message = self.error_codes.get(status_code, unknown_status_code_msg)
        else:
            self.message = message

        self.status_code = status_code

        super().__init__(self.message)

    def __str__(self):
        return "{} | {}".format(self.status_code, self.message)


# TODO: Feat: support translating > 5000 characters (or just exception raising)
# TODO: Feat: Some translation services give out a lot of useful information that can come in handy for programmers. I think we need implement separate models class for each Translator service
# --> If these informations come from already using endpoints like the translation or transliteration endpoint we could make an "extra data" field with those informations
# --> but if it is completely different endpoints, we could just add them to the Translator class or as an extra function in the classes which the user would be able to use by initiating their own translator.

class BaseTranslator(ABC):
    """
    Base abstract class for a translate service
    """

    _translations_cache = LRUDictCache()
    _languages_cache = LRUDictCache()
    _text_to_speeches_cache = LRUDictCache(8)

    _supported_languages = {}

    def translate(self, text: str, destination_language: str, source_language: str = "auto") -> TranslationResult:
        """
        Translates text from a given language to another specific language.

        Parameters:
        ----------
            text : str
                The text to be translated.
            destination_language : str
                If str it expects the language code that the `text` should be translated to.
                to check the list of languages that a `Translator` supports, and use `.get_language` to
                search for a language of the `Translator`, and find it's code.
            source_language : str
                If str it expects the code of the language that the `text` is written in. When using the default value (`auto`),
                the `Translator` will try to find the language automatically.

        Returns:
        --------
            TranslationResult:
                Translation result.

        """

        # Validate the text
        self._validate_text(text)

        # Validate the languages
        # We save the values in new variables, so at the end
        # of this method, we still have acess to the original codes.
        # With this we can use the original codes to build the response,
        # this makes the code transformation transparent to the user.
        dest_code = self._detect_and_validate_lang(destination_language)
        source_code = self._detect_and_validate_lang(source_language)

        self._validate_language_pair(source_code, dest_code)

        # Build cache key
        _cache_key = str({"t": text, "d": dest_code, "s": source_code})

        if _cache_key in self._translations_cache:
            # Taking the values from the cache
            source_language, translation = self._translations_cache[_cache_key]
        else:
            # Call the private concrete implementation of the Translator to get the translation
            source_language, translation = self._translate(text, dest_code, source_code)

            # Cache the translation values to speed up the translation process in the future
            self._translations_cache[_cache_key] = (source_language, translation)

        # Return a `TranslationResult` object
        return TranslationResult(
            service=self,
            source=text,
            source_language=self._language_denormalize(source_language),
            destination_language=self._language_denormalize(destination_language),
            result=translation,
        )

    def _translate(self, text: str, destination_language: str, source_language: str) -> str:
        """
        Private method that concrete Translators must implement to hold the concrete
        logic for the translations. Receives the validated and normalized parameters and must
        return a translation (str).
        """
        raise UnsupportedMethod()

    def language(self, text: str) -> LanguageResult:
        """
        Detect the language of the text

        Args:
            text: The text to be detect the language

        Returns:
            A `LanguageResult` object with the results of the detected language.

        """

        # Validate the text
        self._validate_text(text)

        # Build cache key
        _cache_key = str({"t": text})

        if _cache_key in self._languages_cache:
            # Taking the values from the cache
            language = self._languages_cache[_cache_key]
        else:
            # Call the private concrete implementation of the Translator to get the language
            language = self._language(text)

            # Cache the languages values to speed up the translation process in the future
            self._languages_cache[_cache_key] = language

        denormalized_lang = self._language_denormalize(language)

        # Return a `LanguageResult` object
        return LanguageResult(
            service=self,
            source=text,
            result=denormalized_lang,
        )

    def _language(self, text: str) -> str:
        """
        Private method that concrete Translators must implement to hold the concrete
        logic for the language. Receives the validated and normalized parameters and must
        return a language code (str).
        """
        raise UnsupportedMethod()

    def text_to_speech(self, text: str, speed: int = 100, gender: str = "female", source_language: str = "auto") -> TextToSpechResult:
        """
        Gives back the text to speech result for the given text

        Args:
            text: text for voice-over
            speed: text speed

        Returns:
            A `TextToSpechResult` object

        """

        # Validate the text
        self._validate_text(text)

        # Validate the languages
        # We save the values in new variables, so at the end
        # of this method, we still have acess to the original codes.
        # With this we can use the original codes to build the response,
        # this makes the code transformation transparent to the user.
        source_code = self._detect_and_validate_lang(source_language)

        gender = remove_spaces(gender).lower()

        if gender not in {"male", "female"}:
            raise ParameterValueError("Gender {gender} not supported. Supported genders: male, female".format(gender=gender))

        # Build cache key
        _cache_key = str({"t": text, "sp": speed, "s": source_code, "g": gender})

        if _cache_key in self._text_to_speeches_cache:
            # Taking the values from the cache
            source_language, text_to_speech = self._text_to_speeches_cache[_cache_key]
        else:
            # Call the private concrete implementation of the Translator to get text to spech result
            source_language, text_to_speech = self._text_to_speech(text, speed, gender, source_code)

            # Cache the text to spech result to speed up the translation process in the future
            self._text_to_speeches_cache[_cache_key] = (source_language, text_to_speech)

        # Return a `TextToSpechResult` object
        return TextToSpechResult(
            service=self,
            source=text,
            source_language=self._language_denormalize(source_language),
            speed=speed,
            gender=gender,
            result=text_to_speech,
        )

    def _text_to_speech(self, text: str, speed: int, gender: str, source_language: str) -> bytes:
        """
        Private method that concrete Translators must implement to hold the concrete
        logic for the translations.
        """
        raise UnsupportedMethod()

    @abstractmethod
    def _language_normalize(self, language) -> str:
        """
        Private method that concrete Translators must implement to hold the concrete
        logic for the translations. Receives the Language instance and must
        return a normalized code language specific of translator (str).
        """

    @abstractmethod
    def _language_denormalize(self, language_code) -> str:
        """
        Private method that concrete Translators must implement to hold the concrete
        logic for the translations. Receives the language code specific of translator and must
        return a Language instance.
        """

    def _detect_and_validate_lang(self, language: str) -> str:
        """
        Validates the language code, and converts the language code into a single format.
        """
        if isinstance(language, Language):
            result = language
        else:
            result = Language(language)

        normalized_result = self._language_normalize(result)

        if self._supported_languages:  # Check if the attribute is not empty
            if normalized_result not in self._supported_languages:
                raise UnsupportedLanguage("The language {language_code} is not supported by {service}".format(language_code=language, service=str(self)))

        return normalized_result

    def _validate_text(self, text: str) -> None:
        """
        Performs text validation. Checks the text for the correct type,
        and if it is not empty
        """
        if not isinstance(text, str):
            raise ParameterTypeError("Parameter 'text' must be a string, {} was given".format(type(text).__name__))

        if remove_spaces(text) == "":
            raise ParameterValueError("Parameter 'text' must not be empty")

    def _validate_language_pair(self, source_language, destination_language):
        """
        Performs language pair validation
        """
        if source_language == destination_language:
            raise ParameterValueError("Parameter source_language cannot be equal to the destination_language parameter")

    def clean_cache(self) -> None:
        """
        Cleans caches

        Returns:
            None
        """
        self._translations_cache.clear()
        self._languages_cache.clear()

    def __str__(self) -> str:
        """
        String representation of a translator.
        """
        class_name = self.__class__.__name__
        class_name = class_name[:class_name.rfind("Translate")]
        return "Unknown" if class_name == "" else class_name

    def __repr__(self) -> str:
        return "Translator({translator})".format(translator=self.__str__())
