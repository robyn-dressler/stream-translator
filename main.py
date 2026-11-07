import asyncio
import logging

import speech_recognition as sr
import torch

from libretranslate_service import LibreTranslateService
from translation_bot import start_bot
from translation_file_service import TranslationFileService


async def transcribe():
    r = sr.Recognizer()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    with sr.Microphone() as source:
        async with TranslationFileService() as translation_file_service:
            while True:
                audio = await asyncio.to_thread(lambda: r.listen(source))
                try:
                    english_text = await asyncio.to_thread(
                        lambda: r.recognize_whisper(audio, language="english", load_options={"device": device})
                    )
                    if not english_text:
                        continue

                    await translation_file_service.process_text(english_text.strip())

                except sr.UnknownValueError:
                    logging.error("Whisper could not understand audio")
                except sr.RequestError as e:
                    logging.error(f"Could not request results from Whisper; {e}")

async def main():
    logging.getLogger().setLevel(logging.INFO)

    device = "GPU" if torch.cuda.is_available() else "CPU"
    logging.info(f"Using {device} for speech recognition")

    with LibreTranslateService() as translation_service:
        translation_service.start()

        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(transcribe())
            task_group.create_task(start_bot())

if __name__ == '__main__':
    asyncio.run(main())
