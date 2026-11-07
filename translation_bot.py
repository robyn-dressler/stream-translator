import asyncio
import logging
from typing import override, Mapping

import twitchio
from twitchio.eventsub import ChatMessageSubscription
from twitchio.ext import commands
from twitchio.ext.commands import Bot

import config
from translation_client import TranslationClient
from util import get_authorized_users, get_twitch_id_map


class TranslationBot(Bot):

    def __init__(self, id_map: Mapping[str, str]):
        super().__init__(
            client_id=config.twitch_client_id,
            client_secret=config.twitch_client_secret,
            bot_id=id_map[config.twitch_bot_login],
            owner_id=id_map[config.twitch_owner_login],
            prefix=config.twitch_bot_prefix
        )

        self.id_map = id_map

    @override
    async def setup_hook(self):
        authorized_ids = get_authorized_users()
        broadcaster_ids = [ self.id_map[login] for login in config.twitch_broadcaster_logins if login in self.id_map ]
        for broadcaster_id in broadcaster_ids:
            if broadcaster_id not in authorized_ids:
                logging.warning(f"Broadcaster id '{broadcaster_id}' not authorized. Skipping.")
                continue

            await self.subscribe_websocket(
                payload=ChatMessageSubscription(
                    broadcaster_user_id=broadcaster_id,
                    user_id=self.bot_id
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

    if config.twitch_client_id and config.twitch_client_secret and config.twitch_owner_login and config.twitch_bot_login\
        and config.twitch_broadcaster_logins:

        id_map = get_twitch_id_map()

        async with TranslationBot(id_map) as bot:
            await bot.add_component(CommandComponent(bot))
            await bot.start()

def main():
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()