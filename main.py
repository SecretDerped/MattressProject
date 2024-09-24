import asyncio
import logging
import os
import subprocess

import threading

from waitress import serve

from bot import Tg
from utils.tools import ensure_ngrok, start_scheduler, config
from web_app import start_ngrok, app

from fastapi import FastAPI


streamlit_port = config['site']['streamlit_port']
flask_port = config['site']['flask_port']


def run_flask():
    logging.info("Запуск Flask-приложения на Waitress")
    serve(app, host='0.0.0.0', port=flask_port)


def run_streamlit_app():
    logging.info("Запуск Streamlit-приложения")
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_page.py')
    subprocess.run(["streamlit", "run", script_path, f"--server.port={streamlit_port}", "--server.headless=true"], check=True)


if __name__ == '__main__':

    streamlit_thread = threading.Thread(target=run_streamlit_app)
    streamlit_thread.start()

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    start_scheduler(17, 35)  # Запуск планировщика задач

    ensure_ngrok()
    ngrok_process, ngrok_urls = start_ngrok()

    bot = Tg(ngrok_urls['flask'], ngrok_urls['streamlit'])
    bot_thread = threading.Thread(target=lambda: asyncio.run(bot.main()))
    bot_thread.start()

    flask_thread.join()  # Дожидаемся потока Flask-приложения
    bot_thread.join()  # Дожидаемся потока бота

    ngrok_process.wait()
