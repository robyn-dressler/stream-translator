import asyncio
import logging
from asyncio import Queue
from contextlib import ExitStack
from dataclasses import astuple, dataclass
from io import TextIOWrapper
from threading import Thread
from typing import override, cast

from translation_client import TranslationClient


@dataclass
class TranslationFileWriteRequest:
    english_text: str
    en_file: TextIOWrapper | None
    ja_file: TextIOWrapper | None

    def __iter__(self):
        return iter(astuple(self))



class TranslationFileThread(Thread):
    _poison = TranslationFileWriteRequest("", None, None)

    def __init__(self):
        super().__init__(name="TranslationFileThread")
        self._file_write_queue: Queue[TranslationFileWriteRequest] = Queue()

    @override
    def run(self):
        asyncio.run(self.run_async())

    async def run_async(self):
        while True:
            request = await self._file_write_queue.get()
            if request is TranslationFileThread._poison:
                break

            try:
                if not request.english_text or request.en_file is None or request.ja_file is None:
                    return

                TranslationFileThread.overwrite_file(request.en_file, request.english_text)
                logging.info(f"English phrase: {request.english_text}")

                ja_text = TranslationClient.translate(request.english_text, from_lang="en", to_lang="ja")
                if ja_text is not None:
                    TranslationFileThread.overwrite_file(request.ja_file, ja_text)
                    logging.info(f"Japanese translation: {ja_text}")

            except Exception:
                pass
            finally:
                self._file_write_queue.task_done()

    async def enqueue(self, request: TranslationFileWriteRequest):
        await self._file_write_queue.put(request)

    async def stop(self):
        await self._file_write_queue.put(TranslationFileThread._poison)

    @staticmethod
    def overwrite_file(file: TextIOWrapper, text: str):
        file.seek(0)
        file.write(text)
        file.truncate()
        file.flush()

class TranslationFileService:
    def __init__(self):
        self.translation_file_thread: TranslationFileThread | None = None
        self.en_file: TextIOWrapper | None = None
        self.ja_file: TextIOWrapper | None = None

    def __enter__(self):
        self.translation_file_thread = TranslationFileThread()
        self.en_file = open("english.txt", "w")
        self.ja_file = open("japanese.txt", "w")

        with ExitStack() as stack:
            stack.enter_context(cast(TextIOWrapper, self.en_file))
            stack.enter_context(cast(TextIOWrapper, self.ja_file))
            self._stack = stack.pop_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stack.__exit__(exc_type, exc_val, exc_tb)

        if self.translation_file_thread is None or not self.translation_file_thread.is_alive():
            return

        asyncio.run(self.translation_file_thread.stop())
        self.translation_file_thread.join()

    async def process_text(self, text: str):
        if self.translation_file_thread is None or self.en_file is None or self.ja_file is None:
            return

        request = TranslationFileWriteRequest(english_text=text, en_file=self.en_file, ja_file=self.ja_file)
        await self.translation_file_thread.enqueue(request)