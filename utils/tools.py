import locale
import logging
import os
import re
import shutil
import socket
import sys

import streamlit as st
import pandas as pd
import tomli
from datetime import datetime


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


locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))

config = load_conf()

hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

site_conf = config.get('site')
tasks_cash = site_conf.get('tasks_cash_filepath')
employees_cash = site_conf.get('employees_cash_filepath')
backup_folder = site_conf.get('backup_path')
flask_port = site_conf.get('flask_port')


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


def load_tasks():
    data = read_file(tasks_cash)
    return data.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                            ascending=[False, True, True, False])


def create_backup():
    # Создание папки для бэкапов и excel, если она не существует
    os.makedirs(backup_folder, exist_ok=True)

    # Текущая дата в формате DD / MM / YYYY
    current_date = datetime.now().strftime('%d_%m_%Y')

    # Создание путей для бэкап файла и excel файла
    backup_file_path = os.path.join(backup_folder, f'{current_date}.pkl')

    # Копирование файла в папку для бэкапов
    shutil.copy2(tasks_cash, backup_file_path)
    logging.debug(f'Бэкап создан: {backup_file_path}')


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


def cashing(dataframe, state):
    st.session_state[state] = dataframe


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
        save_to_file(empty_dataframe, cash_filepath)


def get_employee_name(index):
    """
    Загружает DataFrame из файла кэша сотрудников и возвращает значение из колонки 'name' по заданному индексу.

    :param index: ID сотрудника, он же индекс строки
    :return: Значение из колонки 'name' по заданному индексу
    """
    try:
        # Загружаем DataFrame из файла .pkl
        df = pd.read_pickle(employees_cash)
        # Проверяем, что DataFrame содержит колонку 'name'
        if 'name' not in df.columns:
            raise KeyError("Column 'name' does not exist in the DataFrame.")

        # Получаем значение из колонки 'name' по заданному индексу
        name_value = df['name'].get(int(index), 'Неизвестен')
        return name_value

    except FileNotFoundError:
        return f"Нет доступа к файлу '{employees_cash}'."
    except KeyError as e:
        return str(e)
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


def get_date_str(dataframe_row: pd.Series) -> str:
    """
    Принимает дату из датафрейма и преобразует в строку: 08 мая, среда
    """
    date = pd.to_datetime(dataframe_row).strftime('%d.%m.%A')
    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    day, month, weekday = date.split('.')
    return f'{day} {months[int(month) - 1]}, {weekday}'


def barcode_link(id: str) -> str:
    """Возвращает ссылку со сгенерированным штрих-кодом."""
    return f'http://{local_ip}:{flask_port}/api/barcode/{id}'


def time_now():
    return datetime.now().strftime("%H:%M")


def create_message_str(data):
    positions_data = data['positionsData']
    positions = "\n".join([f"{item['article']} - {item['quantity']} шт." for item in positions_data])
    date = data['delivery_date']
    type = data['delivery_type']
    region = data['region_select']
    address = data['delivery_address']
    price = data.get('price', 'Не указано')
    prepay = data['prepayment']
    to_reserve = data['amount_to_receive']
    comment = data['comment']
    order_message = (f"Заявка от клиента: {data['party']}\n\n"
                     
                     f"Позиции:\n{positions}\n\n"
                     
                     f"Дата получения: {date}\n"
                     f"Тип доставки: {type}\n"
                     f"Регион: {region}\n")
    if address != '':
        order_message += f"Адрес:\n {address}\n\n"

    order_message += f"Цена: {price}\n"
    if prepay != '0':
        order_message += f"Предоплата: {prepay}\n"
    order_message += f"Нужно получить: {to_reserve}"

    if comment != '':
        order_message += f"\n\nКомментарий: {comment}"

    return order_message


if __name__ == "__main__":
    # Пример использования
    input_string_1 = "Размеры: 10x20 см"
    input_string_2 = "20 10"
    dimensions_1 = get_size_int(input_string_1)
    dimensions_2 = get_size_int(input_string_2)
    print(dimensions_1)  # Вывод: {'length': 10, 'width': 20, 'height': None}
    print(dimensions_2)  # Вывод: {'length': 10, 'width': 20, 'height': 30}
