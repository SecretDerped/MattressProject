import os
import re
import sys
import json
import time
import logging
import subprocess
from io import BytesIO

# Jvybccbz? ghjcnb? xnj z gjd`kcz yf yjdjvjlysq ahtqvdjhr b htibk pfgbkbnm yf y`v ghbkj;tybt? cjdctv yt ghtlyfpyfxtyyjt lkz nfrb[ pflfx
from barcode import Code128
from datetime import datetime as dt, datetime
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette.responses import RedirectResponse

from utils.models import Order, MattressRequest, Employee, EmployeeTask
from utils.db_connector import async_session
from utils.sbis_manager import SBISWebApp
from utils.tools import load_conf, fabric_type, send_telegram_message, create_history_note, remove_text_in_parentheses, \
    str_num_to_float

config = load_conf()

site_config = config.get('site')
regions = site_config.get('regions')
delivery_types = site_config.get('delivery_types')
fastapi_port = site_config.get('site_port')

tg_group_chat_id = config.get('telegram', {}).get('group_chat_id')

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

sbis_config = config.get('sbis')
login = sbis_config.get('login')
password = sbis_config.get('password')
sale_point_name = sbis_config.get('sale_point_name')
price_list_name = sbis_config.get('price_list_name')
sbis = SBISWebApp(login, password, sale_point_name, price_list_name)

nomenclatures = {}


def create_order_row(order):
    return Order(
        organization=order.get('organization'),
        contact=order.get('contact'),
        delivery_type=order['deliveryType'],
        address=order.get("deliveryAddress", 'г. Краснодар, ул. Демуса, д. 6а'),
        region=order.get('regionSelect'),
        deadline=dt.strptime(order.get('deliveryDate'), '%Y-%m-%d'),
        created=dt.now()
    )


def get_mattress_str(mattress, sbis_data):
    """Формирование части сообщения с позициями для telegram"""

    base_fabric = mattress.get('topFabric')
    side_fabric = mattress.get('sideFabric')
    spring_block = mattress.get('springBlock')
    comment = mattress.get('comment')

    return (
            f"Арт. {sbis_data['article']}, {mattress['quantity']} шт. {mattress['size']} \n"
            + (f"Топ: {base_fabric}\n" if base_fabric else '')
            + (f"Бок: {side_fabric}\n" if side_fabric else '')
            + (f"ПБ: {spring_block}\n" if spring_block else '')
            + (f"{comment}\n" if comment != '' else '')
            + f"\n"
    )


def form_mattress_row(mattress, sbis_data):
    # Размер по умолчанию, если не указан вручную
    if mattress['size'] == '':
        mattress['size'] = sbis_data['size']
    # Символ разделителя "/" заменит символы "*", "-" и "_" для одинакового вида,
    # и чтобы markdown в дальнейшем не ломал строку типа "190*120*20"
    mattress['size'] = re.sub(r'[*_\-|]', '/', mattress['size'])
    # Убираем текст в скобках из названий тканей в СБИС, так как работягам эта информация не нужна
    mattress["topFabric"] = remove_text_in_parentheses(mattress.get("topFabric"))
    mattress["sideFabric"] = remove_text_in_parentheses(mattress.get("sideFabric"))
    mattress["springBlock"] = remove_text_in_parentheses(mattress.get("springBlock"))
    # Преобразование и расчет цены
    mattress['price'] = str_num_to_float(mattress.get('price', 0))
    # Количество матрасов по умолчанию
    mattress['quantity'] = int(mattress.get('quantity', 1))

    return mattress


def create_mattress_row(mattress, sbis_data):
    # По умолчанию матрас не отображается заготовщику если components_is_done = True
    components_field = True
    # Если артикул в списке showed_articles, либо что-то прописали в комментарий,
    # либо размер не стандартный, то components_is_done = False
    showed_articles = config.get('components', {}).get('showed_articles', [])
    if sbis_data['article'] in showed_articles or mattress.get('comment') != '' or mattress['size'] != sbis_data['size']:
        components_field = False

    return MattressRequest(
        high_priority=False,
        article=sbis_data['article'] or '0',
        components_is_done=components_field,
        fabric_is_done=False,
        gluing_is_done=False,
        sewing_is_done=False,
        packing_is_done=False,
        base_fabric=mattress['topFabric'],
        side_fabric=mattress['sideFabric'] or mattress['topFabric'],
        springs=mattress["springBlock"] or '',
        size=mattress['size'],
        photo=mattress.get('photo'),
        comment=mattress.get('comment', ''),
        attributes=sbis_data['structure'],
        history='',
        created=dt.now()
    )


def get_order_str(order, positions, price):
    return (
            f"{order['organization']}\n"
            f"{dt.strptime(order['deliveryDate'], '%Y-%m-%d').strftime('%d.%m')}\n"
            f"{positions}\n"
            + (f"{order['contact']}\n" if order['contact'] else '')
            + (f"{order['deliveryAddress']}\n" if order['deliveryAddress'] != '' else '')
            + f"\nИтого {price} р.\n"
            + (f"Предоплата {order['prepayment']} р.\n" if order['prepayment'] != 0 else '')
            + (f"Остаток к оплате: {price - int(order['prepayment'])} р.\n" if order['prepayment'] != 0 else '')
    )


@app.get('/', response_class=HTMLResponse)
async def get_index(request: Request):
    global nomenclatures
    logging.debug("Рендеринг шаблона index.html")
    nomenclatures = sbis.get_nomenclatures()
    return templates.TemplateResponse("index.html", {"request": request,
                                                     "nomenclatures": nomenclatures,
                                                     "regions": regions,
                                                     "delivery_types": delivery_types})


@app.post('/')
async def post_index(request: Request):
    try:
        order_data = await request.json()
        # Заранее превращаем значение предоплаты во float, записываем в JSON
        order_data['prepayment'] = str_num_to_float(order_data.get('prepayment', 0))

        async with async_session() as session:
            async with session.begin():
                total_price = 0
                position_message = ''
                # Тут формируются и добавляются матрасы в базу нарядов для работяг, если в заявке есть матрасы
                mattresses_list = order_data.get('mattresses')
                if mattresses_list:
                    for mattress in mattresses_list:
                        item_sbis_data = nomenclatures[mattress['name']]
                        mattress = form_mattress_row(mattress, item_sbis_data)
                        total_price += mattress['price']
                        # Формируем сообщение для TG и сохраняем заказ и матрасы в БД
                        position_message += get_mattress_str(mattress, item_sbis_data)
                        order = create_order_row(order_data)
                        session.add(order)
                        # Добавляем матрасы, привязанные к заказу
                        for _ in range(mattress['quantity']):
                            mattress_request = create_mattress_row(mattress, item_sbis_data)
                            mattress_request.order = order  # Привязываем матрасы к заказу. Установка связи
                            session.add(mattress_request)

                # Тут формируются и добавляются допники в сообщение телеги, если в заявке есть допники
                additional_items_list = order_data.get('additionalItems')
                if additional_items_list:
                    for item in additional_items_list:
                        item['price'] = str_num_to_float(item.get('price', 0))
                        total_price += item['price']
                        # Формирование части сообщения с позициями для telegram
                        position_message += f"{item['name']}, {item['quantity']} шт. \n"

                # Отправляем сформированное сообщение в группу telegram, где все заявки, и пользователю бота в ЛС
                order_message = get_order_str(order_data, position_message, total_price)
                print(order_message)
                await send_telegram_message(order_message, request.query_params.get('chat_id'))
                # await send_telegram_message(order_message, tg_group_chat_id)

                # Из JSON создаётся документ реализации в СБИС
                # sbis.write_implementation(order_data)
                await session.commit()
                return {"status": "success",
                        "data": "   Заявка принята.\nРеализация записана.\nНаряды созданы."}

    except Exception as e:
        logging.error(f"Необработанная ошибка: - {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Сообщите администратору: {str(e)}.")


@app.get('/command')
async def mirror_command():
    # URL, куда будет перенаправлен запрос
    streamlit_url = 'http://localhost:8501/command'
    # Редирект
    return RedirectResponse(url=streamlit_url)


@app.get('/gluing')
async def gluing(request: Request):
    logging.debug('Рендеринг страницы склейки')
    return templates.TemplateResponse('gluing.html', {"request": request})


@app.post('/log_sequence_gluing')
async def log_sequence_gluing(request: Request):
    def transform_task_data(task):
        message = {
            'Артикул': task.article,
            'Состав': task.attributes,
            'Ткань (Верх / низ)': fabric_type(task.base_fabric),
            'Ткань (Боковина)': fabric_type(task.side_fabric),
            'Пружины': task.springs,
            'Размер': task.size
        }

        if task.comment:
            message['Комментарий'] = f"<strong>{task.comment}</strong>"

        if task.photo:
            message['Фото'] = task.photo  # Фото в формате JPEG

        return message

    return await log_sequence(request, 'Сборка', 'Отметка', transform_task_data)


@app.post('/complete_task_gluing')
async def complete_task_gluing(request: Request):
    return await complete_task(request, 'Сборка', 'Готово', 'gluing_is_done')


@app.get('/sewing')
async def sewing(request: Request):
    logging.debug('Рендеринг страницы швейного стола')
    return templates.TemplateResponse('sewing.html', {"request": request})


@app.post('/log_sequence_sewing')
async def log_sequence_sewing(request: Request):
    def transform_task_data(task):
        message = {
            'Артикул': task.article,
            'Размер': task.size,
            'Пружины': task.springs,
            'Ткань (Верх / низ)': task.base_fabric,
            'Ткань (Боковина)': task.side_fabric
        }

        if task.comment:
            message['Комментарий'] = f"<strong>{task.comment}</strong>"

        if task.photo:
            message['Фото'] = task.photo  # Фото в формате JPEG

        return message

    return await log_sequence(request, 'Шитьё', 'Отметка', transform_task_data)


@app.post('/complete_task_sewing')
async def complete_task_sewing(request: Request):
    return await complete_task(request, 'Шитьё', 'Готово', 'sewing_is_done')


@app.get('/api/nomenclatures')
async def get_articles():
    """Запрос выдаёт список строк с названиями товаров.
    Символы строк в формате Unicode escape-последовательности"""
    logging.debug("Получен GET-запрос к /api/nomenclatures")
    return JSONResponse(content={"status": "success", "data": list(nomenclatures)})


@app.get('/api/additions')
async def get_additions():
    logging.debug("Получен GET-запрос к /api/additions")
    mattresses = {key: value for key, value in nomenclatures.items() if value['is_mattress']}
    return JSONResponse(content={"status": "success", "data": list(set(list(nomenclatures)) - set(list(mattresses)))})


@app.get('/api/fabrics')
async def get_fabrics():
    logging.debug("Получен GET-запрос к /api/fabrics")
    fabrics = {key: value for key, value in nomenclatures.items() if value['is_fabric']}
    return JSONResponse(content={"status": "success", "data": list(fabrics)})


@app.get('/api/springs')
async def get_springs():
    logging.debug("Получен GET-запрос к /api/springs")
    springs = {key: value for key, value in nomenclatures.items() if value['is_springs']}
    springs['Нет'] = ''  # Добавляем пустую позицию на ПБ
    return JSONResponse(content={"status": "success", "data": list(springs)})


@app.get('/api/mattresses')
async def get_mattresses():
    """Запрос почти как /api/nomenclatures, только выдаёт
    не все товары, а список строк с названиями матрасов.
    Символы строк в формате Unicode escape-последовательности"""
    logging.debug("Получен GET-запрос к /api/mattresses")
    mattresses = {key: value for key, value in nomenclatures.items() if value['is_mattress']}
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
        result = await session.execute(select(Employee).where(employee_id == Employee.id))
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


async def log_sequence(request: Request,
                       page_name: str,
                       action: str,
                       transform_task_data):
    endpoint = request.url.path.replace('/log_sequence_', '')

    data = await request.json()
    sequence = data.get('sequence', '').replace('Shift', '')
    logging.debug(f"Полученная последовательность: {sequence}")

    # Проверяем, что sequence не пустая
    if not sequence:
        return JSONResponse(content={"status": "error",
                                     "data": {
                                         'error': 'Ошибка в штрих-коде.\n'
                                                  'Идентификатора нет.\n'
                                                  '\n'
                                                  'Жду штрих-код...'}})

    try:
        employee_id = int(sequence)
    except ValueError:
        return JSONResponse(content={"status": "error",
                                     "data": {
                                         'error': 'Ошибка при чтении штрих-кода.\n'
                                                  'Поднесите код так, чтобы имя было внизу.\n'
                                                  'Проверьте целостность кода и качество печати.\n'
                                                  '\n'
                                                  'Жду штрих-код...'}})

    # Получение информации о сотруднике по его идентификатору
    async with async_session() as session:
        employee = await session.get(Employee, employee_id)

        if not employee:
            return JSONResponse(content={"status": "error",
                                         "data": {'error': 'Сотрудник не найден.\n'
                                                           '\n'
                                                           'Жду штрих-код...'}})

        if not employee.is_on_shift:
            return JSONResponse(content={"status": "error",
                                         "data": {'sequence': employee.name,
                                                  'error': 'Откройте смену у бригадира.\n'
                                                           '\n'
                                                           'Жду штрих-код...'}})

        if page_name.lower() not in employee.position.lower():
            return JSONResponse(content={"status": "error",
                                         "data": {'sequence': employee.name,
                                                  'error': 'Нет доступа. Уточните должность у бригадира.\n'
                                                           '\n'
                                                           'Жду штрих-код...'}})

        # Проверяем, есть ли у сотрудника текущая задача в таблице EmployeeTask
        existing_task = await session.execute(
            select(EmployeeTask).where(
                EmployeeTask.employee_id == employee_id,
                EmployeeTask.endpoint == endpoint))
        existing_task = existing_task.scalar_one_or_none()
        if existing_task:
            # У сотрудника уже есть назначенная задача
            task = await session.get(MattressRequest, existing_task.task_id)
            return JSONResponse(content={"status": "success",
                                         "data": {'sequence': employee.name,
                                                  'task_data': transform_task_data(task)}})

        # Получение доступных задач из базы данных
        search_field = f'{endpoint}_is_done'
        match endpoint:
            case 'gluing':
                result = await session.execute(
                    select(MattressRequest)
                    .where(MattressRequest.components_is_done == True,  # Учитываем только незавершённые задачи
                    getattr(MattressRequest, search_field) == False) # Для корректной динамической постановки поискового поля нужен такой костыль. Нотация через точку не работает
                    .options(joinedload(MattressRequest.order))  # Загрузка связанных заказов
                )
            case 'sewing':
                result = await session.execute(
                    select(MattressRequest)
                    .where(MattressRequest.components_is_done == True,
                           MattressRequest.fabric_is_done == True,
                           MattressRequest.gluing_is_done == True,
                           getattr(MattressRequest, search_field) == False)
                    .options(joinedload(MattressRequest.order))
                )
        tasks = result.scalars().all()
        if not tasks:
            return JSONResponse(content={"status": "error",
                                         "data": {'sequence': employee.name,
                                                  'error': 'Сейчас пока нет задач.\n'
                                                           '\n'
                                                           'Жду штрих-код...'}})

        # Сортируем задачи по приоритетам
        tasks = sorted(tasks, key=lambda x: (
            not x.high_priority,  # False означает высокий приоритет
            x.order.deadline if x.order and x.order.deadline else datetime.max,  # Дедлайн из заказа, если он есть
            delivery_types.index(x.order.delivery_type) if x.order and x.order.delivery_type in delivery_types else len(
                delivery_types),  # Тип доставки из заказа
            not bool(x.comment)))  # True означает отсутствие комментария

        # Поиск новой задачи
        for task in tasks:
            # Проверяем, назначена ли задача другим сотрудникам
            task_assigned = await session.execute(select(EmployeeTask).where(
                EmployeeTask.task_id == task.id,
                EmployeeTask.endpoint == endpoint))
            task_assigned = task_assigned.scalar_one_or_none()
            if task_assigned:
                continue

            # Назначаем задачу сотруднику
            employee_task = EmployeeTask(
                employee_id=employee_id,
                task_id=task.id,
                endpoint=endpoint)
            session.add(employee_task)
            await update_task_history(session, task, page_name, employee.name, action)
            await session.commit()
            return JSONResponse(content={"status": "success",
                                         "data": {'sequence': employee.name,
                                                  'task_data': transform_task_data(task)}})

        return JSONResponse(content={"status": "error",
                                     "data": {'sequence': employee.name,
                                              'error': 'Задач для тебя пока нет. Приходи позже.\n'
                                                       '\n'
                                                       'Жду штрих-код...'}})


async def complete_task(request: Request, page_name: str, action: str, done_field: str):
    data = await request.json()
    employee_sequence = data['employee_sequence'].replace('Shift', '')
    endpoint = request.url.path.replace('/complete_task_', '')

    logging.debug(f"Получен запрос на завершение задачи. employee_sequence: {employee_sequence}")

    try:
        employee_id = int(employee_sequence)
    except ValueError:
        return JSONResponse(content={"status": "error",
                                     "data": {'sequence': employee_sequence,
                                              'error': 'Некорректный ID сотрудника. Назначьте число в качестве идетификатора и замените штрих-код.\n\nЖду штрих-код...'}})

    async with async_session() as session:
        # Получаем текущую задачу сотрудника
        result = await session.execute(select(EmployeeTask).where(
            EmployeeTask.employee_id == employee_id,
            EmployeeTask.endpoint == endpoint))
        employee_task = result.scalar_one_or_none()
        if not employee_task:
            logging.error(f"EmployeeTask ID doesn't found in database for Employee ID {employee_id}")
            return JSONResponse(content={"status": "error",
                                         "data": {'sequence': employee_id,
                                                  'error': 'Этой брони больше нет'}},
                                status_code=404)

        task = await session.get(MattressRequest, employee_task.task_id)
        if not task:
            logging.error(f"MattressRequest ID doesn't found in database: {employee_task.task_id}")
            return JSONResponse(content={"status": "error",
                                         "data": {'sequence': employee_id,
                                                  'error': f"Этого матраса больше нет"}},
                                status_code=404)

        employee = await session.get(Employee, employee_id)
        if not employee:
            logging.error(f"Employee ID doesn't found in database: {employee_id}")
            return JSONResponse(content={"status": "error",
                                         "data": {'sequence': employee_id,
                                                  'error': f"Сотрудник не найден"}},
                                status_code=404)

        # Обновление статуса задачи
        setattr(task, done_field, True)
        await update_task_history(session, task, page_name, employee.name, action)
        # Удаление задачи из текущих задач сотрудника
        await session.delete(employee_task)

        # Завершение
        await session.commit()
        logging.debug(f"Задача {task.id} завершена сотрудником {employee_id}. Статус обновлен.")
    return JSONResponse(content={"status": "success"})


async def update_task_history(session: AsyncSession, task: MattressRequest,
                              page_name: str,
                              employee_name: str,
                              action: str):
    history_note = create_history_note(page_name, employee_name, action)
    task.history = history_note if not task.history else history_note + task.history
    logging.debug(f"История задачи {task.id} обновлена: {history_note}")

    await session.commit()


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
            time.sleep(0.5)

    logging.warning(f'FastAPI доступен через ngrok: {urls["fastapi"]}')
    logging.warning(f'Streamlit доступен через ngrok: {urls["streamlit"]}')
    return process, urls


if __name__ == '__main__':
    ngrok_process, ngrok_url = start_ngrok()
    logging.info("Тестовый запуск FastAPI-приложения на Uvicorn")
    uvicorn.run("web_app:app", host='0.0.0.0', port=int(fastapi_port), reload=True)

    # ngrok_process.wait()
