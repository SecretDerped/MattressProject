import asyncio
import os
import sys
import threading
from streamlit.web import cli as stcli

from bot import Tg
from utils.tools import ensure_ngrok, start_scheduler
from web_app import run_flask, start_ngrok


def run_streamlit_app():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_page.py')
    sys.argv = ["streamlit", "run", script_path]
    stcli.main()


if __name__ == '__main__':

    flask_thread = threading.Thread(target=run_flask, args=())
    flask_thread.start()

    ensure_ngrok()
    ngrok_process, ngrok_url = start_ngrok()

    bot = Tg(ngrok_url)
    bot_thread = threading.Thread(target=lambda: asyncio.run(bot.main()), args=())
    bot_thread.start()

    run_streamlit_app()  # Запуск Streamlit-приложения в основном потоке
    flask_thread.join()  # Дожидаемся потока Flask-приложения
    bot_thread.join()  # Дожидаемся потока бота
    start_scheduler(9, 10)  # Запуск планировщика задач

    ngrok_process.wait()
