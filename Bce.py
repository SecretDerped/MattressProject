import os

import pandas as pd
import streamlit as st

import datetime
from utils.tools import config, read_file, save_to_file

task_cash = config.get('site').get('cash_filepath')

fabrics = list(config.get('fabric_corrections'))

# TODO: настроить выгрузку ткани из СБИС и конфигов

regions = config.get('site').get('regions')

delivery_type = ['Самовывоз', "Город", "Край", "Регионы", "Страны"]

st.set_page_config(page_title="Производственный терминал",
                   page_icon="🛠️",
                   layout="wide")

CASH_STATE = 'task_dataframe'
SHOW_TABLE = 'show_table'

employee_columns = {
    "is_on_shift": st.column_config.CheckboxColumn("На смене", default=False),

    "name": st.column_config.TextColumn("Имя / Фамилия"),

    "position": st.column_config.ListColumn("Роль", options=['1', "2"], required=True)
}

editors_columns = {
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
                                               options=regions,
                                               default=regions[0],
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


def cashing(dataframe):
    st.session_state[CASH_STATE] = dataframe


def get_cash():
    return st.session_state[CASH_STATE]


def clear_cash():
    if CASH_STATE in st.session_state:
        del st.session_state[CASH_STATE]


def create_cashfile_if_empty(columns: dict[st.column_config], cash_filepath: str):
    """Если файл с кэшем отсутствует, создаёт его, прописывая пустые колонки
    из ключей словаря настройки колонн, типа из get_editors_columns()"""

    if not os.path.exists(cash_filepath):
        base_dict = {}
        for key in columns.keys():
            base_dict[key] = []
        empty_dataframe = pd.DataFrame(base_dict)
        open(cash_filepath, 'w+')
        save_to_file(empty_dataframe, cash_filepath)


def redact_tasks():
    """База данных в этом проекте представляет собой файл pkl с датафреймои библиотеки pandas.
    Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
    а кэш делается из session_state - текущего состояния таблицы. Каждое изменение таблицы
    провоцируют on_change методы, а потом обновление всей страницы. Поэтому стстема
    такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
    Как только какое-то поле было изменено, то изменения записываются в кэш,
    потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями
    сохраняется в базу"""
    create_cashfile_if_empty(editors_columns, task_cash)

    # Со страницы создания заявки возвращаются только строки, поэтому тут
    # екоторые столбцы преобразуются в типы, читаемые для pandas.
    dataframe_columns_types = {'deadline': "datetime64[ns]",
                               'created': "datetime64[ns]"}
    if CASH_STATE not in st.session_state:
        dataframe = read_file(task_cash)
        dataframe = dataframe.astype(dataframe_columns_types)
        cashing(dataframe)

    edited_df = get_cash()

    editor = st.data_editor(
        edited_df,
        column_config=editors_columns,
        hide_index=True,
        num_rows="fixed",
        on_change=cashing, args=(edited_df,),
        height=420
    )
    save_to_file(editor, task_cash)


@st.experimental_fragment(run_every="2s")
def show_tasks():
    st.dataframe(data=read_file(task_cash), column_config=editors_columns, hide_index=True)


################################################ Page ###################################################

tab1, tab2 = st.tabs(['Наряды', 'Сотрудники'])

with tab1:
    if SHOW_TABLE not in st.session_state:
        st.session_state[SHOW_TABLE] = False

    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("🏭 Все наряды")
        # Кнопка для отображения/скрытия таблицы с изменением текста
        button_text = '**Перейти в режим редактирования**' if not st.session_state[SHOW_TABLE] else ":red[**Сохранить и вернуть режим просмотра**]"''
        if st.button(button_text):
            clear_cash()  # Очистить данные, если таблица скрывается
            st.session_state[SHOW_TABLE] = not st.session_state[SHOW_TABLE]
            st.rerun()

    with col2:
        st.write(' ')
        st.info('''Чтобы поправить любой наряд, включите режим редактирования.
        Он обладает высшим приоритетом - пока активен режим редактирования,
        изменения других рабочих не сохраняются. **Не забывайте сохранять таблицу!**''')

    # Отображение таблицы в зависимости от состояния
    if st.session_state[SHOW_TABLE]:
        redact_tasks()
    if not st.session_state[SHOW_TABLE]:
        show_tasks()

with tab2:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.title("👷 Сотрудники")
    with col2:
        st.write(' ')
        st.info('''Выставляйте рабочих на смену. Они будут отображаться при выборе ответственного на нужном экране.''')

