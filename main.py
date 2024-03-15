import asyncio
import logging
import threading
from web_app import run_flask
from bot import Tg
from web_app import start_ngrok

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, encoding='utf-8')
logger = logging.getLogger(__name__)


def run_flask_app():
    run_flask()


if __name__ == '__main__':
    ngrok_process, ngrok_url = start_ngrok()

    # Запуск Flask-приложения в отдельном потоке
    flask_thread = threading.Thread(target=run_flask_app, args=())
    flask_thread.start()
    print('SITE IS RUNNING')

    bot = Tg(ngrok_url)
    asyncio.run(bot.main())
    print('BOT IS ONLINE')

    flask_thread.join()  # Дожидаемся завершения потока Flask-приложения
    ngrok_process.wait()
