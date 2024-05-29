import datetime

import streamlit as st
from utils import icon
from utils.tools import read_file, config, save_to_file, get_date_str

cash_file = config.get('site').get('cash_filepath')
st.set_page_config(page_title="Упаковка",
                   page_icon="📦",
                   layout="wide")

columns_to_display = ['deadline', 'article', 'address', 'delivery_type', 'region', 'comment']
num_columns = 3


@st.experimental_fragment(run_every="5s")
def show_packing_tasks():
    # Загрузка данных
    data = read_file(cash_file)
    data_df = data[data['packing_is_done'] == False]
    tasks = data_df.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                ascending=[False, True, True, False])

    row_container = st.columns(num_columns)
    count = 0
    for index, row in tasks.iterrows():
        comment = row.get('comment', '')
        deadline = get_date_str(row['deadline'])
        if count % num_columns == 0:
            row_container = st.columns(num_columns)

        box = row_container[count % num_columns].container(height=266, border=True)

        text_color = 'red' if row['high_priority'] else 'gray'

        box_text = f""":{text_color}[**Артикул:** {row['article']}  
                                     **Размер**: {row['size']}  
                                     **Тип доставки**: {row['delivery_type']}  
                                     **Адрес:** {row['address']}  
                                     **Клиент:** {row.get('client')}  
                                     **Срок**: {deadline}  
"""

        if row['comment']:
            box_text += f"**Комментарий**: {comment}"

        box_text += ']'

        with box:
            if box.button(":orange[**Выполнено**]", key=index):
                data.at[index, 'packing_is_done'] = True
                data.at[index, 'history'] += f' -> Упакован ({datetime.datetime.now().strftime("%H:%M")})'
                save_to_file(data, cash_file)
                st.rerun()
            box.markdown(box_text)
        count += 1

################################################ Page ###################################################


icon.show_icon("📦")
show_packing_tasks()
