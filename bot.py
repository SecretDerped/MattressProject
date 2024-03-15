import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BotCommand, MenuButtonWebApp, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters.command import Command
from os import getenv
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class Tg:
    def __init__(self, webapp_url):
        self.app_url = webapp_url
        self.bot_token = getenv('TG_TOKEN')
        self.bot = Bot(token=self.bot_token)
        self.router = Router()

        @self.router.message(Command(commands=['start']))
        async def cmd_start(message: Message):
            user_chat_id = message.from_user.id
            webapp_url_with_chat_id = f"{self.app_url}?chat_id={user_chat_id}"
            webapp_button = InlineKeyboardButton(text="Создать заявку",
                                                 web_app=WebAppInfo(url=webapp_url_with_chat_id))
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])

            await message.answer(
                text="Используйте этого бота...",
                reply_markup=keyboard
            )

    async def set_menu_button(self):
        await self.bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Создать заявку", web_app=self.app_url))

    async def on_startup(self):
        await self.set_menu_button()
        await self.bot.set_my_commands([BotCommand("start", "Начать")])

    async def send_message(self, chat_id, text):
        await self.bot.send_message(chat_id, text)

    async def main(self):
        dp = Dispatcher()
        dp.include_router(self.router)
        await dp.start_polling(self.bot, on_startup=self.on_startup)


if __name__ == "__main__":
    bot = Tg("https://5ac5-46-29-13-252.ngrok-free.app")
    asyncio.run(bot.main())
