import asyncio
import logging

import speech_recognition as sr

from libretranslate_service import LibreTranslateService
from translation_bot import start_bot
from translation_file_service import TranslationFileService


async def transcribe():
    r = sr.Recognizer()

    with sr.Microphone() as source, TranslationFileService() as translation_file_service:
        while True:
            audio = await asyncio.to_thread(lambda: r.listen(source))
            try:
                english_text = await asyncio.to_thread(lambda: r.recognize_whisper(audio, language="english"))
                await translation_file_service.process_text(english_text)

            except sr.UnknownValueError:
                logging.error("Whisper could not understand audio")
            except sr.RequestError as e:
                logging.error(f"Could not request results from Whisper; {e}")

async def main():
    logging.getLogger().setLevel(logging.INFO)

    with LibreTranslateService() as translation_service:
        translation_service.start()
        transcribe_task = asyncio.create_task(transcribe())
        bot_task = asyncio.create_task(start_bot())
        await asyncio.gather(bot_task, transcribe_task)

if __name__ == '__main__':
    asyncio.run(main())
