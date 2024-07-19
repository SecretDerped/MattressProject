from datetime import datetime as dt
import json
import time
import httpx
import logging
import subprocess

import pandas as pd
from flask import Flask, render_template, request, abort, jsonify
from sbis_manager import SBISWebApp
from utils.tools import load_conf, create_message_str, append_to_dataframe, read_file, save_to_file
from barcode import Code128
from io import BytesIO

logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s',
                    level=logging.DEBUG,
                    encoding='utf-8')

config = load_conf()

sbis_config = config.get('sbis')
login = sbis_config.get('login')
password = sbis_config.get('password')
sale_point_name = sbis_config.get('sale_point_name')
price_list_name = sbis_config.get('price_list_name')

site_config = config.get('site')
regions = site_config.get('regions')
flask_port = site_config.get('flask_port')
tasks_cash = site_config.get('tasks_cash_filepath')
employees_cash = site_config.get('employees_cash_filepath')

tg_token = config.get('telegram').get('token')

high_priority = False
# Глобальный словарь для отслеживания текущих задач
sequence_buffer = {}
current_tasks = {}

app = Flask(__name__)
sbis = SBISWebApp(login, password, sale_point_name, price_list_name)

nomenclatures = sbis.get_nomenclatures()
fabrics = {key: value for key, value in nomenclatures.items() if value['is_fabric']}
springs = {key: value for key, value in nomenclatures.items() if value['is_springs']}


@app.route('/', methods=['GET', 'POST'])
def index():
    chat_id = request.args.get('chat_id')
    if request.method == 'POST':
        logging.info(f"Получен POST-запрос. Данные формы: {request.form}")

        try:
            # Запрос возвращает строки в качестве данных
            order_data = request.form.to_dict()
            for k, v in order_data.items():
                logging.debug(f'index/ POST: {k} :: {v} ({type(v)})\n')

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
                    "deadline": dt.strptime(order_data['delivery_date'], '%Y-%m-%d'),
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
                    "created": dt.now(),
                }
                for _ in range(int(position['quantity'])):
                    # В этом методе данные будут заполняться из этого словаря построчно.
                    # При добавлении нового поля, или перемещении, нужно это учитывать.
                    # Порядок task_data должен быть как в tasks_columns_config на странице бригадира
                    # TODO: привязать pydantic
                    append_to_dataframe(task_data, tasks_cash)

            sbis.write_implementation(order_data)
            return "   Заказ принят. Реализация записана. Задания созданы."

        except KeyError as e:
            logging.error(f"Отсутствует обязательное поле {str(e)}, ", exc_info=True)
            abort(400, description=f"Отсутствует обязательное поле: {str(e)}")

        except ValueError as e:
            logging.error(f"Ошибка: неверный формат данных - {str(e)}", exc_info=True)
            abort(400, description=f"Неверный формат данных: {str(e)}. Если ошибка возникла при добавлении нового "
                                   f"поля в коде, проверьте порядок данных task_data в web_app.py. Он должен быть как "
                                   f"в tasks_columns на странице бригадира.")

    logging.debug("Рендеринг шаблона index.html")
    return render_template('index.html', nomenclatures=nomenclatures, regions=regions)


@app.route('/gluing')
def gluing():
    logging.debug('Рендеринг страницы склейки')
    return render_template('gluing.html')


@app.route('/sewing')
def sewing():
    logging.debug('Рендеринг страницы швейного стола')
    return render_template('sewing.html')


@app.route('/log_sequence_gluing', endpoint="log_sequence_gluing", methods=['POST'])
@app.route('/log_sequence_sewing', endpoint="log_sequence_sewing", methods=['POST'])
def log_sequence():
    """Метод ловит запросы со страниц работяг со сканерами. Если пользователь на странице, то каждый раз, когда
    вводится символ начала последовательности ввода (открывающая круглая скобка), функция начинает запоминать
    нажатые клавиши, сохраняя их глобально, а после символа завершения ввода (закрывающая круглая скобка)
    возвращает считанную последовательность"""
    global sequence_buffer
    data = request.json
    key = data['key']

    if key == '(':
        # Инициализируется новый пустой список в глобальном буфере. Туда посимвольно будет вводиться последовательность
        sequence_buffer[request.endpoint] = []
        logging.debug(f"Получен символ начала считывания. Инициализация приёма последовательности...")
    elif key == ')':
        # Создаётся строка, куда попадут все символы из буфера, за исключением сигналов Shift
        employee_id = ''.join(sequence_buffer[request.endpoint]).replace('Shift', '')
        logging.debug(f"Завершенная последовательность: {employee_id}")

        employee_name = get_name_from_dataframe(employees_cash, employee_id)
        res = {
                'sequence': employee_name,
                'task_data': {'error': 'Нет данных'}
            }

        tasks = read_file(tasks_cash).sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                                  ascending=[False, True, True, False])
        if tasks.empty:
            return jsonify(res)

        tasks = tasks[(tasks['gluing_is_done'] == False) &
                      (tasks['sewing_is_done'] == False) &
                      (tasks['packing_is_done'] == False)]
        print(tasks)

        for i in range(0, len(tasks)):
            task = tasks.iloc[i]
            if task.name in current_tasks.values():
                res['task_data'] = task.to_dict()
                return jsonify(res)

        current_tasks[employee_id] = task.name  # Используем индекс строки как идентификатор задачи
        if employee_id not in current_tasks or current_tasks[employee_id] is None:
            pass

        else:
            task_id = current_tasks[employee_id]
            task = tasks.loc[task_id]

        task_data = task.to_dict()

        return jsonify({
            'sequence': employee_name,
            'task_data': task_data
        })

    else:
        sequence_buffer[request.endpoint].append(key)
        logging.debug(f"Текущий ввод: {sequence_buffer[request.endpoint]}")

    return jsonify({'status': 'ok'})


@app.route('/complete_task', methods=['POST'])
def complete_task():
    data = request.json
    task_id = data['task_id']
    employee_sequence = data['employee_sequence']

    tasks = read_file(tasks_cash)
    if task_id not in tasks.index:
        return jsonify({'status': 'error', 'message': 'Задача не найдена'}), 400

    tasks.loc[task_id, 'gluing_is_done'] = True
    save_to_file(tasks, tasks_cash)
    current_tasks[employee_sequence] = None

    return jsonify({'status': 'ok'})


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


@app.route('/api/barcode/<employee_id>', methods=['GET'])
def get_barcode(employee_id: str = ''):
    """Параметры: employee_id: id сотрудника из датафрейма.
    При переходе по ссылке на основе id создаётся линейный штрих-код
    Code128 в формате svg и выводится на экран.
    """

    employee_id = int(employee_id)
    employee_name = get_name_from_dataframe(employees_cash, employee_id)
    # Создаем BytesIO для хранения SVG-кода штрих-кода
    barcode_bites = BytesIO()

    # Инициализация штрих-кода и запись в SVG. Скобки в строке обязательны - они считаются символами начала и конца
    # считывания последовательности введённых символов на страницах работяг со штрих-кодами.
    barcode = Code128(f'({employee_id})')
    barcode.write(barcode_bites,
                  options={"module_height": 17.0,
                           "module_width": 0.9,
                           'foreground': 'black'},
                  text=employee_name)

    # Возвращаем SVG-код в качестве строки из BytesIO
    barcode_bites.seek(0)
    svg_data = barcode_bites.getvalue().decode('utf-8')

    # Рендерим шаблон Flask, передавая SVG-код
    return render_template('barcode.html', svg_data=svg_data)


def get_name_from_dataframe(file_path, index):
    """
    Загружает DataFrame из файла .pkl и возвращает значение из колонки 'name' по заданному индексу.

    :param file_path: Путь к файлу .pkl
    :param index: Индекс строки, значение из которой нужно получить
    :return: Значение из колонки 'name' по заданному индексу
    """
    try:
        # Загружаем DataFrame из файла .pkl
        df = pd.read_pickle(file_path)
        # Проверяем, что DataFrame содержит колонку 'name'
        if 'name' not in df.columns:
            raise KeyError("Column 'name' does not exist in the DataFrame.")

        # Получаем значение из колонки 'name' по заданному индексу
        name_value = df['name'].get(int(index), 'Неизвестен')
        return name_value

    except FileNotFoundError:
        return f"Нет доступа к файлу '{file_path}'."
    except KeyError as e:
        return str(e)
    except Exception as e:
        return f"Системная ошибка: {str(e)}"


def send_telegram_message(text, chat_id):
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"

    data = {"chat_id": chat_id, "text": text}
    logging.info(f"Отправка сообщения в Telegram. URL: {url}, данные: {data}")

    response = httpx.post(url, data=data)
    logging.debug(f"Получен ответ от Telegram API: {response.json()}")
    return response.json()


def start_ngrok():
    process = subprocess.Popen(['utils/ngrok.exe', 'http', flask_port])
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
    app.run(host='0.0.0.0')


if __name__ == '__main__':
    logging.info("Запуск приложения")
    ngrok_process, ngrok_url = start_ngrok()
    run_flask()

    ngrok_process.wait()
