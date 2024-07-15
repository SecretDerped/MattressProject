import asyncio
import logging
import subprocess
import threading
from web_app import run_flask, start_ngrok
from bot import Tg

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG, encoding='utf-8')
logger = logging.getLogger(__name__)


def run_flask_app():
    run_flask()


def run_streamlit_app():
    subprocess.run(["streamlit", "run", "start_page.py"])


if __name__ == '__main__':
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
