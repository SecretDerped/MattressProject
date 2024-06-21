import datetime
import json
import time
import httpx
import logging
import subprocess
from flask import Flask, render_template, request, abort, jsonify
from sbis_manager import SBISWebApp
from utils.tools import load_conf, create_message_str, append_to_dataframe

config = load_conf()

sbis_config = config.get('sbis')
login = sbis_config.get('login')
password = sbis_config.get('password')
sale_point_name = sbis_config.get('sale_point_name')
price_list_name = sbis_config.get('price_list_name')
cash_file = config.get('site').get('cash_filepath')
regions = config.get('site').get('regions')
high_priority = False

tg_token = config.get('telegram').get('token')

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG, encoding='utf-8')

app = Flask(__name__)
sbis = SBISWebApp(login, password, sale_point_name, price_list_name)

nomenclatures = sbis.get_nomenclatures()
fabrics = {key: value for key, value in nomenclatures.items() if value['is_fabric']}
springs = {key: value for key, value in nomenclatures.items() if value['is_springs']}


@app.route('/', methods=['GET', 'POST'])
def index():
    chat_id = request.args.get('chat_id')
    if request.method == 'POST':
        logging.debug(f"Получен POST-запрос. Данные формы: {request.form}")

        try:
            # Запрос возвращает строки в качестве данных
            order_data = request.form.to_dict()
            for k, v in order_data.items():
                print(f'{k} :: {v} ({type(v)})\n')

            order_data['positionsData'] = json.loads(order_data['positionsData'] or '{}')

            order_data['price'] = float(order_data.get('price')) if order_data.get('price') != '' else 0
            order_data['prepayment'] = float(order_data.get('prepayment')) if order_data.get('prepayment') != '' else 0
            order_data['amount_to_receive'] = order_data['price'] - order_data['prepayment']

            tg_message = create_message_str(order_data)
            logging.info(f"Сформировано сообщение для заказа: {tg_message}")

            send_telegram_message(tg_message, chat_id)
            logging.debug(f"Сообщение отправлено в Telegram. Chat ID: {chat_id}")

            # В positionsData находится только название позиции и количество.
            # По названию будут подтягиваться данные из словаря номенклатуры.
            for position in order_data['positionsData']:
                item = nomenclatures[position['article']]
                # Позиции не в группе "Матрасы" пропускаются
                if not item['is_mattress']:
                    continue

                task_data = {
                    "high_priority": high_priority,
                    "deadline": order_data['delivery_date'],
                    "article": item['article'],
                    "size": item['size'],
                    "base_fabric": order_data['base_fabric'],
                    "side_fabric": order_data['side_fabric'],
                    "photo": order_data['photo_data'],
                    "comment": order_data['comment'],
                    "springs": order_data['springs'],
                    "attributes": item['structure'],
                    "fabric_is_done": False,
                    "gluing_is_done": False,
                    "sewing_is_done": False,
                    "packing_is_done": False,
                    "history": "",
                    "client": order_data['party'],
                    "delivery_type": order_data['delivery_type'],
                    "address": order_data["delivery_address"],
                    "region": order_data['region_select'],
                    "created": datetime.datetime.now(),
                }
                for _ in range(int(position['quantity'])):
                    # В этом методе данные будут заполняться из этого словаря построчно.
                    # При добавлении нового поля, или перемещении, нужно это учитывать.
                    # Порядок task_data должен быть как в editors_columns на странице бригадира
                    # TODO: привязать pydantic
                    append_to_dataframe(task_data, cash_file)

            sbis.write_implementation(order_data)
            return "   Заказ принят. Реализация записана. Задания созданы."

        except KeyError as e:
            logging.error(f"Отсутствует обязательное поле {str(e)}, ", exc_info=True)
            abort(400, description=f"Отсутствует обязательное поле: {str(e)}")

        except ValueError as e:
            logging.error(f"Ошибка: неверный формат данных - {str(e)}", exc_info=True)
            abort(400, description=f"Неверный формат данных: {str(e)}. Если ошибка возникла при добавлении нового "
                                   f"поля в коде, проверьте порядок данных task_data в web_app.py. Он должен быть как "
                                   f"в editors_columns на странице бригадира.")

    logging.debug("Рендеринг шаблона index.html")
    return render_template('index.html', nomenclatures=nomenclatures, regions=regions)


@app.route('/api/nomenclatures', methods=['GET'])
def get_articles():
    """Запрос выдаёт список строк с названиями товаров.
    Символы строк в формате Unicode escape-последовательности"""
    logging.debug("Получен GET-запрос к /api/nomenclatures")
    return jsonify(list(nomenclatures))


@app.route('/api/fabrics', methods=['GET'])
def get_fabrics():
    """Запрос почти как /api/nomenclatures, только выдаёт
    не все товары, а список строк с названиями тканей.
    Символы строк в формате Unicode escape-последовательности"""
    logging.debug("Получен GET-запрос к /api/fabrics")
    return jsonify(list(fabrics))


@app.route('/api/springs', methods=['GET'])
def get_springs():
    """Запрос почти как /api/nomenclatures, только выдаёт
    не все товары, а список строк с названиями пружинных блоков.
    Символы строк в формате Unicode escape-последовательности"""
    logging.debug("Получен GET-запрос к /api/springs")
    return jsonify(list(springs))


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
