from datetime import datetime
import streamlit as st
from utils import icon
from utils.tools import read_file, config, save_to_file, get_date_str

cash_file = config.get('site').get('cash_filepath')

columns_to_display = ['article', 'deadline', 'fabric', 'size', 'comment']

st.set_page_config(page_title="Шитьё",
                   page_icon="🧵",
                   layout="wide")

st.session_state.show_input = True


def input_submit():
    st.session_state.show_input = not st.session_state.show_input
    st.session_state.saved_text = st.session_state.input_text


# Показ поля ввода, если show_input = True
if st.session_state.show_input:
    st.text_input("Введите текст:", key="input_text", on_change=input_submit)

# Показ сохранённого текста
if "saved_text" in st.session_state:
    st.write(f"Сохранённый текст: {st.session_state.saved_text}")


@st.experimental_fragment(run_every="5s")
def show_sewing_tasks(num_columns=4):
    # Загрузка данных
    data = read_file(cash_file)
    data_df = data[data['sewing_is_done'] == False]
    tasks = data_df.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                ascending=[False, True, True, False])

    row_container = st.columns(num_columns)
    count = 0
    for index, row in tasks.iterrows():
        deadline = get_date_str(row['deadline'])
        comment = row.get('comment', '')
        if count % num_columns == 0:
            row_container = st.columns(num_columns)
        box = row_container[count % num_columns].container(height=225, border=True)

        text_color = 'red' if row['high_priority'] else 'gray'

        box_text = f""":{text_color}[**Артикул:** {row['article']}  
                                     **Ткань**: {row['fabric']}  
                                     **Размер:** {row['size']}  
                                     **Срок**: {deadline}  
"""
        if row['comment']:
            box_text += f"  **Комментарий**: {comment}  "

        box_text += ']'

        with box:
            if box.button(":green[**Выполнено**]", key=index):
                data.at[index, 'sewing_is_done'] = True
                data.at[index, 'history'] += f' -> Пошит ({datetime.now().strftime("%H:%M")})'
                save_to_file(data, cash_file)
                st.rerun()
            box.markdown(box_text)

        count += 1


icon.show_icon("🧵")
show_sewing_tasks(4)
