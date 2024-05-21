import os

import pandas as pd
import streamlit as st

import datetime
from utils.tools import config, read_file, save_to_file

cash_file = config.get('site').get('cash_filepath')

fabrics = list(config.get('fabric_corrections'))

# TODO: настроить выгрузку из СБИС и конфигов

region = ['Краснодарский край', 'Ростовская область', 'Уральский автономный округ']

delivery_type = ['Самовывоз', "Город", "Край", "Регионы", "Страны"]

st.set_page_config(page_title="Производственный терминал",
                   page_icon="🛠️",
                   layout="wide")

CASH_STATE = 'task_dataframe'
SHOW_TABLE = 'show_table'


def cashing(dataframe):
    st.session_state[CASH_STATE] = dataframe


def get_cash():
    return st.session_state[CASH_STATE]


def clear_cash():
    if CASH_STATE in st.session_state:
        del st.session_state[CASH_STATE]


def get_editors_columns_params():
    return {
        "high_priority": st.column_config.CheckboxColumn("Приоритет", default=False),

        "deadline": st.column_config.DateColumn("Срок",
                                                min_value=datetime.date(2020, 1, 1),
                                                max_value=datetime.date(2199, 12, 31),
                                                format="DD.MM.YYYY",
                                                step=1,
                                                default=datetime.date.today()),

        "article": "Артикул",

        "size": "Размер",

        "fabric": st.column_config.SelectboxColumn("Тип ткани",
                                                   options=fabrics,
                                                   default=fabrics[0],
                                                   required=True),
        "attributes": "Состав начинки",

        "comment": st.column_config.TextColumn("Комментарий", default=''),

        "photo": st.column_config.ImageColumn("Фото", help="Кликните, чтобы развернуть"),

        "fabric_is_done": st.column_config.CheckboxColumn("Нарезано",
                                                          default=False),
        "gluing_is_done": st.column_config.CheckboxColumn("Собран",
                                                          default=False),
        "sewing_is_done": st.column_config.CheckboxColumn("Пошит",
                                                          default=False),
        "packing_is_done": st.column_config.CheckboxColumn("Упакован",
                                                           default=False),

        "delivery_type": st.column_config.SelectboxColumn("Тип доставки",
                                                          options=delivery_type,
                                                          default=delivery_type[0],
                                                          required=True),

        "address": "Адрес",

        "region": st.column_config.SelectboxColumn("Регион",
                                                   width='medium',
                                                   options=region,
                                                   default=region[0],
                                                   required=True),

        "client": "Клиент",

        "history": st.column_config.TextColumn("Действия",
                                               width='large',
                                               disabled=True),

        "created": st.column_config.DatetimeColumn("Создано",
                                                   format="D.MM.YYYY | HH:MM",
                                                   # default=datetime.datetime.today(),
                                                   disabled=True),
    }


def redact_tasks():
    """База данных в этом проекте представляет собой файл pkl с датафреймои библиотеки pandas.
    Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
    а кэш делается из session_state - текущего состояния таблицы. Каждое изменение таблицы
    провоцируют on_change методы, а потом обновление всей страницы. Поэтому стстема
    такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
    Как только какое-то поле было изменено, то изменения записываются в кэш,
    потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями
    сохраняется в базу"""

    columns = get_editors_columns_params()
    dataframe_columns_types = {'high_priority': bool,
                               'deadline': "datetime64[ns]",
                               'article': str,
                               'size': str,
                               'fabric': str,
                               'attributes': str,
                               'comment': str,
                               'photo': str,
                               'fabric_is_done': bool,
                               'gluing_is_done': bool,
                               'sewing_is_done': bool,
                               'packing_is_done': bool,
                               'address': str,
                               'delivery_type': str,
                               'region': str,
                               'client': str,
                               'history': str,
                               'created': "datetime64[ns]"}
    # Если файл с кэшем отсутсвует, создаёт его, прописывая пустые колонки из словаря настройки колонн
    if not os.path.exists(cash_file):
        base_dict = {}
        for key in columns.keys():
            base_dict[key] = []
        empty_dataframe = pd.DataFrame(base_dict)
        open(cash_file, 'w+')
        save_to_file(empty_dataframe, cash_file)

    if CASH_STATE not in st.session_state:
        dataframe = read_file(cash_file)
        dataframe = dataframe.astype(dataframe_columns_types)
        cashing(dataframe)

    edited_df = get_cash()

    editor = st.data_editor(
        edited_df,
        column_config=columns,
        hide_index=True,
        num_rows="fixed",
        on_change=cashing, args=(edited_df,),
        height=550
    )
    save_to_file(editor, cash_file)


################################################ Page ###################################################

if SHOW_TABLE not in st.session_state:
    st.session_state[SHOW_TABLE] = False

half_screen_1, half_screen_2 = st.columns(2)

with half_screen_1:
    st.title("🏭 Все заявки")
    # Кнопка для отображения/скрытия таблицы с изменением текста
    button_text = 'Открыть для редактирования' if not st.session_state[SHOW_TABLE] else 'Сохранить и свернуть'
    if st.button(button_text):
        clear_cash()  # Очистить данные, если таблица скрывается
        st.session_state[SHOW_TABLE] = not st.session_state[SHOW_TABLE]
        st.rerun()

with half_screen_2:
    st.write(' ')
    st.info('Это таблица нарядов со всей информацией в них. Отсюда можно исправлять ошибки, '
            'опечатки и редактировать почти любую информацию в текущих нарядах. '
            'Не забывайте сохранять таблицу!')

# Отображение таблицы в зависимости от состояния
if st.session_state[SHOW_TABLE]:
    redact_tasks()
