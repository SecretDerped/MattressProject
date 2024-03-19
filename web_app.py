import json
import time
import httpx
import logging
import subprocess
from os import getenv
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, abort
from sbis_manager import SBISWebApp

load_dotenv()

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, encoding='utf-8')
logger = logging.getLogger(__name__)

SALE_POINT_NAME = 'Кесиян Давид Арсенович, ИП'
PRICE_LIST_NAME = 'Тестовые матрацы'

app = Flask(__name__)
sbis = SBISWebApp(getenv('sbis.login'), getenv('sbis.password'), SALE_POINT_NAME, PRICE_LIST_NAME)
articles = sbis.get_articles()


@app.route('/', methods=['GET', 'POST'])
def index():
    chat_id = request.args.get('chat_id')
    if request.method == 'POST':
        logger.debug(f"Получен POST-запрос. Данные формы: {request.form}")

        try:
            order_data = dict({
                'party': request.form['party'],
                'party_data_json': request.form['party_data'],
                'positionsData': request.form['positionsData'],
                'delivery_date': request.form['delivery_date'],
                'delivery_address': request.form['delivery_address'],
                'address_data': request.form['address_data'],
                'contact': request.form['contact'],
                'price': request.form['price'],
                'prepayment': request.form['prepayment'],
                'comment': request.form.get('comment', '')
            })
            order_data['amount_to_receive'] = float(order_data.get('price', 0)) - float(order_data.get('prepayment', 0))

            positions_data = json.loads(order_data['positionsData'])
            positions_str = "\n".join([f"{item['article']} - {item['quantity']} шт." for item in positions_data])
            order_message = (f"""🟡 НОВАЯ ЗАЯВКА

Позиции:
{positions_str}

Дата доставки:
{order_data['delivery_date']}

Адрес:
{order_data['delivery_address']}

Магазин:
{order_data['party']}

Цена: {order_data['price']}

Предоплата: {order_data['prepayment']}

Нужно получить: {order_data['amount_to_receive']}""")

            logger.info(f"Сформировано сообщение для заказа: {order_message}")

            send_telegram_message(order_message, chat_id)
            logger.debug(f"Сообщение отправлено в Telegram. Chat ID: {chat_id}")
            sbis.write_implementation(order_data)

            return "Заказ принят"

        except KeyError as e:
            logger.error(f"Ошибка: отсутствует обязательное поле {str(e)}")
            abort(400, description=f"Отсутствует обязательное поле: {str(e)}")

        except ValueError as e:
            logger.error(f"Ошибка: неверный формат данных {str(e)}")
            abort(400, description=f"Неверный формат данных: {str(e)}")

    logger.debug("Рендеринг шаблона index.html")
    return render_template('index.html', articles=articles)


@app.route('/api/articles', methods=['GET'])
def get_articles():
    logger.debug("Получен GET-запрос к /api/articles")
    return jsonify(list(articles))


def send_telegram_message(text, chat_id):
    bot_token = getenv('TG_TOKEN')
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = {"chat_id": chat_id, "text": text}
    logger.info(f"Отправка сообщения в Telegram. URL: {url}, данные: {data}")

    response = httpx.post(url, data=data)
    logger.debug(f"Получен ответ от Telegram API: {response.json()}")
    return response.json()


def start_ngrok():
    process = subprocess.Popen(['ngrok.exe', 'http', '5000'])
    url = None

    while url is None:
        try:
            response = subprocess.check_output(['curl', '-s', 'http://localhost:4040/api/tunnels'])
            data = json.loads(response.decode('utf-8'))
            url = data['tunnels'][0]['public_url']
        except:
            time.sleep(1)

    logger.info(f'Сайт доступен через ngrok: {url}')
    return process, url


def run_flask():
    logger.info("Запуск Flask-приложения")
    app.run()


if __name__ == '__main__':
    logger.info("Запуск приложения")
    ngrok_process, ngrok_url = start_ngrok()
    run_flask()

    ngrok_process.wait()
