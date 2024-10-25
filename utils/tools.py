import os
import re
import sys
from pathlib import Path

import httpx
import tomli
import shutil
import socket
import locale

import win32print
import win32api

import pandas as pd
import aspose.pdf as ap

import logging
from logging import basicConfig, StreamHandler, FileHandler, DEBUG
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# Создание директории cash, если она не существует
if not os.path.exists('cash'):
    os.makedirs('cash')

hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))


def load_conf():
    # Определяем путь к файлу конфигурации
    if getattr(sys, 'frozen', False):
        # Если приложение собрано в один файл
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    config_path = os.path.join(base_path, "utils/app_config.toml")
    with open(config_path, 'rb') as f:
        conf = tomli.load(f)

    return conf


config = load_conf()

site_conf = config.get('site')
site_port = site_conf.get('site_port')

tg_conf = config.get('telegram')
tg_token = tg_conf.get('token')

hardware = site_conf.get('hardware')
tasks_cash = Path(hardware.get('tasks_cash_filepath'))
employees_cash = hardware.get('employees_cash_filepath')
backup_folder = hardware.get('backup_path')
log_path = hardware.get('log_filepath')
db_path = hardware.get('database_path')

log_level = DEBUG
log_format = '[%(asctime)s | %(name)s]: %(message)s'
basicConfig(level=log_level,
            format=log_format,
            handlers=(StreamHandler(sys.stdout),
                      FileHandler(log_path, mode="w")),
            encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
logging.getLogger('websockets.client').setLevel(logging.INFO)


def create_backup():
    pass


def get_size_int(size: str):
    """
    Принимает строку с размером матраса типа "180х200".
    Ищет первые два или три числа, разделенных любым символом.
    Если не находит число, ставит 0.
    :return: Словарь с размерами:
    {'length': 180,
    'width': 200,
    'height': 0}
    """

    pattern = r'(\d+)(?:\D+(\d+))?(?:\D+(\d+))?'

    match = re.search(pattern, size)
    if not match:
        return {'length': 0, 'width': 0, 'height': 0}

    length = int(match.group(1))
    width = int(match.group(2)) if match.group(2) else 0
    height = int(match.group(3)) if match.group(3) else 0
    return {'length': length, 'width': width, 'height': height}


def side_eval(size: str, fabric: str = None) -> str:
    """
    Вычисляет сколько нужно отрезать боковины, используя размер из функции get_size_int.
   Формула для вычисления размера боковины: (Длина * 2 + Ширина * 2) + корректировка
   В зависимости от типа ткани корректировка прописывается в app_config.toml,
   в разделе [fabric_corrections]
   """
    size = get_size_int(size)
    try:
        result = (size.get('length', 0) * 2 + size.get('width', 0) * 2)
        corrections = config.get('fabric_corrections', {'Текстиль': 0})

        # Ищет в названии ткани совпадения со словарём коррекций тканей и отсчитывает нужное кол-во сантиметров
        correction_value = next(
            (value for key, value in corrections.items() if re.search(key, fabric, re.IGNORECASE)), 0)

        result += correction_value

        return str(result)

    except Exception as e:
        print(e)
        return "Ошибка в вычислении размера"


def fabric_type(fabric: str = None):
    """Даёт тип ткани, основываясь на названии"""
    if fabric is None:
        return "Новый тип ткани"

    fabrics = config.get('fabric_corrections', {'Текстиль': 0})
    # Если ни одна ткань не найдётся, next вернет второе значение
    return next((key for key in fabrics.keys() if re.search(key, fabric, re.IGNORECASE)), fabric)


def get_date_str(dt_obj) -> str:
    """Принимает дату и преобразует в строку: 08 мая, среда"""
    try:
        if type(dt_obj) is pd._libs.tslibs.timestamps.Timestamp:
            date = pd.to_datetime(dt_obj).strftime('%d.%m.%A')
        else:
            date = datetime.strftime(dt_obj, '%d.%m.%A')

        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        day, month, weekday = date.split('.')

        return f'{day} {months[int(month) - 1]}, {weekday}'

    except Exception as e:
        logging.error(f'{e} -- Неизвестный тип даты: {type(dt_obj)}')
        return str(dt_obj)


def barcode_link(employee_id: str) -> str:
    """Возвращает ссылку со сгенерированным штрих-кодом."""
    return f'http://{local_ip}:{site_port}/api/barcode/{employee_id}'


def create_history_note(page_name: str,
                        employee_name: str,
                        action: str):
    """Формирует строку истории для записи в БД. Содержит текущее время, название страницы (процесса),
    имя работника и действие (завершение или бронирование).
    Пример: (21.09.2024 19:12:08) Сборка [ Иван ] -> Отметка;"""

    return f'({datetime.now().strftime("%d.%m.%Y %H:%M:%S")}) {page_name} [ {employee_name} ] -> {action}; \n'


async def send_telegram_message(text: str, chat_id: str):
    """Отправляет текстовое сообщение ботом в telegram в указанный chat_id.
    Id группы по заявкам прописывается в app_config"""

    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"

    data = {"chat_id": chat_id, "text": text}
    logging.info(f"Отправка сообщения в Telegram. URL: {url}, данные: {data}")

    response = httpx.post(url, data=data)
    logging.debug(f"Получен ответ от Telegram API: {response.json()}")
    return response.json()


def get_printers():
    """Функция для получения списка принтеров в Windows."""
    return [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]


def print_file(file_path, printer_name: str = win32print.GetDefaultPrinter()):
    """Функция для печати файла в системе Windows."""
    file_name, file_extension = os.path.splitext(file_path)
    logging.debug(f"Available printers: {get_printers()}\n Selected printer: {printer_name}")

    if file_extension.lower() == '.pdf':
        # Устанавливаем дефолтный принтер
        win32print.SetDefaultPrinterW(printer_name)
        win32print.SetDefaultPrinter(printer_name)

        document = ap.Document(file_path)
        strategy = ap.RgbToDeviceGrayConversionStrategy()

        # Loop through all the pages
        for page in document.pages:
            # Convert the RGB colorspace image to GrayScale colorspace
            strategy.convert(page)

        viewer = ap.facades.PdfViewer()  # Создать объект PDFViewer
        viewer.bind_pdf(file_path)  # Открыть входной PDF-файл
        viewer.print_document()  # Распечатать PDF-документ
        viewer.close()  # Закрыть PDF-файл

    else:
        # Устанавливаем дефолтный принтер
        win32print.SetDefaultPrinterW(printer_name)
        win32print.SetDefaultPrinter(printer_name)

        win32api.ShellExecute(
            0,
            "print",
            file_path,
            f'/d:"{printer_name}"',
            ".",
            0)


def start_scheduler(hour: int = 0, minute: int = 0) -> None:
    scheduler = BackgroundScheduler()
    trigger = CronTrigger(hour=hour, minute=minute)  # Запуск каждый день. По умолчанию в полночь
    scheduler.add_job(create_backup, trigger)
    scheduler.start()
    logging.info(f"Планировщик задач запущен. Каждый день в {hour} часов {minute} минут будет создаваться копия "
                 f"данных нарядов.")


def ensure_ngrok():
    # Создание директории utils, если она не существует
    if not os.path.exists('utils'):
        os.makedirs('utils')
    # Копирование ngrok.exe в директорию utils, если его там нет
    if not os.path.isfile('utils/ngrok.exe'):
        ngrok_path = os.path.join(os.path.dirname(__file__), 'utils/ngrok.exe')
        shutil.copy(ngrok_path, 'utils/ngrok.exe')
