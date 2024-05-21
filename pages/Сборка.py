from datetime import datetime
import streamlit as st
from utils import icon, tools
from utils.tools import save_to_file, read_file, get_date_str

cash_file = tools.config.get('site').get('cash_filepath')
st.set_page_config(page_title="Сборка",
                   page_icon="🔨",
                   layout="wide")

columns_to_display = ['deadline', 'article', 'size', 'attributes', 'comment', 'photo']

num_columns = 1


@st.experimental_fragment(run_every="5s")
def show_gluing_tasks():
    # Загрузка данных
    data = read_file(cash_file)
    data_df = data[data['gluing_is_done'] == False]
    tasks = data_df.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                ascending=[False, True, True, False])

    row_container = st.columns(num_columns)
    count = 0
    for index, row in tasks.iterrows():
        comment = row.get('comment', '')
        deadline = get_date_str(row['deadline'])
        if count % num_columns == 0:
            row_container = st.columns(num_columns)

        box = row_container[count % num_columns].container(height=120, border=True)
        #
        text_color = 'red' if row['high_priority'] else 'gray'

        box_text = f""":{text_color}[**Арт.:** {row['article']} 
        | **Размер:** {row['size']} 
        | **Состав:** {row['attributes']} 
        | **Срок:** {deadline}
"""

        if row['comment']:
            box_text += f"| **Комментарий**: {comment} "

        if row['photo']:
            box_text += f"| [**Фото**]({row['photo']})"

        box_text += ']'

        with box:
            col1, col2 = st.columns(2)
            with col1:
                if box.button(":orange[**Выполнено**]", key=index):
                    data.at[index, 'gluing_is_done'] = True
                    data.at[index, 'history'] += f' -> Основа собрана ({datetime.now().strftime("%H:%M")})'
                    save_to_file(data, cash_file)
                    st.rerun()
            with col2:
                box.markdown(box_text)
        count += 1


icon.show_icon("🔨")
show_gluing_tasks()
