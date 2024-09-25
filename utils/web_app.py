import os
import re
import sys
import json
import time
import logging
import subprocess
from io import BytesIO
from typing import List

from barcode import Code128
from datetime import datetime as dt
import uvicorn
from fastapi import WebSocket, WebSocketDisconnect, FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from utils.models import Order, MattressRequest, Employee
from db_connector import async_session
from sbis_manager import SBISWebApp
from utils.tools import load_conf, time_now, get_date_str, fabric_type, send_telegram_message

config = load_conf()

sbis_config = config.get('sbis')
login = sbis_config.get('login')
password = sbis_config.get('password')
sale_point_name = sbis_config.get('sale_point_name')
price_list_name = sbis_config.get('price_list_name')

site_config = config.get('site')
delivery_types = site_config.get('delivery_types')
regions = site_config.get('regions')
site_port = site_config.get('site_port')
streamlit_port = site_config.get('streamlit_port')

hardware = site_config.get('hardware')
tasks_cash = hardware.get('tasks_cash_filepath')
employees_cash = hardware.get('employees_cash_filepath')
current_tasks_cash = hardware.get('current_tasks_cash_filepath')
tg_group_chat_id = config.get('telegram', {}).get('group_chat_id')

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
sbis = SBISWebApp(login, password, sale_point_name, price_list_name)

nomenclatures = sbis.get_nomenclatures()
fabrics = {key: value for key, value in nomenclatures.items() if value['is_fabric']}
springs = {key: value for key, value in nomenclatures.items() if value['is_springs']}
mattresses = {key: value for key, value in nomenclatures.items() if value['is_mattress']}

# Список артикулов, которые показываются на экране заготовщика, если они появляются
components_page_articles = config.get('components', {}).get('showed_articles', [])

sequence_buffer = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Обработка полученных данных
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get('/', response_class=HTMLResponse)
async def get_index(request: Request):
    logging.debug("Рендеринг шаблона index.html")
    # Здесь вы можете использовать шаблонизатор Jinja2 для рендеринга HTML
    return templates.TemplateResponse("index.html", {"request": request,
                                                     "nomenclatures": nomenclatures,
                                                     "regions": regions,
                                                     "delivery_types": delivery_types})


@app.post('/')
async def post_index(request: Request):
    order_data = await request.json()
    async with async_session() as session:
        async with session.begin():
            logging.info(f"Получен POST-запрос. Данные формы: {order_data}")

            try:
                total_price = 0

                # В этой строке будут записаны выбранные позиции в заявке. Потом эти позиции добавятся в итоговое
                # сообщение для telegram после отправки заявки
                position_str = ''

                # Запоминаем время создания наряда
                now = dt.now()

                # Сохраняем заказ
                order = Order(
                    organization=order_data.get('organization'),
                    contact=order_data.get('contact'),
                    delivery_type=order_data['deliveryType'],
                    address=order_data.get("deliveryAddress"),
                    region=order_data.get('regionSelect'),
                    created=now
                )
                session.add(order)

                # Тут формируются и добавляются матрасы в базу нарядов для работяг, если в заявке есть матрасы
                mattresses_list = order_data.get('mattresses')
                if mattresses_list:
                    for mattress in mattresses_list:

                        # Убираем текст в скобках из названий тканей в СБИС, так как работягам эта информация не нужна
                        base_fabric = remove_text_in_parentheses(mattress.get("topFabric"))
                        side_fabric = remove_text_in_parentheses(mattress.get("sideFabric"))

                        item_sbis_data = nomenclatures[mattress['name']]
                        size = mattress['size'] or item_sbis_data['size']

                        quantity = int(mattress.get('quantity', 1))

                        # Формирование части сообщения с позициями для telegram
                        mattress_str = (
                                f"Арт. {item_sbis_data['article']}, {quantity} шт. {size} \n"
                                + (f"Топ: {base_fabric}\n" if base_fabric else '')
                                + (f"Бок: {side_fabric}\n" if side_fabric else '')
                                + (f"ПБ: {mattress['springBlock']}\n" if mattress['springBlock'] else '')
                                + (f"{mattress['comment']}\n" if mattress['comment'] != '' else '')
                                + f"\n"
                        )
                        position_str += mattress_str

                        # По умолчанию матрас не отображается заготовщику, то есть components_is_done = True.
                        # Если артикул в списке components_page_articles, то components_is_done = False,
                        # а значит появится на экране заготовщика
                        components_is_done_field = item_sbis_data['article'] not in components_page_articles

                        # Цена записывается в итог
                        mattress['price'] = str_num_to_float(mattress.get('price', 0))
                        total_price += mattress['price']

                        # Формируем список матрасов для записи в датафрейм
                        for _ in range(quantity):
                            mattress_request = MattressRequest(
                                high_priority=False,
                                deadline=dt.strptime(order_data['deliveryDate'], '%Y-%m-%d'),
                                article=item_sbis_data['article'],
                                size=size,
                                base_fabric=base_fabric,
                                side_fabric=side_fabric or base_fabric,
                                photo=mattress.get('photo'),
                                comment=mattress.get('comment', ''),
                                springs=mattress["springBlock"] or 'Нет',
                                attributes=item_sbis_data['structure'],
                                components_is_done=components_is_done_field,
                                fabric_is_done=False,
                                gluing_is_done=False,
                                sewing_is_done=False,
                                packing_is_done=False,
                                history='',
                                created=now
                            )
                            # Привязываем матрасы к заказу
                            mattress_request.order = order  # Устанавливаем связь
                            session.add(mattress_request)

                await session.commit()

                # Тут формируются и добавляются допники в сообщение телеги, если в заявке есть допники
                additional_items_list = order_data.get('additionalItems')
                if additional_items_list:
                    for item in additional_items_list:
                        total_price += str_num_to_float(item['price'])
                        # Формирование части сообщения с позициями для telegram
                        position_str += f"{item['name']}, {item['quantity']} шт. \n"

                # Заранее превращаем значение предоплаты во float, записываем в JSON
                order_data['prepayment'] = str_num_to_float(order_data.get('prepayment', 0))

                # Из JSON создаётся документ реализации в СБИС
                # await sbis.write_implementation(order_data)

                # Формирование сообщения для telegram
                order_message = (
                        f"{order_data['organization']}\n"
                        f"{dt.strptime(order_data['deliveryDate'], '%Y-%m-%d').strftime('%d.%m')}\n"
                        f"{position_str}\n"
                        + (f"{order_data['contact']}\n" if order_data['contact'] else '')
                        + (f"{order_data['deliveryAddress']}\n" if order_data['deliveryAddress'] != '' else '')
                        + f"\nИтого {total_price} р.\n"
                        + (f"Предоплата {order_data['prepayment']} р.\n" if order_data['prepayment'] != 0 else '')
                        + (f"Остаток к оплате: {total_price - int(order_data['prepayment'])} р.\n" if order_data[
                                                                                                          'prepayment'] != 0 else '')
                )

                # Отправляем сформированное сообщение в группу telegram, где все заявки, и пользователю бота в ЛС
                send_telegram_message(order_message, request.query_params.get('chat_id'))
                # await send_telegram_message(order_message, tg_group_chat_id)

                # Отправка обновлений всем подключённым клиентам
                await manager.broadcast(json.dumps({
                    "event": "new_order",
                    "data": order_data
                }))

                return {"status": "success",
                        "data": "   Заявка принята.\nРеализация записана.\nНаряды созданы."}

            except Exception as e:
                logging.error(f"Необработанная ошибка: - {str(e)}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"Сообщите администратору: {str(e)}.")


@app.get('/command')
async def mirror_command():
    # URL, куда будет перенаправлен запрос
    streamlit_url = 'http://localhost:8501/command'
    # Редирект
    return RedirectResponse(url=streamlit_url)


@app.get('/gluing')
async def gluing():
    logging.debug('Рендеринг страницы склейки')
    return templates.TemplateResponse('gluing.html')


@app.post('/log_sequence_gluing')
async def log_sequence_gluing(request: Request):
    filter_conditions = [
        "components_is_done == True",
        "gluing_is_done == False",
        "sewing_is_done == False",
        "packing_is_done == False"
    ]

    def transform_task_data(task):
        message = {
            'Артикул': task.article,
            'Состав': task.attributes,
            'Ткань (Верх / низ)': fabric_type(task.base_fabric),
            'Ткань (Боковина)': fabric_type(task.side_fabric),
            'Пружины': task.springs,
            'Размер': task.size,
            'Срок': get_date_str(task.deadline)
        }

        if task.comment:
            message['Комментарий'] = f"<strong>{task.comment}</strong>"

        if task.photo:
            message['Фото'] = task.photo  # Фото в формате JPEG

        return message

    return await log_sequence(request, 'Сборка', 'Отметка', filter_conditions, transform_task_data)


@app.post('/complete_task_gluing')
async def complete_task_gluing(request: Request):
    return await complete_task(request, 'Сборка', 'Готово', 'gluing_is_done')


@app.get('/sewing')
async def sewing():
    logging.debug('Рендеринг страницы швейного стола')
    return templates.TemplateResponse('sewing.html')


@app.post('/log_sequence_sewing')
async def log_sequence_sewing(request: Request):
    filter_conditions = [
        "components_is_done == True",
        "gluing_is_done == True",
        "fabric_is_done == True",
        "sewing_is_done == False",
        "packing_is_done == False"
    ]

    def transform_task_data(task):
        message = {
            'Артикул': task.article,
            'Размер': task.size,
            'Ткань (Верх / низ)': fabric_type(task.base_fabric),
            'Ткань (Боковина)': fabric_type(task.side_fabric),
            'Срок': get_date_str(task.deadline)
        }
        if task.comment:
            message['Комментарий'] = f"<strong>{task.comment}</strong>"

        if task.photo:
            message['Фото'] = task.photo  # Фото в формате JPEG

        return message

    return log_sequence(request, 'Шитьё', 'Отметка', filter_conditions, transform_task_data)


@app.post('/complete_task_sewing')
async def complete_task_sewing(request: Request):
    return await complete_task(request, 'Шитье', 'Готово', 'sewing_is_done')


@app.get('/api/nomenclatures')
async def get_articles():
    """Запрос выдаёт список строк с названиями товаров.
    Символы строк в формате Unicode escape-последовательности"""
    logging.debug("Получен GET-запрос к /api/nomenclatures")
    return JSONResponse(content={"status": "success", "data": list(nomenclatures)})


@app.get('/api/additions')
async def get_additions():
    logging.debug("Получен GET-запрос к /api/additions")
    return JSONResponse(content={"status": "success", "data": list(set(list(nomenclatures)) - set(list(mattresses)))})


@app.get('/api/fabrics')
async def get_fabrics():
    logging.debug("Получен GET-запрос к /api/fabrics")
    return JSONResponse(content={"status": "success", "data": list(fabrics)})


@app.get('/api/springs')
async def get_springs():
    logging.debug("Получен GET-запрос к /api/springs")
    return JSONResponse(content={"status": "success", "data": list(springs)})


@app.get('/api/mattresses')
async def get_mattresses():
    """Запрос почти как /api/nomenclatures, только выдаёт
    не все товары, а список строк с названиями матрасов.
    Символы строк в формате Unicode escape-последовательности"""
    logging.debug("Получен GET-запрос к /api/mattresses")
    return JSONResponse(content={"status": "success", "data": list(mattresses)})


@app.get('/api/barcode/{employee_id}', response_class=HTMLResponse)
async def get_barcode(employee_id: int, request: Request):
    """
    Параметры:
        employee_id: ID сотрудника из базы данных.

    При переходе по ссылке на основе ID создаётся линейный штрих-код
    Code128 в формате SVG и выводится на экран.
    """

    async with async_session() as session:
        # Получаем данные о сотруднике из базы данных
        result = await session.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()

        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден.")

        employee_name = employee.name

        # Создаем BytesIO для хранения SVG-кода штрих-кода
        barcode_bytes = BytesIO()

        # Инициализация штрих-кода и запись в SVG.
        # Скобки в строке обязательны - они считаются символами начала и конца
        # считывания последовательности введённых символов на страницах работников со штрих-кодами.
        barcode = Code128(f'({employee_id})')
        barcode.write(barcode_bytes,
                      options={"module_height": 17.0,
                               "module_width": 0.9,
                               'foreground': 'black'},
                      text=employee_name)

        # Возвращаем SVG-код в качестве строки из BytesIO
        barcode_bytes.seek(0)
        svg_data = barcode_bytes.getvalue().decode('utf-8')

        # Рендерим шаблон с использованием FastAPI и Jinja2
        return templates.TemplateResponse('barcode.html', {"request": request, "svg_data": svg_data})


async def log_sequence(request: Request, page_name: str, action: str, filter_conditions: List[str],
                       transform_task_data):
    global sequence_buffer
    endpoint = request.url.path.replace('/log_sequence_', '')
    if endpoint not in sequence_buffer:
        sequence_buffer[endpoint] = []

    data = await request.json()
    key = data['key']

    if key == '(':
        sequence_buffer[endpoint] = []
        logging.debug("Получен символ начала считывания. Инициализация приёма последовательности...")
    elif key == ')':
        employee_sequence = ''.join(sequence_buffer[endpoint]).replace('Shift', '')
        logging.debug(f"Завершенная последовательность: {employee_sequence}")

        # Получение информации о сотруднике по его идентификатору
        async with async_session() as session:
            employee_id = int(employee_sequence)
            employee = await session.execute(select(Employee).where(Employee.id == employee_id))
            employee = employee.scalar_one_or_none()

            if not employee:
                return JSONResponse(content={"status": "error", "data": {'error': 'Сотрудник не найден.'}})

            if not employee.is_on_shift:
                return JSONResponse(content={"status": "error", "data": {'sequence': employee.name, 'task_data': {
                    'error': 'Сначала нужно открыть смену.'}}})

            if page_name.lower() not in employee.position.lower():
                return JSONResponse(content={"status": "error", "data": {'sequence': employee.name, 'task_data': {
                    'error': 'Нет доступа. Уточните свою должность.'}}})

            # Получение доступных задач из базы данных
            tasks_query = select(MattressRequest).where(
                *[eval(f"MattressRequest.{condition}") for condition in filter_conditions])
            tasks_result = await session.execute(tasks_query)
            tasks = tasks_result.scalars().all()

            if not tasks:
                return JSONResponse(content={"status": "error", "data": {'sequence': employee.name, 'task_data': {
                    'error': 'Сейчас пока нет задач.'}}})

            # Логика назначения задач (используем current_tasks из базы данных или кэша)
            current_tasks = load_json(current_tasks_cash)
            if endpoint not in current_tasks:
                current_tasks[endpoint] = {}

            task_id = current_tasks[endpoint].get(str(employee_id))
            if task_id:
                task = await session.get(MattressRequest, int(task_id))
                if task:
                    logging.debug(f"Возвращаем текущую задачу для сотрудника {employee_id}: {task}")
                    transformed_task = transform_task_data(task)
                    return JSONResponse(content={"status": "success",
                                                 "data": {'sequence': employee.name, 'task_data': transformed_task}})
                else:
                    # Если задача не найдена (возможно, уже выполнена), удаляем её из current_tasks
                    current_tasks[endpoint].pop(str(employee_id), None)
                    save_to_json(current_tasks, current_tasks_cash)

            # Поиск новой задачи
            for task in tasks:
                if str(task.id) not in current_tasks[endpoint].values():
                    current_tasks[endpoint][str(employee_id)] = str(task.id)
                    await update_task_history(session, task, page_name, employee.name, action)
                    await session.commit()

                    logging.debug(f"Назначаем новую задачу сотруднику {employee_id}: {task}")
                    save_to_json(current_tasks, current_tasks_cash)

                    transformed_task = transform_task_data(task)
                    return JSONResponse(content={"status": "success",
                                                 "data": {'sequence': employee.name, 'task_data': transformed_task}})
            else:
                return JSONResponse(content={"status": "error", "data": {'sequence': employee.name, 'task_data': {
                    'error': 'Задач для тебя пока нет. Приходи позже.'}}})
    else:
        sequence_buffer[endpoint].append(key)
        logging.debug(f"Текущий ввод: {sequence_buffer[endpoint]}")

    return JSONResponse(content={"status": "success"})


async def complete_task(request: Request, page_name: str, action: str, done_field: str):
    data = await request.json()
    employee_sequence = data['employee_sequence'].replace('Shift', '')
    endpoint = request.url.path.replace('/complete_task_', '')

    logging.debug(f"Получен запрос на завершение задачи. employee_sequence: {employee_sequence}")

    current_tasks = load_json(current_tasks_cash)
    task_id = current_tasks.get(endpoint, {}).get(employee_sequence)

    if not task_id:
        logging.error(f"Задача не найдена для сотрудника: {employee_sequence}")
        return JSONResponse(content={"status": "error", "data": "Task not found for this employee"}, status_code=404)

    async with async_session() as session:
        task = await session.get(MattressRequest, int(task_id))
        if not task:
            logging.error(f"Task ID not found in database: {task_id}")
            return JSONResponse(content={"status": "error", "data": "Task ID not found"}, status_code=404)

        employee = await session.execute(select(Employee).where(Employee.id == int(employee_sequence)))
        employee = employee.scalar_one_or_none()
        if not employee:
            return JSONResponse(content={"status": "error", "data": "Employee not found"}, status_code=404)

        # Обновление статуса задачи
        setattr(task, done_field, True)
        await update_task_history(session, task, page_name, employee.name, action)
        await session.commit()

        # Удаление задачи из текущих задач сотрудника
        current_tasks[endpoint].pop(employee_sequence, None)
        save_to_json(current_tasks, current_tasks_cash)

        logging.debug(f"Задача {task_id} завершена сотрудником {employee_sequence}. Статус обновлен.")

    return JSONResponse(content={"status": "success"})


async def update_task_history(session: AsyncSession, task: MattressRequest, page_name: str, employee_name: str, action: str):
    history_note = f'({time_now()}) {page_name} [ {employee_name} ] -> {action}; \n'
    if task.history:
        task.history += history_note
    else:
        task.history = history_note
    logging.debug(f"История задачи {task.id} обновлена: {history_note}")



def start_ngrok():
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    ngrok_path = os.path.join(base_dir, '', 'ngrok.exe')
    config_path = os.path.join(base_dir, '', 'ngrok.yml')
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
    logging.info("Тестовый запуск FastAPI-приложения на Uvicorn")
    uvicorn.run("web_app:app", host='0.0.0.0', port=int(site_port), reload=True)

    # ngrok_process.wait()
