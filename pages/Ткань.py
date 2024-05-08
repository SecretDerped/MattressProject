import datetime
import locale
import pandas as pd
import streamlit as st
from utils import icon
from utils.tools import get_size_int, side_eval, config, read_file, save_to_file, get_date_str

cash_file = config.get('site').get('cash_filepath')
locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))
st.set_page_config(page_title="Нарезка ткани",
                   page_icon="✂️",
                   layout="wide")
columns_to_display = ['fabric', 'size', 'article', 'deadline']

num_columns = 5


@st.experimental_fragment(run_every="5s")
def show_cutting_tasks():
    # Загрузка данных
    data = read_file(cash_file)
    tasks_todo = data[data['fabric_is_done'] == False]

    sorted_df = tasks_todo.sort_values(by=['high_priority', 'deadline'], ascending=[False, True])
    row_container = st.columns(num_columns)
    n = 0
    for index, row in sorted_df.iterrows():
        size = get_size_int(row['size'])
        side = side_eval(size, row['fabric'])
        deadline = get_date_str(row['deadline'])
        if n % num_columns == 0:
            row_container = st.columns(num_columns)
        box = row_container[n % num_columns].container(height=190, border=True)

        text_color = 'red' if row['high_priority'] else 'gray'

        box_text = f""":{text_color}[**Артикул:** {row['article']}  
                                     **Тип**: {row['fabric']}  
                                     **Размер:** {row['size']} ({side})  
                                     **Срок**: {deadline}]"""
        with box:
            box.markdown(box_text)
            if box.button(":orange[**Выполнено**]", key=index):
                data.at[index, 'fabric_is_done'] = True
                save_to_file(data, cash_file)
                st.rerun()
        n += 1


st.title('✂️ Нарезка ткани')
show_cutting_tasks()
