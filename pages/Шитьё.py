import streamlit as st
from utils import icon
from utils.tools import read_file, config

cash_file = config.get('site').get('cash_filepath')

st.set_page_config(page_title="Шитьё",
                   page_icon="🧵",
                   layout="wide")

@st.experimental_fragment(run_every="5s")
def show_sewing_tasks():
    # Загрузка данных
    data = read_file(cash_file)
    tasks = data[data['sewing_is_done'] == False]

    sorted_df = tasks.sort_values(by=['high_priority', 'deadline'], ascending=[False, True])
    columns_to_display = ['article', 'deadline', 'fabric', 'size']

    st.table(sorted_df[columns_to_display])


icon.show_icon("🧵")
show_sewing_tasks()
