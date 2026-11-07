import asyncio
import logging
from asyncio import Queue
from contextlib import ExitStack
from dataclasses import astuple, dataclass
from io import TextIOWrapper

from langcodes import Language

import config
from util import overwrite_file
from translation_client import TranslationClient


@dataclass
class TranslationFileWriteRequest:
    english_text: str
    en_file: TextIOWrapper | None
    translated_files: dict[str, TextIOWrapper] | None

    def __iter__(self):
        return iter(astuple(self))


class TranslationFileWriter:
    _poison = TranslationFileWriteRequest("", None, None)

    def __init__(self):
        self._file_write_queue: Queue[TranslationFileWriteRequest] = Queue()

    async def run(self):
        while True:
            request = await self._file_write_queue.get()
            if request is TranslationFileWriter._poison:
                break

            try:
                if request.en_file is None or request.translated_files is None:
                    return

                overwrite_file(request.en_file, request.english_text)
                logging.info(f"English phrase: {request.english_text}")

                for code, file in request.translated_files.items():
                    translated_text = TranslationClient.translate(request.english_text, from_lang="en", to_lang=code)
                    lang = Language.get(code)
                    if translated_text is not None:
                        overwrite_file(file, translated_text)
                        logging.info(f"{lang.language_name()} translation: {translated_text}")

            except:
                logging.exception(f"Write request failed")
            finally:
                self._file_write_queue.task_done()

    async def enqueue(self, request: TranslationFileWriteRequest):
        await self._file_write_queue.put(request)

    async def stop(self):
        await self._file_write_queue.put(TranslationFileWriter._poison)

class TranslationFileService:
    def __init__(self):
        self.writer: TranslationFileWriter | None = None
        self.en_file: TextIOWrapper | None = None
        self.translated_files: dict[str, TextIOWrapper] = {}

    async def __aenter__(self):
        self.writer = TranslationFileWriter()
        self.en_file = open("english.txt", "w", encoding="utf-8")

        self.translated_files: dict[str, TextIOWrapper] = {}
        for language in config.translate_to_languages or []:
            lang = Language.find(language)
            self.translated_files[lang.to_tag()] = open(f"{lang.language_name().lower()}.txt", "w", encoding="utf-8")

        with ExitStack() as stack:
            stack.enter_context(self.en_file)
            for code, file in self.translated_files.items():
                stack.enter_context(file)
            self._stack = stack.pop_all()

        self.writer_task = asyncio.create_task(self.writer.run())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._stack.__exit__(exc_type, exc_val, exc_tb)

        if self.writer is not None:
            await self.writer.stop()

        if self.writer_task is not None:
            await self.writer_task


    async def process_text(self, text: str):
        if self.writer is None or self.en_file is None or not self.translated_files:
            return

        request = TranslationFileWriteRequest(english_text=text, en_file=self.en_file, translated_files=self.translated_files)
        await self.writer.enqueue(request)