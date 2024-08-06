import asyncio
import os
import subprocess
import threading

from bot import Tg
from utils.tools import ensure_ngrok, start_scheduler
from web_app import run_flask, start_ngrok


def run_streamlit_app():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_page.py')
    subprocess.run(["streamlit", "run", script_path, "--server.port=8501", "--server.headless=true"], check=True)


if __name__ == '__main__':

    streamlit_thread = threading.Thread(target=run_streamlit_app)
    streamlit_thread.start()

    flask_thread = threading.Thread(target=run_flask, args=())
    flask_thread.start()
    start_scheduler(17, 35)  # Запуск планировщика задач

    ensure_ngrok()
    ngrok_process, ngrok_url = start_ngrok()

    bot = Tg(ngrok_url)
    bot_thread = threading.Thread(target=lambda: asyncio.run(bot.main()), args=())
    bot_thread.start()

    flask_thread.join()  # Дожидаемся потока Flask-приложения
    bot_thread.join()  # Дожидаемся потока бота

    ngrok_process.wait()
