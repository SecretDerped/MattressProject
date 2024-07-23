from datetime import datetime as dt
import json
import time
import httpx
import logging
import subprocess

from flask import Flask, render_template, request, abort, jsonify
from sbis_manager import SBISWebApp
from utils.tools import load_conf, create_message_str, append_to_dataframe, read_file, save_to_file, load_tasks, \
    get_employee_name, time_now, get_filtered_tasks, get_date_str
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


@app.route('/log_sequence_gluing', endpoint="log_sequence_gluing", methods=['POST'])
def log_sequence_gluing():
    filter_conditions = [
        "gluing_is_done == False",
        "sewing_is_done == False",
        "packing_is_done == False"
    ]

    def transform_task_data(task):
        return {
            'Артикул': task['article'],
            'Состав': task['attributes'],
            'Размер': task['size'],
            'Срок': get_date_str(task['deadline'])
        }
    return log_sequence('Сборка', 'Отметка', filter_conditions, transform_task_data)


@app.route('/complete_task_gluing', methods=['POST'])
def complete_task_gluing():
    return complete_task('Сборка', 'Готово', 'gluing_is_done')


@app.route('/sewing')
def sewing():
    logging.debug('Рендеринг страницы швейного стола')
    return render_template('sewing.html')


@app.route('/log_sequence_sewing', endpoint="log_sequence_sewing", methods=['POST'])
def log_sequence_sewing():
    filter_conditions = [
        "gluing_is_done == True",
        "sewing_is_done == False",
        "fabric_is_done == True",
        "packing_is_done == False"
    ]

    def transform_task_data(task):
        return {
            'Артикул': task['article'],
            'Размер': task['size'],
            'Ткань (Верх / Низ)': task['base_fabric'],
            'Ткань (Боковина)': task['side_fabric'],
            'deadline': get_date_str(task['deadline'])
        }
    return log_sequence('Шитье', 'Отметка', filter_conditions, transform_task_data)


@app.route('/complete_task_sewing', methods=['POST'])
def complete_task_sewing():
    return complete_task('Шитье', 'Готово', 'sewing_is_done')


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
    employee_name = get_employee_name(employee_id)
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


def log_sequence(page_name, action, filter_conditions, transform_task_data):
    global sequence_buffer, current_tasks
    data = request.json
    key = data['key']

    if key == '(':
        sequence_buffer[request.endpoint] = []
        logging.debug(f"Получен символ начала считывания. Инициализация приёма последовательности...")
    elif key == ')':
        employee_id = ''.join(sequence_buffer[request.endpoint]).replace('Shift', '')
        logging.debug(f"Завершенная последовательность: {employee_id}")

        employee_name = get_employee_name(employee_id)

        tasks = load_tasks()
        if tasks.empty:
            return jsonify({'sequence': employee_name, 'task_data': {'error': 'Нет данных'}})

        filtered_tasks = get_filtered_tasks(tasks, filter_conditions)

        task_id = current_tasks.get(employee_id)
        if task_id is not None:
            task = filtered_tasks.loc[task_id]
            logging.debug(f"Возвращаем задачу для сотрудника {employee_id}: {task.to_dict()}")
            transformed_task = transform_task_data(task)
            return jsonify({'sequence': employee_name, 'task_data': transformed_task})

        for task_id in filtered_tasks.index:
            if task_id not in current_tasks.values():
                current_tasks[employee_id] = task_id
                task = filtered_tasks.loc[task_id]
                update_task_history(tasks, task_id, page_name, employee_name, action)
                save_to_file(tasks, tasks_cash)
                logging.debug(f"Назначаем новую задачу сотруднику {employee_id}: {task.to_dict()}")
                transformed_task = transform_task_data(task)
                return jsonify({'sequence': employee_name, 'task_data': transformed_task})

        return jsonify({'sequence': employee_name, 'task_data': {'error': 'Нет доступных задач'}})

    else:
        if request.endpoint in sequence_buffer:
            sequence_buffer[request.endpoint].append(key)
        else:
            sequence_buffer[request.endpoint] = [key]
        logging.debug(f"Текущий ввод: {sequence_buffer[request.endpoint]}")

    return jsonify({'status': 'ok'})



def complete_task(page_name, action, done_field):
    global current_tasks
    data = request.json
    employee_id = data['employee_sequence'].replace('Shift', '')

    logging.debug(f"Получен запрос на завершение задачи. employee_id: {employee_id}")

    # Получаем task_id из глобального словаря current_tasks
    task_id = current_tasks.get(employee_id)

    if task_id is None:
        logging.error(f"Задача не найдена для сотрудника: {employee_id}")
        return jsonify({'status': 'error', 'message': 'Task not found for this employee'}), 404

    tasks = load_tasks()
    if task_id not in tasks.index:
        logging.error(f"Task ID not found in tasks: {task_id}")
        return jsonify({'status': 'error', 'message': 'Task ID not found'}), 404

    # Обновляем статус задачи
    tasks.at[task_id, done_field] = True
    employee_name = get_employee_name(employee_id)
    update_task_history(tasks, task_id, page_name, employee_name, action)
    save_to_file(tasks, tasks_cash)

    # Удаляем задачу из текущих задач сотрудника
    current_tasks.pop(employee_id, None)

    logging.debug(f"Задача {task_id} завершена сотрудником {employee_id}. Статус обновлен.")

    return jsonify({'status': 'ok'})


def update_task_history(tasks, task_id, page_name, employee_name, action):
    history_note = f'({time_now()}) {page_name} [ {employee_name} ] -> {action}; \n'
    if 'history' in tasks.columns:
        tasks.at[task_id, 'history'] += history_note
    else:
        tasks.at[task_id, 'history'] = history_note
    logging.debug(f"История задачи {task_id} обновлена: {history_note}")


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
