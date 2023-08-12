"""
translatepy v2.3

© Anime no Sekai — 2021
"""

from multiprocessing.pool import ThreadPool
from threading import Thread
from typing import Union

from .exceptions import NoResult, ParameterTypeError, ParameterValueError
from .language import Language
from .models import LanguageResult, TextToSpechResult, TranslationResult
                                
from .translators import (BaseTranslator, BingTranslate,
                                     DeeplTranslate, GoogleTranslate,
                                     LibreTranslate, MyMemoryTranslate,
                                     ReversoTranslate, TranslateComTranslate,
                                     YandexTranslate, MicrosoftTranslate)
from .utils.annotations import List
from .utils.queue import Queue
from .utils.request import Request
from .utils.sanitize import remove_spaces


class Translate():
    """
    A class which groups all of the APIs
    """

    def __init__(
        self,
        services_list: List[BaseTranslator] = [
            GoogleTranslate,
            YandexTranslate,
            MicrosoftTranslate,
            ReversoTranslate,
            BingTranslate,
            DeeplTranslate,
            LibreTranslate,
            TranslateComTranslate,
            MyMemoryTranslate
        ],
        request: Request = Request(),
        fast: bool = False
    ) -> None:
        """
        A special Translator class grouping multiple translators to have better results.

        Parameters:
        ----------
            services_list : list
                A list of instanciated or not BaseTranslator subclasses to use as translators
            request : Request
                The Request class used to make requests
            fast : bool
                Enabling fast mode (concurrent processing) or not
        """

        if not isinstance(services_list, List):
            raise ParameterTypeError("Parameter 'services_list' must be a list, {} was given".format(type(services_list).__name__))

        if not services_list:
            raise ParameterValueError("Parameter 'services_list' must not be empty")

        self.FAST_MODE = fast

        if isinstance(request, type):  # is not instantiated
            self.request = request()
        else:
            self.request = request

        self.services = []
        for service in services_list:
            if not isinstance(service, BaseTranslator):  # not instantiated
                if not issubclass(service, BaseTranslator):
                    raise ParameterTypeError("{service} must be a child class of the BaseTranslator class".format(service=service))
            self.services.append(service)

    def _instantiate_translator(self, service: BaseTranslator, services_list: list, index: int):
        if not isinstance(service, BaseTranslator):  # not instantiated
            if "request" in service.__init__.__code__.co_varnames:  # check if __init__ wants a request parameter
                service = service(request=self.request)
            else:
                service = service()
            services_list[index] = service
        return service

    def translate(self, text: str, destination_language: str, source_language: str = "auto") -> TranslationResult:
        """
        Translates the given text to the given language

        i.e Good morning (en) --> おはようございます (ja)
        """
        dest_lang = Language(destination_language)
        source_lang = Language(source_language)

        def _translate(translator: BaseTranslator, index: int):
            translator = self._instantiate_translator(translator, self.services, index)
            result = translator.translate(
                text=text, destination_language=dest_lang, source_language=source_lang
            )
            if result is None:
                raise NoResult("{service} did not return any value".format(service=translator.__repr__()))
            return result

        def _fast_translate(queue: Queue, translator: BaseTranslator, index: int):
            try:
                queue.put(_translate(translator=translator, index=index))
            except Exception:
                pass

        if self.FAST_MODE:
            _queue = Queue()
            threads = []
            for index, service in enumerate(self.services):
                thread = Thread(target=_fast_translate, args=(_queue, service, index))
                thread.start()
                threads.append(thread)
            result = _queue.get(threads=threads)  # wait for a value and return it
            if result is None:
                raise NoResult("No service has returned a valid result")
            return result

        for index, service in enumerate(self.services):
            try:
                return _translate(translator=service, index=index)
            except Exception:
                continue
        else:
            raise NoResult("No service has returned a valid result")

    def language(self, text: str) -> LanguageResult:
        """
        Returns the language of the given text

        i.e 皆さんおはようございます！ --> Japanese
        """
        def _language(translator: BaseTranslator, index: int):
            translator = self._instantiate_translator(translator, self.services, index)
            result = translator.language(
                text=text
            )
            if result is None:
                raise NoResult("{service} did not return any value".format(service=translator.__repr__()))
            return result

        def _fast_language(queue: Queue, translator: BaseTranslator, index: int):
            try:
                queue.put(_language(translator=translator, index=index))
            except Exception:
                pass

        if self.FAST_MODE:
            _queue = Queue()
            threads = []
            for index, service in enumerate(self.services):
                thread = Thread(target=_fast_language, args=(_queue, service, index))
                thread.start()
                threads.append(thread)
            result = _queue.get(threads=threads)  # wait for a value and return it
            if result is None:
                raise NoResult("No service has returned a valid result")
            return result

        for index, service in enumerate(self.services):
            try:
                return _language(translator=service, index=index)
            except Exception:
                continue
        else:
            raise NoResult("No service has returned a valid result")

    def text_to_speech(self, text: str, speed: int = 100, gender: str = "female", source_language: str = "auto") -> TextToSpechResult:
        """
        Gives back the text to speech result for the given text

        Args:
          text: the given text
          source_language: the source language

        Returns:
            the mp3 file as bytes

        Example:
            >>> from translatepy import Translator
            >>> t = Translator()
            >>> result = t.text_to_speech("Hello, how are you?")
            >>> with open("output.mp3", "wb") as output: # open a binary (b) file to write (w)
            ...     output.write(result.result)
                    # or:
                    result.write_to_file(output)
            # Or you can just use write_to_file method:
            >>> result.write_to_file("output.mp3")
            >>> print("Output of Text to Speech is available in output.mp3!")

            # the result is an MP3 file with the text to speech output
        """
        source_lang = Language(source_language)

        def _text_to_speech(translator: BaseTranslator, index: int):
            translator = self._instantiate_translator(translator, self.services, index)
            result = translator.text_to_speech(
                text=text, speed=speed, gender=gender, source_language=source_lang
            )
            if result is None:
                raise NoResult("{service} did not return any value".format(service=translator.__repr__()))
            return result

        def _fast_text_to_speech(queue: Queue, translator: BaseTranslator, index: int):
            try:
                queue.put(_text_to_speech(translator=translator, index=index))
            except Exception:
                pass

        if self.FAST_MODE:
            _queue = Queue()
            threads = []
            for index, service in enumerate(self.services):
                thread = Thread(target=_fast_text_to_speech, args=(_queue, service, index))
                thread.start()
                threads.append(thread)
            result = _queue.get(threads=threads)  # wait for a value and return it
            if result is None:
                raise NoResult("No service has returned a valid result")
            return result

        for index, service in enumerate(self.services):
            try:
                return _text_to_speech(translator=service, index=index)
            except Exception:
                continue
        else:
            raise NoResult("No service has returned a valid result")

    def clean_cache(self) -> None:
        """
        Cleans caches

        Returns:
            None
        """
        for service in self.services:
            service.clean_cache()
