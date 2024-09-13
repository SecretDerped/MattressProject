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
import streamlit as st
import aspose.pdf as ap

import logging
from logging import basicConfig, StreamHandler, FileHandler, INFO, DEBUG
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

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

    config_path = os.path.join(base_path, "app_config.toml")

    # Загрузка конфигурации
    with open(config_path, 'rb') as f:
        conf = tomli.load(f)

    return conf


config = load_conf()

site_conf = config.get('site')
flask_port = site_conf.get('flask_port')

tg_conf = config.get('telegram')
tg_token = tg_conf.get('token')

hardware = site_conf.get('hardware')
tasks_cash = Path(hardware.get('tasks_cash_filepath'))
employees_cash = hardware.get('employees_cash_filepath')
backup_folder = hardware.get('backup_path')
log_path = hardware.get('log_filepath')

log_format = '[%(asctime)s | %(name)s]: %(message)s'
log_level = DEBUG
basicConfig(level=log_level,
            format=log_format,
            handlers=(StreamHandler(),
                      FileHandler(log_path, mode="w")),
            encoding='utf-8')


def save_to_file(data: pd.DataFrame, filepath: str):
    data.to_pickle(filepath)


def read_file(filepath: str) -> pd.DataFrame:
    try:
        data = pd.read_pickle(filepath)
        return data
    # Иногда ввод пользователей не успевает за обновлениями базы,
    # особенно на локальном переходе со страницы на страницу,
    # поэтому тихо ловим ошибки и страницу обновляем, тогда все данные занесутся корректно.
    except (RuntimeError, EOFError):
        st.rerun()


def load_tasks(file):
    data = read_file(file)
    return data.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                            ascending=[False, True, True, False])


"""def create_backup():
    # Создание папки для бэкапов и excel, если она не существует
    os.makedirs(backup_folder, exist_ok=True)

    # Текущая дата в формате DD / MM / YYYY
    current_date = datetime.now().strftime('%d_%m_%Y')

    # Создание путей для бэкап файла и excel файла
    backup_file_path = os.path.join(backup_folder, f'{current_date}.pkl')

    # Копирование файла в папку для бэкапов
    shutil.copy2(tasks_cash, backup_file_path)
    logging.debug(f'Бэкап создан: {backup_file_path}')

    # Удаление записей старше 31 дня
    data = read_file(tasks_cash)
    cutoff_date = datetime.now() - timedelta(days=31)
    data['created'] = pd.to_datetime(data['created'])
    filtered_data = data[data['created'] > cutoff_date]

    # Сохранение обновленного DataFrame
    save_to_file(filtered_data, tasks_cash)
    logging.debug(f'Удалены старые записи, сохранено в {tasks_cash}')"""


def get_filtered_tasks(tasks, conditions):
    """Фильтрует задачи на основе переданных условий."""
    for condition in conditions:
        tasks = tasks.query(condition)
    return tasks


def append_to_dataframe(data: dict, filepath: str):
    """
    Принимает словарь для датафрейма, где ключи совпадают с названиями колонок.
    Берёт оттуда значения без ключей и формирует запись в конце указанного датафрейма.
    """
    df = read_file(filepath)
    new_row = pd.DataFrame([data])
    df = pd.concat([df, new_row], ignore_index=True)
    save_to_file(df, filepath)


def cashing(data, state):
    st.session_state[state] = data


def get_cash(state):
    return st.session_state[state]


def clear_cash(state):
    if state in st.session_state:
        del st.session_state[state]


def create_cashfile_if_empty(columns: dict, cash_filepath: str):
    """Если файл с кэшем отсутствует, создаёт его, прописывая пустые колонки
    из ключей словаря настройки колонн, типа из tasks_columns_config"""
    if not os.path.exists(cash_filepath):
        base_dict = {key: pd.Series(dtype='object') for key in columns.keys()}
        empty_dataframe = pd.DataFrame(base_dict)
        save_to_file(empty_dataframe, cash_filepath + "/task.pkl")


def get_employee_column_data(index, column):
    """
    Загружает DataFrame из файла кэша сотрудников и возвращает значение из колонки по заданному индексу.

    :param index: ID сотрудника, он же индекс строки
    :return: Значение из колонки по заданному индексу
    """
    try:
        # Загружаем DataFrame из файла .pkl
        df = pd.read_pickle(employees_cash)
        # Проверяем, что DataFrame содержит колонку 'name'
        if column not in df.columns:
            raise Exception(f"Column {column} does not exist in the DataFrame.")

        # Получаем значение из колонки по заданному индексу
        value = df[column].get(int(index))
        return value

    except FileNotFoundError:
        return f"Нет доступа к файлу '{employees_cash}'."
    except KeyError as e:
        return f"Ошибка номера сотрудника: {str(e)}"
    except Exception as e:
        return f"Системная ошибка: {str(e)}"


def scripts_in_dir(directory):
    """
    Возвращает список имен файлов .py и .html в указанной директории,
    исключая '__init__.py' и 'barcode.py'. Жуткий хардкод, но работает.

    :param directory: Путь к директории
    :return: Список имен файлов .py и .html
    """
    scripts = []
    for file in os.listdir(directory):
        if (file.endswith('.py') or file.endswith('.html')) and file not in ['__init__.py', 'barcode.html']:
            scripts.append(file)
    return scripts


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


def get_size_str(size: str):
    """
    Принимает строку и ищет в ней подстроку размера матраса типа "180х200" или 70*190.
    Ищет первые два или три числа, разделенных любым символом.
    Если не находит никаких размеров, возвращает False.
    Если не находит число, ставит '/0'.
    :return: Строка с размерами:
    'Длина/Ширина/Высота'
    """

    pattern = r'(\d+)\D(\d+)(?:\D(\d+))?'

    match = re.search(pattern, size)
    if not match:
        return False

    size_str = f'{match.group(1)}/{match.group(2)}'
    size_str += f'/{match.group(3)}' if match.group(3) else '/0'
    return size_str


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
    # Если ни один ткань не найдётся, next вернет второе значение
    value = next((key for key in fabrics.keys() if re.search(key, fabric, re.IGNORECASE)), fabric)
    return value


def get_date_str(dt_obj) -> str:
    """
    Принимает дату и преобразует в строку: 08 мая, среда
    """
    try:
        if type(dt_obj) == datetime:
            date = datetime.strftime(dt_obj, '%d.%m.%A')
        elif type(dt_obj) == pd._libs.tslibs.timestamps.Timestamp:
            date = pd.to_datetime(dt_obj).strftime('%d.%m.%A')
        else:
            logging.error(f'Неизвестный тип даты: {type(dt_obj)}')
            return str(dt_obj)
        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        day, month, weekday = date.split('.')
        return f'{day} {months[int(month) - 1]}, {weekday}'
    except Exception as e:
        return '---'


def barcode_link(id: str) -> str:
    """Возвращает ссылку со сгенерированным штрих-кодом."""
    return f'http://{local_ip}:{flask_port}/api/barcode/{id}'


def time_now():
    return datetime.now().strftime("%H:%M")


def send_telegram_message(text, chat_id: str):
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
    #scheduler.add_job(create_backup, trigger)
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
