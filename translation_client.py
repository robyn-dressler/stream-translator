from typing import Dict

from translate import Translator


class TranslationClient:

    translators: Dict[tuple[str, str], Translator] = {}

    @staticmethod
    def translate(text, from_lang="autodetect", to_lang="en") -> str | None:
        translator = TranslationClient.__get_translator(from_lang, to_lang)
        translated = translator.translate(text)
        return translated if translated != text else None

    @staticmethod
    def __get_translator(from_lang: str, to_lang: str) -> Translator:
        if (from_lang, to_lang) in TranslationClient.translators:
            return TranslationClient.translators[(from_lang, to_lang)]

        translator = Translator(from_lang=from_lang, to_lang=to_lang, provider="libre", base_url="http://localhost:5000")
        TranslationClient.translators[(from_lang, to_lang)] = translator
        return translator