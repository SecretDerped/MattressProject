from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    MenuButtonCommands,
)
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from utils.tools import config


class Tg:
    def __init__(self, query_screen_url, foreman_screen_url, group_chat_id=None):
        self.query_screen_url = query_screen_url
        self.foreman_screen_url = foreman_screen_url + '/command'
        self.group_chat_id = group_chat_id  # ID группы, куда будут отправляться сообщения
        self.bot_token = config.get('telegram').get('token')

        self.app = ApplicationBuilder().token(self.bot_token).build()  # Создаём приложение (асинхронное)
        self.app.add_handler(CommandHandler("start", self.cmd_start))  # Регистрируем обработчик команды /start

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_chat_id = update.effective_user.id

        query_button_url = f"{self.query_screen_url}?chat_id={user_chat_id}"
        query_button = InlineKeyboardButton(
            text="Создание заявки",
            web_app=WebAppInfo(query_button_url)
        )

        foreman_button_url = f"{self.foreman_screen_url}?chat_id={user_chat_id}"
        foreman_button = InlineKeyboardButton(
            text="Показать экран бригадира",
            web_app=WebAppInfo(foreman_button_url)
        )

        keyboard = InlineKeyboardMarkup([[query_button], [foreman_button]])

        await update.message.reply_text(
            text="Соединение с сервером установлено.\nВыберите действие:",
            reply_markup=keyboard
        )

    async def set_menu_button(self, text: str):
        """Устанавливает кнопку меню чата"""
        await self.app.bot.set_chat_menu_button(
            menu_button=MenuButtonCommands(text=text)
        )

    async def on_startup(self):
        """Вызывается при старте поллинга"""
        await self.set_menu_button("Запустить")
        await self.app.bot.set_my_commands(
            [BotCommand("start", "Начать")]
        )

    async def send_message(self, chat_id, text):
        """Посылает сообщение на указанный id чата"""
        await self.app.bot.send_message(chat_id, text)

    def main(self):
        """Запуск бота"""
        #self.on_startup()
        self.app.run_polling()
