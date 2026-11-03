import asyncio
import webbrowser
from asyncio import TaskGroup
from typing import override

import twitchio
from argostranslate import package
from twitchio import Scopes, UserAuthorisation
from twitchio.authentication import UserTokenPayload

import config
from util import get_authorized_users


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

    async def authorize_all_users(self):
        async def authorize():
            await self.twitch_client.wait_until_ready()
            configured_ids = config.twitch_broadcaster_ids + [config.twitch_bot_id]
            user_authorizations = await self.twitch_client.fetch_auth_by_users(configured_ids)
            user_authorization_map = {item.user.id: item for item in user_authorizations}

            # Authorize application to use configured bot user
            bot_scopes = {"user:read:chat", "user:write:chat", "user:bot"}
            bot_user_url = self.twitch_client.http.get_authorization_url(
                scopes=Scopes(bot_scopes),
                force_verify=True,
                redirect_uri=self.twitch_client.redirect_uri
            ).url

            await self.ensure_user_authorized(config.twitch_bot_id, bot_user_url, user_authorization_map, bot_scopes)

            # Authorize bot to read and write in channels
            broadcaster_scopes = {"channel:bot"}
            broadcaster_url = self.twitch_client.http.get_authorization_url(
                scopes=Scopes(broadcaster_scopes),
                force_verify=True,
                redirect_uri=self.twitch_client.redirect_uri
            ).url

            for broadcaster_id in config.twitch_broadcaster_ids:
                await self.ensure_user_authorized(broadcaster_id, broadcaster_url, user_authorization_map, broadcaster_scopes)

            await self.twitch_client.close()

        print("Checking if any users need to provide authorization...")

        async with TaskGroup() as task_group:
            task_group.create_task(authorize())
            task_group.create_task(self.twitch_client.start())

    def install_translation_models(self):
        print("Installing translation models...")

        # Retrieve lists of remote and local packages
        available = package.get_available_packages()
        installed = {
            (p.from_code, p.to_code): p
            for p in package.get_installed_packages()
        }

        # Update existing packages and install new ones
        for p in available:
            key = (p.from_code, p.to_code)
            if key in installed:
                existing_package = installed[key]
                existing_package.update()
            else:
                print(f"Installing {p.from_code} -> {p.to_code}")
                p.install()

        print("Installation complete!")

async def main():
    setup_service = SetupService()
    await setup_service.authorize_all_users()
    setup_service.install_translation_models()

if __name__ == '__main__':
    asyncio.run(main())