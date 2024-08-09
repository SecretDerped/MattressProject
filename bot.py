from aiogram import Bot, Dispatcher, Router
from aiogram.filters.command import Command
from aiogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, \
    MenuButtonCommands

from utils.tools import config


class Tg:
    def __init__(self, webapp_url, group_chat_id=None):
        self.app_url = webapp_url
        self.bot_token = config.get('telegram').get('token')
        self.group_chat_id = group_chat_id  # ID группы, куда будут отправляться сообщения
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
                text="Создайте заявку кнопкой ниже:",
                reply_markup=keyboard
            )

    async def set_menu_button(self):
        await self.bot.set_chat_menu_button(menu_button=MenuButtonCommands(text="Запустить"))

    async def on_startup(self):
        await self.set_menu_button()
        await self.bot.set_my_commands([BotCommand(command="start", description="Начать")])

    async def send_message(self, chat_id, text):
        await self.bot.send_message(chat_id, text)

    async def main(self):
        dp = Dispatcher()
        dp.include_router(self.router)
        await dp.start_polling(self.bot, on_startup=self.on_startup)
