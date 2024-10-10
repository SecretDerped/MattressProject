import os
import sys
import asyncio
import logging
import shutil
import subprocess
import threading

import uvicorn

from datetime import datetime
from start_page import spec_dir, clearing_proc, cash_lifetime

if datetime.now() >= cash_lifetime:
    try:
        # Очистка кэша при закритии программы
        shutil.rmtree(os.path.join(os.path.dirname(__file__), spec_dir))
    except Exception as e:
        pass
    sys.exit(clearing_proc)

from utils.bot import Tg
from utils.tools import ensure_ngrok, start_scheduler, config
from utils.web_app import start_ngrok


streamlit_port = config['site']['streamlit_port']
site_port = config['site']['site_port']

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def run_fastapi_app():
    logging.info("Запуск FastAPI-приложения на Uvicorn")
    # В консольной команде должен быть прописан путь к web_app,
    # либо перейти в нужную папку с помощью cd, иначе uvicorn не найдёт, что загружать
    uvicorn.run("utils.web_app:app", host='0.0.0.0', port=int(site_port), reload=False)


def run_streamlit_app():
    logging.info("Запуск Streamlit-приложения")
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_page.py')
    subprocess.run(["streamlit", "run", script_path, f"--server.port={streamlit_port}", "--server.headless=true"], check=True)


if __name__ == '__main__':

    streamlit_thread = threading.Thread(target=run_streamlit_app)
    streamlit_thread.start()

    fastapi_thread = threading.Thread(target=run_fastapi_app)
    fastapi_thread.start()
    start_scheduler(17, 35)  # Запуск планировщика задач

    ensure_ngrok()
    ngrok_process, ngrok_urls = start_ngrok()

    bot = Tg(ngrok_urls['fastapi'], ngrok_urls['streamlit'])
    bot_thread = threading.Thread(target=lambda: asyncio.run(bot.main()))
    bot_thread.start()

    fastapi_thread.join()  # Дожидаемся потока Flask-приложения
    bot_thread.join()  # Дожидаемся потока бота

    ngrok_process.wait()