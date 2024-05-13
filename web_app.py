import json
import time
import httpx
import logging
import subprocess
from flask import Flask, render_template, request, abort, jsonify
from sbis_manager import SBISWebApp
from utils.tools import load_conf, create_message_str

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
nomenclatures = sbis.get_nomenclatures()

# TODO: если это матрас, добавляем в задачи работягам, компоненты не добавляем.
#  Внедрить фотки и состав матраса.


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
            print(order_data)
            # Считается отдельно на случай, если поля "Цена" и "Предоплата" будут пусты. Метод .get вернёт "0"
            order_data['amount_to_receive'] = float(order_data.get('price', 0)) - float(order_data.get('prepayment', 0))

            tg_message = create_message_str(order_data)
            logging.info(f"Сформировано сообщение для заказа: {tg_message}")

            send_telegram_message(tg_message, chat_id)
            logging.debug(f"Сообщение отправлено в Telegram. Chat ID: {chat_id}")
            # TODO: создавать задачи работягам на каждый матрас
            for positions in order_data['positionsData']:
                for i in range(int(positions['quantity'])):
                    print(nomenclatures[positions['article']])

            sbis.write_implementation(order_data)
            return "   Заказ принят. Реализация записана. Задания созданы."

        except KeyError as e:
            logging.error(f"Отсутствует обязательное поле {str(e)}, ")
            abort(400, description=f"Отсутствует обязательное поле: {str(e)}")

        except ValueError as e:
            logging.error(f"Ошибка: неверный формат данных {str(e)}")
            abort(400, description=f"Неверный формат данных: {str(e)}")

    logging.debug("Рендеринг шаблона index.html")
    return render_template('index.html', nomenclatures=nomenclatures)


@app.route('/api/articles', methods=['GET'])
def get_articles():
    logging.debug("Получен GET-запрос к /api/articles")
    return jsonify(list(nomenclatures))


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
