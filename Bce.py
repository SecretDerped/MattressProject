import streamlit as st
from utils import icon
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

import pandas as pd
import streamlit as st

df = pd.DataFrame(
    [
        {"command": "st.selectbox", "rating": 4, "is_widget": True},
        {"command": "st.balloons", "rating": 5, "is_widget": False},
        {"command": "st.time_input", "rating": 3, "is_widget": True},
    ]
)
edited_df = st.data_editor(
    df,
    column_config={
        "command": "Streamlit Command",
        "rating": st.column_config.NumberColumn(
            "Your rating",
            help="How much do you like this command (1-5)?",
            min_value=1,
            max_value=5,
            step=1,
            format="%d ⭐",
        ),
        "is_widget": "Widget ?",
    },
    disabled=["command"],
    hide_index=True,
)

favorite_command = edited_df.loc[edited_df["rating"].idxmax()]["command"]
st.markdown(f"Your favorite command is **{favorite_command}** 🎈")