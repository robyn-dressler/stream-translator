import asyncio
import logging
from asyncio import Queue
from contextlib import ExitStack
from dataclasses import astuple, dataclass
from io import TextIOWrapper
from typing import cast

from translation_client import TranslationClient


@dataclass
class TranslationFileWriteRequest:
    english_text: str
    en_file: TextIOWrapper | None
    ja_file: TextIOWrapper | None

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
                if request.en_file is None or request.ja_file is None:
                    return

                TranslationFileWriter.overwrite_file(request.en_file, request.english_text)
                logging.info(f"English phrase: {request.english_text}")

                ja_text = TranslationClient.translate(request.english_text, from_lang="en", to_lang="ja")
                if ja_text is not None:
                    TranslationFileWriter.overwrite_file(request.ja_file, ja_text)
                    logging.info(f"Japanese translation: {ja_text}")

            except Exception:
                pass
            finally:
                self._file_write_queue.task_done()

    async def enqueue(self, request: TranslationFileWriteRequest):
        await self._file_write_queue.put(request)

    async def stop(self):
        await self._file_write_queue.put(TranslationFileWriter._poison)

    @staticmethod
    def overwrite_file(file: TextIOWrapper, text: str):
        file.seek(0)
        file.write(text)
        file.truncate()
        file.flush()

class TranslationFileService:
    def __init__(self):
        self.writer: TranslationFileWriter | None = None
        self.en_file: TextIOWrapper | None = None
        self.ja_file: TextIOWrapper | None = None

    async def __aenter__(self):
        self.writer = TranslationFileWriter()
        self.en_file = open("english.txt", "w")
        self.ja_file = open("japanese.txt", "w")

        with ExitStack() as stack:
            stack.enter_context(cast(TextIOWrapper, self.en_file))
            stack.enter_context(cast(TextIOWrapper, self.ja_file))
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
        if self.writer is None or self.en_file is None or self.ja_file is None:
            return

        request = TranslationFileWriteRequest(english_text=text, en_file=self.en_file, ja_file=self.ja_file)
        await self.writer.enqueue(request)