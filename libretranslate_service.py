import logging
import subprocess
from threading import Thread
from time import sleep
from typing import override

import requests

from util import run_command

from types import TracebackType


class LibreTranslateThread(Thread):

    def __init__(self):
        super().__init__(name="LibreTranslate")
        self.libre_process: subprocess.Popen[bytes] | None = None

    def __enter__(self):
        pass

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None):
        if self.libre_process is not None:
            if self.libre_process.poll() is None:
                logging.info("Stopping LibreTranslate...")
                self.libre_process.terminate()

    @override
    def run(self):
        logging.info("Starting LibreTranslate...")

        self.libre_process = run_command(
            ["libretranslate"],
            error_message="Failed to start LibreTranslate"
        )

        logging.info("LibreTranslate stopped!")

class LibreTranslateService:

    def __init__(self):
        self.libre_thread: LibreTranslateThread | None = None

    def __enter__(self):
        self.libre_thread = LibreTranslateThread()
        self.libre_thread.__enter__()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None):
        if self.libre_thread is not None:
            self.libre_thread.__exit__(exc_type, exc_val, exc_tb)
            if self.libre_thread.is_alive():
                self.libre_thread.join()

    def start(self):
        '''
        Starts LibreTranslate in a new thread, but blocks the current thread until the API is available.
        '''

        # Early return if thread has not been allocated
        if self.libre_thread is None:
            return

        self.libre_thread.start()
        logging.info("Waiting for LibreTranslate to start...")
        while True:
            try:
                sleep(5)
                with requests.head("http://127.0.0.1:5000/languages", timeout=1) as response:
                    if response.status_code == 200:
                        break
            except Exception:
                pass