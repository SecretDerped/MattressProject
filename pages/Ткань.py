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
    data = read_file(cash_file)
    tasks = data[data['fabric_is_done'] == False]
    sorted_tasks = tasks.sort_values(by=['high_priority', 'deadline'], ascending=[False, True])

    row_container = st.columns(num_columns)
    count = 0
    for index, row in sorted_tasks.iterrows():
        size = get_size_int(row['size'])
        side = side_eval(size, row['fabric'])
        deadline = get_date_str(row['deadline'])
        if count % num_columns == 0:
            row_container = st.columns(num_columns)
        box = row_container[count % num_columns].container(height=190, border=True)

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
        count += 1

################################################ Page ###################################################


tab1, tab2 = st.tabs(['Плитки', 'Таблица'])

with tab1:
    st.title('✂️ Нарезка ткани')
    show_cutting_tasks()

with tab2:
    data = read_file(cash_file)
    tasks = data[data['fabric_is_done'] == False]
    sorted_tasks = tasks.sort_values(by=['high_priority', 'deadline'], ascending=[False, True])

    col_1, col_2 = st.columns(2)

    with col_1:
        st.dataframe(sorted_tasks[columns_to_display],# width=600, height=600,
                     column_config={'fabric': st.column_config.TextColumn("Ткань"),
                                    'size': st.column_config.TextColumn("Размер"),
                                    'article': st.column_config.TextColumn("Артикул"),
                                    'deadline': st.column_config.DateColumn("Дата", format="DD.MM"),})
    with col_2:
        st.subheader('Табличное отображение данных')
