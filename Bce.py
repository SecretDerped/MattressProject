import streamlit as st
from utils import icon
import pandas as pd
import sys
sys.path.append('sbis_manager.py')


st.set_page_config(page_title="Производственный терминал",
                   page_icon="🛠️",
                   layout="wide")

icon.show_icon("🏭")
st.title("Производственный терминал")
st.sidebar.write('Экраны')
tab1, tab2 = st.sidebar.tabs(["Все заявки", "Экран нарезки"])

tab1.write("Заявки на производство")
tab1.button('да')

tab2.write("Линия НАААрЕЕЕЗкИИИ")


df = pd.DataFrame(
    [
        {"materials": "st.selectbox", "quantity": 4, "is_unique": True},
        {"materials": "st.balloons", "quantity": 5, "is_unique": False},
        {"materials": "st.time_input", "quantity": 3, "time_input": True},
    ]
)

edited_df = st.data_editor(
    df,
    column_config={
        "materials": "Позиция",
        "quantity": st.column_config.NumberColumn(
            "Кол-во",
            min_value=1,
            max_value=999,
            step=1,
            format="%d",
        ),
        "is_unique": "Уникальный?",
    },
    num_rows="dynamic",
    disabled=["command"],
    hide_index=True,
)
print(edited_df)