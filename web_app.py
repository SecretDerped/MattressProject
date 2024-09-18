import os
import re
import sys
import json
import time
import logging
import subprocess
from io import BytesIO

import requests
from waitress import serve
from barcode import Code128
from datetime import datetime as dt
from flask import Flask, render_template, request, abort, jsonify, Response

from sbis_manager import SBISWebApp
from utils.tools import load_conf, append_to_dataframe, save_to_file, load_tasks, \
    get_employee_column_data, time_now, get_filtered_tasks, get_date_str, fabric_type, send_telegram_message

config = load_conf()

sbis_config = config.get('sbis')
login = sbis_config.get('login')
password = sbis_config.get('password')
sale_point_name = sbis_config.get('sale_point_name')
price_list_name = sbis_config.get('price_list_name')

site_config = config.get('site')
delivery_types = site_config.get('delivery_types')
regions = site_config.get('regions')
flask_port = site_config.get('flask_port')
streamlit_port = site_config.get('streamlit_port')

hardware = site_config.get('hardware')
tasks_cash = hardware.get('tasks_cash_filepath')
employees_cash = hardware.get('employees_cash_filepath')
current_tasks_cash = hardware.get('current_tasks_cash_filepath')
tg_group_chat_id = config.get('telegram', {}).get('group_chat_id')

app = Flask(__name__)
sbis = SBISWebApp(login, password, sale_point_name, price_list_name)

nomenclatures = sbis.get_nomenclatures()
fabrics = {key: value for key, value in nomenclatures.items() if value['is_fabric']}
springs = {key: value for key, value in nomenclatures.items() if value['is_springs']}
mattresses = {key: value for key, value in nomenclatures.items() if value['is_mattress']}

# Список артикулов, которые показываются на экране заготовщика, если они появляются
components_page_articles = config.get('components', {}).get('showed_articles', [])

sequence_buffer = {}


def str_num_to_float(string):
    """Превращает число из строки в дробное с двумя знаками после запятой. Если не получается, возвращает 0."""
    try:
        return round(float(string), 2)
    except (ValueError, TypeError):
        return 0


def remove_text_in_parentheses(text):
    """Удаляет из строки все подстроки в скобках."""
    try:
        return re.sub(r'\(.*?\)\s*', '', text)
    except TypeError:
        return 'Нет'
    except ValueError:
        return 'ОШИБКА'


def load_json(filepath):
    """Загружает текущие задачи из JSON-файла."""
    if os.path.exists(filepath):
        with open(filepath) as file:
            return json.load(file)
    return {}


def save_to_json(data, filepath):
    """Сохраняет текущие задачи в JSON-файл."""
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)


@app.route('/', methods=['GET', 'POST'])
def index():
    tg_chat_id = request.args.get('chat_id')

    if request.method == 'POST':
        logging.info(f"Получен POST-запрос. Данные формы: {request.json}")

        try:
            order_data = request.json
            mattress_quantity = 0
            total_price = 0

            # В этой строке будут записаны выбранные позиции в заявке. Потом эти позиции добавятся в итоговое
            # сообщение для telegram после отправки заявки
            position_str = ''

            # Тут формируются и добавляются матрасы в базу нарядов для работяг, если в заявке есть матрасы
            mattresses_list = order_data.get('mattresses')
            if mattresses_list:
                for mattress in mattresses_list:
                    item_sbis_data = nomenclatures[mattress['name']]
                    item_quantity = int(mattress.get('quantity', 1))

                    mattress['price'] = str_num_to_float(mattress.get('price', 0))
                    total_price += mattress['price']
                    # По умолчанию матрас не отображается заготовщику, то есть components_is_done = True.
                    # Если артикул в списке components_page_articles, то components_is_done = False,
                    # а значит появится на экране заготовщика
                    components_is_done_field = item_sbis_data['article'] not in components_page_articles

                    # Убираем текст в скобках из названий тканей в СБИС, так как работягам эта информация не нужна
                    base_fabric = remove_text_in_parentheses(mattress.get("topFabric"))
                    side_fabric = remove_text_in_parentheses(mattress.get("sideFabric"))
                    size = mattress['size'] or item_sbis_data['size']
                    task_data = {
                        "high_priority": False,
                        "deadline": dt.strptime(order_data['deliveryDate'], '%Y-%m-%d'),
                        "article": item_sbis_data['article'],
                        "size": size,
                        "base_fabric": base_fabric,
                        "side_fabric": side_fabric or base_fabric,
                        "photo": mattress.get('photo'),
                        "comment": mattress['comment'],
                        "springs": mattress["springBlock"] or 'Нет',
                        "attributes": item_sbis_data['structure'],
                        "components_is_done": components_is_done_field,
                        "fabric_is_done": False,
                        "gluing_is_done": False,
                        "sewing_is_done": False,
                        "packing_is_done": False,
                        "history": "",
                        "organization": order_data.get('organization'),
                        "contact": order_data.get('contact'),
                        "delivery_type": order_data['deliveryType'],
                        "address": order_data.get("deliveryAddress"),
                        "region": order_data.get('regionSelect'),
                        "created": dt.now(),
                    }
                    print(f"{task_data['photo']} = ")

                    # Формирование сообщения для telegram
                    mattress_str = (
                            f"Арт. {item_sbis_data['article']}, {item_quantity} шт. {size} \n"
                            + (f"Топ: {base_fabric}\n" if base_fabric else '')
                            + (f"Бок: {side_fabric}\n" if side_fabric else '')
                            + (f"ПБ: {mattress['springBlock']}\n" if mattress['springBlock'] else '')
                            + (f"{mattress['comment']}" if mattress['comment'] != '' else '')
                    )
                    position_str += mattress_str
                    mattress_quantity += item_quantity
                    for _ in range(item_quantity):
                        append_to_dataframe(task_data, tasks_cash)

            # Тут формируются и добавляются допники в сообщение телеги, если в заявке есть допники
            additional_items_list = order_data.get('additionalItems')
            if additional_items_list:
                for item in additional_items_list:
                    total_price += item['price']
                    position_str += f"{item['article']}, {item} шт."

            # Заранее превращаем значение предоплаты во float, записываем в JSON
            order_data['prepayment'] = str_num_to_float(order_data.get('prepayment', 0))

            # Из JSON создаётся документ реализации в СБИС
            sbis.write_implementation(order_data)

            # Формирование сообщения для telegram
            order_message = (
                    f"{order_data['party']}\n"
                    f"{dt.strptime(order_data['deliveryDate'], '%Y-%m-%d').strftime('%d.%m')}\n"
                    f"{position_str}"
                    + (f"{order_data['contact']}\n" if order_data['contact'] else '')
                    + (f"{order_data['deliveryAddress']}\n" if order_data['deliveryAddress'] != '' else '')
                    + f"\nИтого {total_price} р.\n"
                    + (f"Предоплата {order_data['prepayment']} р.\n" if order_data['prepayment'] != 0 else '')
                    + (f"Остаток к оплате: {total_price - int(order_data['prepayment'])} р.\n" if order_data['prepayment'] != 0 else '')
            )

            # Отправляем сформированное сообщение в группу telegram, где все заявки, и пользователю бота в ЛС
            send_telegram_message(order_message, tg_chat_id)
            #send_telegram_message(order_message, tg_group_chat_id)

            return "   Заявка принята.\nРеализация записана.\nНаряды созданы."

        except KeyError as e:
            logging.error(f"Отсутствует обязательное поле {str(e)}", exc_info=True)
            abort(400, description=f"Отсутствует обязательное поле: {str(e)}")

        except ValueError as e:
            logging.error(f"Ошибка: неверный формат данных - {str(e)}", exc_info=True)
            abort(400, description=f"Неверный формат данных: {str(e)}")

        except Exception as e:
            logging.error(f"Необработанная ошибка: - {str(e)}", exc_info=True)
            abort(400, description=f"Сообщите администратору: {str(e)}.")

    logging.debug("Рендеринг шаблона index.html")
    return render_template('index.html',
                           nomenclatures=nomenclatures,
                           regions=regions,
                           delivery_types=delivery_types)


@app.route('/command')
def mirror_command():
    # URL, куда будет перенаправлен запрос
    streamlit_url = 'http://localhost:8501/command'

    # Получаем запрос, который пришел на /command
    req = requests.Request(method=request.method, url=streamlit_url, headers=request.headers, data=request.data,
                           params=request.args)
    prepped = req.prepare()

    # Отправляем запрос на Streamlit
    session = requests.Session()
    response = session.send(prepped)

    # Возвращаем ответ от Streamlit в качестве ответа Flask
    return Response(response.content, status=response.status_code, headers=dict(response.headers))


@app.route('/gluing')
def gluing():
    logging.debug('Рендеринг страницы склейки')
    return render_template('gluing.html')


@app.route('/log_sequence_gluing', endpoint="log_sequence_gluing", methods=['POST'])
def log_sequence_gluing():
    filter_conditions = [
        "components_is_done == True",
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

        if task['photo']:
            message['Фото'] = task['photo']  # Фото в формате JPEG

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
        "components_is_done == True",
        "gluing_is_done == True",
        "fabric_is_done == True",
        "sewing_is_done == False",
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

        if task['photo']:
            message['Фото'] = task['photo']  # Фото в формате JPEG
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


@app.route('/api/mattresses', methods=['GET'])
def get_mattresses():
    """Запрос почти как /api/nomenclatures, только выдаёт
    не все товары, а список строк с названиями матрасов.
    Символы строк в формате Unicode escape-последовательности"""
    logging.debug("Получен GET-запрос к /api/mattresses")
    return jsonify(list(mattresses))


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
    global sequence_buffer
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
            return jsonify({'sequence': employee_name,
                            'task_data': {'error': 'Жду штрих-код...\n\n\nСначала нужно открыть смену.'}})

        if page_name.lower() not in get_employee_column_data(employee_id, 'position').lower():
            return jsonify({'sequence': employee_name,
                            'task_data': {'error': 'Жду штрих-код...\n\n\nНет доступа.\nУточните свою должность.'}})

        tasks = load_tasks()
        if tasks.empty:
            return jsonify(
                {'sequence': employee_name, 'task_data': {'error': 'Жду штрих-код...\n\n\nСейчас пока нет задач.'}})

        filtered_tasks = get_filtered_tasks(tasks, filter_conditions)

        current_tasks = load_json(current_tasks_cash)  # Загрузка текущих задач
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
                save_to_json(current_tasks, current_tasks_cash)

                transformed_task = transform_task_data(task)
                return jsonify({'sequence': employee_name, 'task_data': transformed_task})

        return jsonify({'sequence': employee_name,
                        'task_data': {'error': 'Жду штрих-код...\n\n\nЗадач для тебя пока нет.\nПриходи позже.'}})

    else:
        sequence_buffer[endpoint].append(key)
        logging.debug(f"Текущий ввод: {sequence_buffer[endpoint]}")

    return jsonify({'status': 'ok'})


def complete_task(page_name, action, done_field):
    data = request.json
    employee_id = data['employee_sequence'].replace('Shift', '')
    endpoint = request.endpoint.replace('complete_task_', '')

    logging.debug(f"Получен запрос на завершение задачи. employee_id: {employee_id}")

    current_tasks = load_json(current_tasks_cash)  # Загрузка текущих задач
    # Получаем task_id из словаря current_tasks
    task_id = current_tasks.get(endpoint, {}).get(employee_id)

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
    save_to_json(current_tasks, current_tasks_cash)
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
    config_path = os.path.join(base_dir, 'utils', 'ngrok.yml')
    process = subprocess.Popen(['start', 'cmd', '/k', ngrok_path, 'start', '--all', '--config', config_path],
                               shell=True)

    urls = {}
    while len(urls) < 2:
        try:
            response = subprocess.check_output(['curl', '-s', 'http://localhost:4040/api/tunnels'])
            data = json.loads(response.decode('utf-8'))
            for tunnel in data['tunnels']:
                urls[tunnel['name']] = tunnel['public_url']
        except Exception:
            time.sleep(1)

    logging.warning(f'Flask доступен через ngrok: {urls["flask"]}')
    logging.warning(f'Streamlit доступен через ngrok: {urls["streamlit"]}')
    return process, urls


if __name__ == '__main__':
    ngrok_process, ngrok_url = start_ngrok()
    logging.info("Тестовый запуск Flask-приложения на Waitress")
    serve(app, host='0.0.0.0', port=flask_port)

    # ngrok_process.wait()
