import logging
import subprocess
from io import TextIOWrapper
from threading import Thread
from time import sleep
from typing import override
from urllib.request import urlopen

from translate import Translator
import speech_recognition as sr

from util import run_command

class LibreTranslateThread(Thread):

    def __init__(self):
        Thread.__init__(self, name="LibreTranslate")
        self.libre_process: subprocess.Popen[bytes] | None = None
        self.ready = False

    @override
    def run(self):
        logging.info("Starting LibreTranslate...")

        self.libre_process = run_command(
            ["libretranslate", "--update-models"],
            error_message="Failed to start LibreTranslate",
            background_process=True
        )

        try:
            while self.libre_process.poll() is None:
                sleep(0.1)

        except KeyboardInterrupt:
            self.libre_process.terminate()
            raise

    def stop(self):
        logging.info("Stopping LibreTranslate...")

        if self.libre_process is not None:
            self.libre_process.terminate()

        self.join()

def transcribe():
    translator = Translator(from_lang="en", to_lang="ja", provider="libre", base_url="http://localhost:5000")

    r = sr.Recognizer()
    with sr.Microphone() as source, open("english.txt", "w") as en_file, open("japanese.txt", "w") as ja_file:
        while True:
            audio = r.listen(source)
            try:
                english_text = r.recognize_whisper(audio, language="english")

                if not english_text:
                    continue

                overwrite_file(en_file, english_text)

                ja_text = translator.translate(english_text)
                overwrite_file(ja_file, ja_text)

                logging.info(f"English phrase: {english_text}")
                logging.info(f"Japanese translation: {ja_text}")
            except sr.UnknownValueError:
                logging.error("Whisper could not understand audio")
            except sr.RequestError as e:
                logging.error(f"Could not request results from Whisper; {e}")


def overwrite_file(file: TextIOWrapper, text: str):
    file.seek(0)
    file.write(text)
    file.truncate()
    file.flush()


if __name__ == '__main__':
    libre_thread = None

    try:
        libre_thread = LibreTranslateThread()
        libre_thread.start()

        logging.info("Waiting for LibreTranslate to start...")
        while True:
            try:
                sleep(5)
                with urlopen("http://127.0.0.1:5000/languages", timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                pass

        transcribe()

    except KeyboardInterrupt:
        logging.info("Detected KeyboardInterrupt")
    finally:
        if libre_thread is not None:
            libre_thread.stop()
