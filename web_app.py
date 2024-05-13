import json
import time
import httpx
import logging
import subprocess
from flask import Flask, render_template, request, jsonify, abort
from sbis_manager import SBISWebApp
from utils.tools import load_conf

config = load_conf()

sbis_config = config.get('sbis')
login = sbis_config.get('login')
password = sbis_config.get('password')
sale_point_name = sbis_config.get('sale_point_name')
price_list_name = sbis_config.get('price_list_name')

tg_token = config.get('telegram').get('token')

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, encoding='utf-8')

app = Flask(__name__)
sbis = SBISWebApp(login, password, sale_point_name, price_list_name)
articles = sbis.get_articles()

# TODO: если это матрас, добавляем в задачи работягам, компоненты не добавляем.
#  Внедрить фотки и состав матраса.
#  добавить все позиции в поиск


@app.route('/', methods=['GET', 'POST'])
def index():
    chat_id = request.args.get('chat_id')
    if request.method == 'POST':
        logging.debug(f"Получен POST-запрос. Данные формы: {request.form}")

        try:
            order_data = {
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
            }
            order_data['amount_to_receive'] = float(order_data.get('price', 0)) - float(order_data.get('prepayment', 0))

            positions_data = json.loads(order_data['positionsData'])
            positions_str = "\n".join([f"{item['article']} - {item['quantity']} шт." for item in positions_data])
            order_message = (f"""НОВАЯ ЗАЯВКА
------------
Позиции:
{positions_str}
------------
Дата доставки:
{order_data['delivery_date']}
------------
Адрес:
{order_data['delivery_address']}
------------
Магазин:
{order_data['party']}
------------
Цена: {order_data['price']}
Предоплата: {order_data['prepayment']}
Нужно получить: {order_data['amount_to_receive']}""")
            if order_data['comment'] != '':
                order_message += f"\n------------\nКомментарий: {order_data['comment']}"

            logging.info(f"Сформировано сообщение для заказа: {order_message}")

            send_telegram_message(order_message, chat_id)
            logging.debug(f"Сообщение отправлено в Telegram. Chat ID: {chat_id}")
            res = sbis.write_implementation(order_data)
            return "   Заказ принят. Реализация записана. Задания созданы."

        except KeyError as e:
            logging.error(f"Отсутствует обязательное поле {str(e)}, ")
            abort(400, description=f"Отсутствует обязательное поле: {str(e)}")

        except ValueError as e:
            logging.error(f"Ошибка: неверный формат данных {str(e)}")
            abort(400, description=f"Неверный формат данных: {str(e)}")

    logging.debug("Рендеринг шаблона index.html")
    return render_template('index.html', articles=articles)


@app.route('/api/articles', methods=['GET'])
def get_articles():
    logging.debug("Получен GET-запрос к /api/articles")
    return jsonify(list(articles))


def send_telegram_message(text, chat_id):
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"

    data = {"chat_id": chat_id, "text": text}
    logging.info(f"Отправка сообщения в Telegram. URL: {url}, данные: {data}")

    response = httpx.post(url, data=data)
    logging.debug(f"Получен ответ от Telegram API: {response.json()}")
    return response.json()


def start_ngrok():
    process = subprocess.Popen(['utils/ngrok.exe', 'http', '5000'])
    url = None

    while url is None:
        try:
            response = subprocess.check_output(['curl', '-s', 'http://localhost:4040/api/tunnels'])
            data = json.loads(response.decode('utf-8'))
            url = data['tunnels'][0]['public_url']
        except:
            time.sleep(1)

    logging.info(f'Сайт доступен через ngrok: {url}')
    return process, url


def run_flask():
    logging.info("Запуск Flask-приложения")
    app.run()


if __name__ == '__main__':
    logging.info("Запуск приложения")
    ngrok_process, ngrok_url = start_ngrok()
    run_flask()

    ngrok_process.wait()
