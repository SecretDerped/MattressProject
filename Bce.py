import os
import random

import streamlit as st
import pandas as pd

from datetime import date
from utils.tools import config

cash_file = config.get('site').get('cash_filepath')
fabrics = list(config.get('fabric_corrections'))
positions = ["801", "802", "Уникальная"]

st.set_page_config(page_title="Производственный терминал",
                   page_icon="🛠️",
                   layout="wide")

editor_columns = {
    "index": '',
    "high_priority": st.column_config.CheckboxColumn("Высокий приоритет", default=False),
    "deadline": st.column_config.DateColumn("Срок",
                                            min_value=date(2020, 1, 1),
                                            max_value=date(2199, 12, 31),
                                            format="DD.MM.YYYY",
                                            step=1,
                                            default=date.today()),
    "article": st.column_config.SelectboxColumn("Позиция", options=positions),
    "size": "Размер",
    "fabric": st.column_config.SelectboxColumn("Тип ткани", options=fabrics, default=fabrics[0], required=True),
    "fabric_is_done": st.column_config.CheckboxColumn("Нарезано", default=False),
    "gluing_is_done": st.column_config.CheckboxColumn("Собран", default=False),
    "sewing_is_done": st.column_config.CheckboxColumn("Пошит", default=False),
    "packing_is_done": st.column_config.CheckboxColumn("Упакован", default=False),
    "address": "Адрес",
    "client": "Клиент",
    "history": "Действия"
}


def save_to_cash(data, file):
    data.to_csv(file, index=False)


def change_state(edited_df):
    st.session_state['df_value'] = edited_df


st.title("🏭 Производственный терминал")


if not os.path.exists(cash_file):
    with open(cash_file, 'w') as file:
        first_row = ','.join(editor_columns.keys())
        file.write('high_priority,deadline,article,size,fabric,fabric_is_done,gluing_is_done,sewing_is_done,packing_is_done,address,client')

df = pd.read_csv(cash_file)
data_types_dict = {'high_priority': bool,
                   'deadline': "datetime64[ns]",
                   'article': str,
                   'size': str,
                   'fabric': str,
                   'fabric_is_done': bool,
                   'gluing_is_done': bool,
                   'sewing_is_done': bool,
                   'packing_is_done': bool,
                   'address': str,
                   'client': str}
df = df.astype(data_types_dict)

if "df_value" not in st.session_state:
    st.session_state["df_value"] = df

if "key" not in st.session_state:
    st.session_state["key"] = random.randint(0, 100000)

edited_df = st.session_state["df_value"]

editor = st.data_editor(
    edited_df,
    column_config=editor_columns,
    num_rows="dynamic",
    hide_index=False,
    on_change=change_state, args=(edited_df,),
    height=550,
    key=str(st.session_state["key"])
)
save_to_cash(editor, cash_file)

