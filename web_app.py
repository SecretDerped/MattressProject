import os
import sys
import json
import time
import logging
import subprocess
from io import BytesIO
from barcode import Code128
from datetime import datetime as dt
from flask import Flask, render_template, request, abort, jsonify

from sbis_manager import SBISWebApp
from utils.tools import load_conf, create_message_str, append_to_dataframe, save_to_file, load_tasks, \
    get_employee_column_data, time_now, get_filtered_tasks, get_date_str, fabric_type, send_telegram_message

config = load_conf()

sbis_config = config.get('sbis')
login = sbis_config.get('login')
password = sbis_config.get('password')
sale_point_name = sbis_config.get('sale_point_name')
price_list_name = sbis_config.get('price_list_name')

site_config = config.get('site')
regions = site_config.get('regions')
flask_port = site_config.get('flask_port')

hardware = site_config.get('hardware')
tasks_cash = hardware.get('tasks_cash_filepath')
employees_cash = hardware.get('employees_cash_filepath')

app = Flask(__name__)
sbis = SBISWebApp(login, password, sale_point_name, price_list_name)

nomenclatures = sbis.get_nomenclatures()
fabrics = {key: value for key, value in nomenclatures.items() if value['is_fabric']}
springs = {key: value for key, value in nomenclatures.items() if value['is_springs']}

sequence_buffer = {}
current_tasks = {}


def str_num_to_float(string: str):
    try:
        return round(float(string), 2)
    except (ValueError, TypeError):
        return 0


@app.route('/', methods=['GET', 'POST'])
def index():
    #chat_id = request.args.get('chat_id')
    if request.method == 'POST':
        logging.info(f"Получен POST-запрос. Данные формы: {request.form}")

        try:
            # Запрос возвращает строки в качестве данных
            order_data = request.form.to_dict()
            for k, v in order_data.items():
                logging.debug(f'index/ POST: {k} :: {v} ({type(v)})\n')

            order_data['positionsData'] = json.loads(order_data['positionsData'] or '{}')

            order_data['prepayment'] = str_num_to_float(order_data['prepayment'])

            mattress_quantity = 0
            total_price = 0
            # В positionsData находится только название позиции и количество.
            # По названию будут подтягиваться данные из словаря номенклатуры.
            for position in order_data['positionsData']:
                item = nomenclatures[position['article']]
                item_quantity = int(position['quantity'])

                position['price'] = str_num_to_float(position['price'])

                total_price += position['price']

                # Позиции не в группе "Матрасы" пропускаются
                if not item['is_mattress']:
                    continue
                mattress_quantity += 1

                task_data = {
                    "high_priority": False,
                    "deadline": dt.strptime(order_data['delivery_date'], '%Y-%m-%d'),
                    "article": item['article'],
                    "size": item['size'] if item['article'] != '000' else order_data.get('size', "0/0/0"),
                    "base_fabric": order_data['base_fabric'],
                    "side_fabric": order_data['side_fabric'] or order_data['base_fabric'],
                    "photo": order_data['photo_data'],
                    "comment": order_data['comment'],
                    "springs": order_data["springs"] or 'нет',
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
                for _ in range(item_quantity):
                    # Порядок task_data должен быть как в tasks_columns_config в app_core
                    append_to_dataframe(task_data, tasks_cash)

            # Вносим в реализацию ткани и пружины
            if order_data['base_fabric']:
                order_data['positionsData'].append({
                    'article': order_data['base_fabric'],
                    'quantity': mattress_quantity * (2 if not order_data['side_fabric'] else 1),
                    'price': str_num_to_float(order_data['base_fabric_price'])
                })
                if order_data['side_fabric']:
                    order_data['positionsData'].append({
                        'article': order_data['side_fabric'],
                        'quantity': mattress_quantity,
                        'price': str_num_to_float(order_data['side_fabric_price'])
                    })

            if order_data['springs']:
                order_data['positionsData'].append({
                    'article': order_data['springs'],
                    'quantity': mattress_quantity,
                    'price': str_num_to_float(order_data['springs_price'])
                })

            sbis.write_implementation(order_data)
            tg_message = create_message_str(order_data)
            send_telegram_message(tg_message)
            return "   Заявка принята.\nРеализация записана.\nНаряды созданы."

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
        message = {
            'Артикул': task['article'],
            'Состав': task['attributes'],
            'Ткань (Верх / низ)': fabric_type(task['base_fabric']),
            'Ткань (Боковина)': fabric_type(task['side_fabric']),
            'Пружины': task['springs'],
            'Размер': task['size'],
            'Срок': get_date_str(task['deadline'])
        }

        if task['comment']:
            message['Комментарий'] = f"<strong>{task['comment']}</strong>"
        return message

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
        message = {
            'Артикул': task['article'],
            'Размер': task['size'],
            'Ткань (Верх / Низ)': task['base_fabric'],
            'Ткань (Боковина)': task['side_fabric'],
            'Срок': get_date_str(task['deadline'])
        }
        if task['comment']:
            message['Комментарий'] = f"<strong>{task['comment']}</strong>"
        return message

    return log_sequence('Шитьё', 'Отметка', filter_conditions, transform_task_data)


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
    employee_name = get_employee_column_data(employee_id, 'name')
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
    global current_tasks, sequence_buffer
    endpoint = request.endpoint.replace('log_sequence_', '')
    if endpoint not in sequence_buffer:
        sequence_buffer[endpoint] = []

    data = request.json
    key = data['key']

    if key == '(':
        sequence_buffer[endpoint] = []
        logging.debug(f"Получен символ начала считывания. Инициализация приёма последовательности...")
    elif key == ')':
        employee_id = ''.join(sequence_buffer[endpoint]).replace('Shift', '')
        logging.debug(f"Завершенная последовательность: {employee_id}")

        employee_name = get_employee_column_data(employee_id, 'name')

        if not get_employee_column_data(employee_id, 'is_on_shift'):
            return jsonify({'sequence': employee_name, 'task_data': {'error': 'Жду штрих-код...\n\n\nСначала нужно открыть смену.'}})

        if page_name.lower() not in get_employee_column_data(employee_id, 'position').lower():
            return jsonify({'sequence': employee_name, 'task_data': {'error': 'Жду штрих-код...\n\n\nНет доступа.\nУточните свою должность.'}})

        tasks = load_tasks()
        if tasks.empty:
            return jsonify({'sequence': employee_name, 'task_data': {'error': 'Жду штрих-код...\n\n\nСейчас пока нет задач.'}})

        filtered_tasks = get_filtered_tasks(tasks, filter_conditions)

        if endpoint not in current_tasks:
            current_tasks[endpoint] = {}

        task_id = current_tasks[endpoint].get(employee_id)
        if task_id is not None:
            task = filtered_tasks.loc[task_id]
            logging.debug(f"Возвращаем задачу для сотрудника {employee_id}: {task.to_dict()}")
            transformed_task = transform_task_data(task)
            return jsonify({'sequence': employee_name, 'task_data': transformed_task})

        for task_id in filtered_tasks.index:
            if task_id not in current_tasks[endpoint].values():
                current_tasks[endpoint][employee_id] = task_id
                task = filtered_tasks.loc[task_id]
                update_task_history(tasks, task_id, page_name, employee_name, action)
                save_to_file(tasks, tasks_cash)
                logging.debug(f"Назначаем новую задачу сотруднику {employee_id}: {task.to_dict()}")
                transformed_task = transform_task_data(task)
                return jsonify({'sequence': employee_name, 'task_data': transformed_task})

        return jsonify({'sequence': employee_name, 'task_data': {'error': 'Жду штрих-код...\n\n\nЗадач для тебя пока нет.\nПриходи позже.'}})

    else:
        sequence_buffer[endpoint].append(key)
        logging.debug(f"Текущий ввод: {sequence_buffer[endpoint]}")

    return jsonify({'status': 'ok'})


def complete_task(page_name, action, done_field):
    global current_tasks
    data = request.json
    employee_id = data['employee_sequence'].replace('Shift', '')
    endpoint = request.endpoint.replace('complete_task_', '')

    logging.debug(f"Получен запрос на завершение задачи. employee_id: {employee_id}")

    # Получаем task_id из глобального словаря current_tasks
    print(current_tasks)
    task_id = current_tasks[endpoint].get(employee_id)

    if task_id is None:
        logging.error(f"Задача не найдена для сотрудника: {employee_id}")
        return jsonify({'status': 'error', 'message': 'Task not found for this employee'}), 404

    tasks = load_tasks()
    if task_id not in tasks.index:
        logging.error(f"Task ID not found in tasks: {task_id}")
        return jsonify({'status': 'error', 'message': 'Task ID not found'}), 404

    # Обновляем статус задачи
    tasks.at[task_id, done_field] = True
    employee_name = get_employee_column_data(employee_id, 'name')
    update_task_history(tasks, task_id, page_name, employee_name, action)
    save_to_file(tasks, tasks_cash)

    # Удаляем задачу из текущих задач сотрудника
    current_tasks[endpoint].pop(employee_id, None)

    logging.debug(f"Задача {task_id} завершена сотрудником {employee_id}. Статус обновлен.")

    return jsonify({'status': 'ok'})


def update_task_history(tasks, task_id, page_name, employee_name, action):
    history_note = f'({time_now()}) {page_name} [ {employee_name} ] -> {action}; \n'
    if 'history' in tasks.columns:
        tasks.at[task_id, 'history'] += history_note
    else:
        tasks.at[task_id, 'history'] = history_note
    logging.debug(f"История задачи {task_id} обновлена: {history_note}")


def start_ngrok():
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    ngrok_path = os.path.join(base_dir, 'utils', 'ngrok.exe')
    process = subprocess.Popen(['start', 'cmd', '/k', ngrok_path, 'http', str(flask_port)], shell=True)
    url = None

    while url is None:
        try:
            response = subprocess.check_output(['curl', '-s', 'http://localhost:4040/api/tunnels'])
            data = json.loads(response.decode('utf-8'))
            url = data['tunnels'][0]['public_url']
        except:
            time.sleep(1)

    logging.warning(f'Сайт доступен через ngrok: {url}')
    return process, url


def run_flask():
    logging.info("Запуск Flask-приложения")
    app.run(host='0.0.0.0')


if __name__ == '__main__':
    logging.info("Запуск приложения")
    ngrok_process, ngrok_url = start_ngrok()
    run_flask()

    ngrok_process.wait()
