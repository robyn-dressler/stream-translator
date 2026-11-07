import asyncio
import json
import webbrowser
from asyncio import TaskGroup
from pathlib import Path
from typing import override
from urllib.request import urlretrieve

import twitchio
import libretranslate.init as init
from argostranslate import package
from twitchio import Scopes, UserAuthorisation
from twitchio.authentication import UserTokenPayload

import config
from util import get_authorized_users, overwrite_file


class SetupTwitchClient(twitchio.Client):

    def __init__(self):
        self.redirect_uri = config.twitch_redirect_uri or "http://localhost:4343/oauth/callback"
        super().__init__(client_id=config.twitch_client_id, client_secret=config.twitch_client_secret,
                         redirect_uri=self.redirect_uri)
        self.auth_user_queue: asyncio.Queue[str] = asyncio.Queue()

    @override
    async def event_oauth_authorized(self, payload: UserTokenPayload):
        await super().event_oauth_authorized(payload)

        if payload.user_id is not None:
            await self.auth_user_queue.put(payload.user_id)

    async def wait_for_authorization(self, user_id: str):
        while True:
            auth_id = await self.auth_user_queue.get()
            self.auth_user_queue.task_done()
            if auth_id == user_id:
                break

            user = await self.fetch_user(id=auth_id)
            print(f"Didn't expect login from '{user.name}'. Please try again.")


class SetupService:
    def __init__(self):
        self.twitch_client = SetupTwitchClient()
        self.authorized_ids = get_authorized_users()
        self.browser = webbrowser.get()

    async def ensure_user_authorized(self, user_id: str, url: str, user_authorization_map: dict[str, UserAuthorisation],
                                     needed_scopes: set[str]):

        user_authorized = user_id in user_authorization_map
        missing_scopes: set[str] = set()

        if user_authorized:
            missing_scopes = needed_scopes.difference(user_authorization_map[user_id].scopes.selected)

        if not user_authorized or len(missing_scopes) > 0:

            user = await self.twitch_client.fetch_user(id=user_id)
            if len(missing_scopes) > 0:
                print(f"User '{user.name}' is missing scope(s): {", ".join(missing_scopes)}")
            else:
                print(f"User '{user.name}' has not provided authorization yet.")

            print(f"Please log in as {user.name}.")

            self.browser.open_new(url)
            await self.twitch_client.wait_for_authorization(user_id)

    async def get_user_ids(self, user_logins: list[str]) -> dict[str, str]:
        users = await self.twitch_client.fetch_users(logins=user_logins)
        return { user.name: user.id for user in users if user.name is not None }

    async def authorize_all_users(self):
        async def authorize():
            await self.twitch_client.wait_until_ready()

            # Get list of all user ids
            configured_logins = config.twitch_broadcaster_logins + [config.twitch_bot_login, config.twitch_owner_login]
            configured_id_map = await self.get_user_ids(configured_logins)
            configured_ids = [ v for k,v in configured_id_map.items() ]

            # Save user ID map
            json_str = json.dumps(configured_id_map)
            with open("twitch_ids.json", "w") as f:
                overwrite_file(f, json_str)

            broadcaster_ids = [ configured_id_map[login] for login in config.twitch_broadcaster_logins ]
            twitch_bot_id = configured_id_map[config.twitch_bot_login]

            user_authorizations = await self.twitch_client.fetch_auth_by_users(configured_ids)
            user_authorization_map = {item.user.id: item for item in user_authorizations if item.user.id in self.authorized_ids}

            # Authorize application to use configured bot user
            bot_scopes = {"user:read:chat", "user:write:chat", "user:bot"}
            bot_user_url = self.twitch_client.http.get_authorization_url(
                scopes=Scopes(bot_scopes),
                force_verify=True,
                redirect_uri=self.twitch_client.redirect_uri
            ).url

            await self.ensure_user_authorized(twitch_bot_id, bot_user_url, user_authorization_map, bot_scopes)

            # Authorize bot to read and write in channels
            broadcaster_scopes = {"channel:bot"}
            broadcaster_url = self.twitch_client.http.get_authorization_url(
                scopes=Scopes(broadcaster_scopes),
                force_verify=True,
                redirect_uri=self.twitch_client.redirect_uri
            ).url

            for broadcaster_id in broadcaster_ids:
                await self.ensure_user_authorized(broadcaster_id, broadcaster_url, user_authorization_map, broadcaster_scopes)

            await self.twitch_client.close()

        print("Checking if any users need to provide authorization...")

        async with TaskGroup() as task_group:
            task_group.create_task(authorize())
            task_group.create_task(self.twitch_client.start())

    def install_translation_models(self):
        print("Installing translation models...")
        init.check_and_install_models(update=True)

       # Remove the es -> en model that is automatically installed
        for model in package.get_installed_packages():
            if model.from_code == "es" and model.to_code == "en":
                print("Removing:", model.package_path, "version", model.package_version)
                package.uninstall(model)

        # Replace version 1.9 with the archived 1.0 version, since 1.9 is borked
        old_es_en_url = "https://data.argosopentech.com/argospm/v1/translate-es_en-1_0.argosmodel"
        model_file = Path("translate-es_en-1_0.argosmodel")

        if not model_file.is_file():
            urlretrieve(old_es_en_url, model_file)

        package.install_from_path(model_file)

        print("Installation complete!")

async def main():
    setup_service = SetupService()
    await setup_service.authorize_all_users()
    setup_service.install_translation_models()

if __name__ == '__main__':
    asyncio.run(main())