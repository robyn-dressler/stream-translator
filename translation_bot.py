import asyncio
import logging
from typing import override

import twitchio
from twitchio.eventsub import ChatMessageSubscription
from twitchio.ext import commands
from twitchio.ext.commands import Bot

import config
from translation_client import TranslationClient


class TranslationBot(Bot):
    @override
    async def setup_hook(self):
        for broadcaster_id in config.twitch_broadcaster_ids:
            await self.subscribe_websocket(
                payload=ChatMessageSubscription(
                    broadcaster_user_id=broadcaster_id,
                    user_id=config.twitch_bot_id
                ),
                as_bot=True
            )


class CommandComponent(commands.Component):

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        # Don't translate the bot's own messages, or commands
        if payload.chatter.id == self.bot.bot_id or payload.text.startswith(config.twitch_bot_prefix):
            return

        logging.info(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")
        translation = TranslationClient.translate(payload.text)

        if translation is not None:
            translation_response = f"{payload.chatter.name}: {translation}"
            logging.info(f"Translated message -- [{payload.broadcaster.name}] - {translation_response}")
            await payload.respond(translation_response)


    @commands.command()
    async def yo(self, ctx: commands.Context):
        """Command that replies to the user with 'yo'.
        """

        await ctx.reply("yo")

async def start_bot():
    twitchio.utils.setup_logging(level=logging.INFO)

    async with TranslationBot(
            client_id=config.twitch_client_id,
            client_secret=config.twitch_client_secret,
            bot_id=config.twitch_bot_id,
            owner_id=config.twitch_owner_id,
            prefix=config.twitch_bot_prefix
    ) as bot:
        await bot.add_component(CommandComponent(bot))
        await bot.start()

def main():
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()