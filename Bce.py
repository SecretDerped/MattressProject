import os

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Производственный терминал",
                   page_icon="🛠️",
                   layout="wide")
cash_file = 'cash.csv'
st.title("🏭 Производственный терминал")
if not os.path.exists(cash_file):
    with open(cash_file, 'w') as file:
        file.write('article,size,fabric,address,client,high_priority')

table = st.data_editor(
    pd.read_csv(cash_file, encoding='utf-8'),
    column_config={
        "index": '',
        "article": st.column_config.SelectboxColumn(
            "Позиция",
            options=["801", "802"]),
        "size": "Размер",
        "fabric": "Ткань",
        "address": "Адрес",
        "client": "Клиент",
        "high_priority": st.column_config.CheckboxColumn("Высокий приоритет", default=False)
    },
    num_rows="dynamic",
    hide_index=True,
    key='table'
)

st.write(st.session_state["table"])


st.sidebar.button("Сохранить", on_click=table.to_csv(cash_file, index=False))
st.sidebar.write(f"Заявки в работе: {len(table)}")
st.sidebar.write("Заявки нарезчика: Нан")
