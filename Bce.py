import os

import pandas as pd
import streamlit as st

import datetime
from utils.tools import config, read_file, save_to_file

cash_file = config.get('site').get('cash_filepath')
fabrics = list(config.get('fabric_corrections'))
articles = ["801", "802", "Уникальная"]
region = ['Краснодарский край', 'Ростовская область', 'Уральский автономный округ']
delivery_type = ['Самовывоз', "Город", "Край", "Регионы", "Страны"]
st.set_page_config(page_title="Производственный терминал",
                   page_icon="🛠️",
                   layout="wide")

CASH_STATE = 'task_dataframe'


def cashing(dataframe):
    st.session_state[CASH_STATE] = dataframe


def get_cash():
    return st.session_state[CASH_STATE]


def clear_cash():
    if CASH_STATE in st.session_state:
        del st.session_state[CASH_STATE]


def get_editors_columns_params():
    return {
        "high_priority": st.column_config.CheckboxColumn("Высокий приоритет", default=False),

        "deadline": st.column_config.DateColumn("Срок",
                                                min_value=datetime.date(2020, 1, 1),
                                                max_value=datetime.date(2199, 12, 31),
                                                format="DD.MM.YYYY",
                                                step=1,
                                                default=datetime.date.today()),

        "article": st.column_config.SelectboxColumn("Артикул",
                                                    options=articles,
                                                    default=articles[0],
                                                    required=True),

        "size": "Размер",

        "fabric": st.column_config.SelectboxColumn("Тип ткани",
                                                   options=fabrics,
                                                   default=fabrics[0],
                                                   required=True),
        "attributes": "Состав начинки",

        "comment": 'Комментарий',

        "photo": st.column_config.ImageColumn("Фото", help="Кликните, чтобы развернуть"),

        "fabric_is_done": st.column_config.CheckboxColumn("Нарезано",
                                                          default=False),
        "gluing_is_done": st.column_config.CheckboxColumn("Собран",
                                                          default=False),
        "sewing_is_done": st.column_config.CheckboxColumn("Пошит",
                                                          default=False),
        "packing_is_done": st.column_config.CheckboxColumn("Упакован",
                                                           default=False),

        "address": "Адрес",

        "region": st.column_config.SelectboxColumn("Регион",
                                                   options=region,
                                                   default=region[0],
                                                   required=True),

        "delivery_type": st.column_config.SelectboxColumn("Тип доставки",
                                                          options=delivery_type,
                                                          default=delivery_type[0],
                                                          required=True),

        "client": "Клиент",

        "history": st.column_config.TextColumn("Действия",
                                               width='large',
                                               disabled=True),

        "created": st.column_config.DatetimeColumn("Создано",
                                                   format="DD.MM.YYYY",
                                                   default=datetime.datetime.today(),
                                                   disabled=True),
    }


def redact_tasks():
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
        num_rows='fixed',
        on_change=cashing, args=(edited_df,),
        height=550
    )
    save_to_file(editor, cash_file)


################################################ Page ###################################################

half_screen_1, buff, half_screen_2 = st.columns(3)
with half_screen_1:
    st.title("🏭 Все заявки")

with half_screen_2:
    quarter_1, quarter_2, quarter_3, quarter_4 = st.columns(4)
    with quarter_4:
        st.header(' ')
        st.button('Обновить', on_click=clear_cash)

redact_tasks()
