import locale
import os
import re
import streamlit as st
import pandas as pd
import tomli
from datetime import datetime


def load_conf(path: str = "app_config.toml"):
    with open(path, "rb") as f:
        return tomli.load(f)


locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))
config = load_conf()
site_conf = config.get('site')
cash_filepath = site_conf.get('cash_filepath')
employees_cash = site_conf.get('employees_cash_filepath')


def save_to_file(data: pd.DataFrame, filepath: str):
    data.to_pickle(filepath)


def read_file(filepath: str) -> pd.DataFrame:
    try:
        return pd.read_pickle(filepath)
    # Иногда ввод пользователей не успевает за обновлениями базы,
    # особенно на локальном переходе со страницы на страницу,
    # поэтому тихо ловим ошибки и страницу обновляем, тогда все данные занесутся корректно.
    except (RuntimeError, EOFError):
        st.rerun()


def append_to_dataframe(data: dict, filepath: str):
    """
    Принимает словарь task_data. Берёт оттуда значения без ключей
    и формирует запись в конце указанного датафрейма.
    """
    df = read_file(filepath)
    row = []
    for k in data.values():
        row.append(k)
    print(row)
    df.loc[len(df.index)] = row
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
    из ключей словаря настройки колонн, типа из editors_columns"""
    if not os.path.exists(cash_filepath):
        base_dict = {key: pd.Series(dtype='object') for key in columns.keys()}
        empty_dataframe = pd.DataFrame(base_dict)
        save_to_file(empty_dataframe, cash_filepath)


def redact_table(columns: dict, cashfile: str, state: str, can_add_lines: bool = False):
    """База данных в этом проекте представляет собой файл pkl с датафреймои библиотеки pandas.
    Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
    а кэш делается из session_state - текущего состояния таблицы. Каждое изменение таблицы
    провоцируют on_change методы, а потом обновление всей страницы. Поэтому система
    такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
    Как только какое-то поле было изменено, то изменения записываются в кэш,
    потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями
    сохраняется в базу."""
    # Создаёт таблицу из настроек колонн, если её нет
    create_cashfile_if_empty(columns, cashfile)

    # Со страницы создания заявки возвращаются только строки, поэтому тут
    # некоторые столбцы преобразуются в типы, читаемые для pandas.
    dataframe_columns_types = {'deadline': "datetime64[ns]",
                               'created': "datetime64[ns]"}
    if state not in st.session_state:
        dataframe = read_file(cashfile)
        # Проверка наличия нужных колонок в датафрейме
        for col in dataframe_columns_types.keys():
            if col in dataframe.columns:
                dataframe[col] = dataframe[col].astype(dataframe_columns_types[col])
        cashing(dataframe, state)

    num_rows_state = "dynamic" if can_add_lines else "fixed"

    edited_df = get_cash(state)
    editor = st.data_editor(
        edited_df,
        column_config=columns,
        hide_index=True,
        num_rows=num_rows_state,
        on_change=cashing, args=(edited_df, state),
        height=420
    )
    save_to_file(editor, cashfile)


@st.experimental_fragment(run_every="1s")
def show_table(columns: dict, cashfile: str):
    """Показывает нередактируемую таблицу данных без индексов.
    Принимает словарь настроек колонн и путь к кэшу.
    Создаёт таблицу из настроек колонн, если её нет"""
    create_cashfile_if_empty(columns, cashfile)
    st.dataframe(data=read_file(cashfile), column_config=columns, hide_index=True)


def get_size_int(size: str):
    """
    Принимает строку с размером матраса типа "180х200".
    Ищет первые два или три числа, разделенных любым символом.
    Если не находит число, ставит 0.
    Возвращает словарь с размерами:
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
    print(f'{fabric} = ')
    try:
        result = (size.get('length', 0) * 2 + size.get('width', 0) * 2)
        corrections = config.get('fabric_corrections', {'Текстиль': 0})

        # Ищет в названии ткани совпадения со словарём коррекций тканей и отсчитывает нужное кол-во сантиметров
        correction_value = next(
            (value for key, value in corrections.items() if re.search(key, fabric, re.IGNORECASE)), 0)

        result += correction_value
        print(result)

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


def get_employees_on_shift(position: str) -> list:
    """Принимает строку для фильтрации по роли сотрудника (position).
    Читает .pkl из employees_cash_filepath, преобразует в датафрейм.
    Фильтрует записи, где значение в "is_on_shift" стоит True,
    а в колонке "position" есть подстрока из аргумента функции (независимо от регистра).
    Возвращает [список имен сотрудников на смене по искомой роли]"""
    dataframe = read_file(employees_cash)
    if 'is_on_shift' not in dataframe.columns or 'position' not in dataframe.columns:
        raise ValueError("В датафрейме сотрудников должны быть колонки 'is_on_shift' и 'position'")

    filtered_df = dataframe[(dataframe['is_on_shift'] == True) & (
        dataframe['position'].str.contains(position, case=False, na=False))]

    return filtered_df['name'].tolist()


def save_employee(position):
    """Метод для работы эффекта on_change виджета из employee_choose.
    Без него выбираемый сотрудник корректно не записывается в session_state."""
    st.session_state[position] = st.session_state[position]


@st.experimental_fragment(run_every="4s")
def employee_choose(position: str):
    """Виджет для выбора активного сотрудника для рабочего места.
    Рабочее место - строка в качестве аргумента.
    Показывает выпадающий список из сотрудников, находящихся на смене.
    При выборе сотрудника в session_state сохраняется строка с именем сотрудника под ключом с названием должности.
    Пример: st.session_state['швейный стол'] == 'Полиграф Полиграфович'"""

    st.selectbox('Ответственный',
                 options=get_employees_on_shift(position),
                 placeholder="Выберите сотрудника",
                 index=None,
                 key=position,
                 on_change=save_employee, args=(position,))


def time_now():
    return datetime.now().strftime("%H:%M")


# Функция для проверки состояния кнопки бронирования
def is_reserved(page_name, index):
    return st.session_state.get(f'{page_name}_reserved_{index}', False)


# Функция для установки состояния кнопки бронирования
def set_reserved(page_name, index, state):
    st.session_state[f'{page_name}_reserved_{index}'] = state


# Функция для получения имени пользователя, который забронировал
def get_reserver(page_name, index):
    return st.session_state.get(f'{page_name}_reserver_{index}', '')


# Функция для установки имени пользователя, который забронировал
def set_reserver(page_name, index, name):
    st.session_state[f'{page_name}_reserver_{index}'] = name


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
