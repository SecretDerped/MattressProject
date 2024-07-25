import os
import shutil
import subprocess
import threading
import asyncio
import logging
from web_app import run_flask, start_ngrok
from bot import Tg

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, encoding='utf-8')
logger = logging.getLogger(__name__)


def run_flask_app():
    run_flask()


def run_streamlit_app():
    subprocess.run(["streamlit", "run", "start_page.py"])


def ensure_ngrok():
    # Создание директории utils, если она не существует
    if not os.path.exists('utils'):
        os.makedirs('utils')
    # Копирование ngrok.exe в директорию utils, если его там нет
    if not os.path.isfile('utils/ngrok.exe'):
        ngrok_path = os.path.join(os.path.dirname(__file__), 'utils/ngrok.exe')
        shutil.copy(ngrok_path, 'utils/ngrok.exe')


if __name__ == '__main__':
    ensure_ngrok()

    ngrok_process, ngrok_url = start_ngrok()

    # Запуск Flask-приложения в отдельном потоке
    flask_thread = threading.Thread(target=run_flask_app, args=())
    flask_thread.start()

    # Запуск Streamlit-приложения в отдельном потоке
    streamlit_thread = threading.Thread(target=run_streamlit_app, args=())
    streamlit_thread.start()

    bot = Tg(ngrok_url)
    asyncio.run(bot.main())

    flask_thread.join()  # Дожидаемся завершения потока Flask-приложения
    streamlit_thread.join()  # Дожидаемся завершения потока Streamlit-приложения
    ngrok_process.wait()
