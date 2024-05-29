from datetime import datetime
import streamlit as st
from utils import icon
from utils.tools import read_file, config, save_to_file, get_date_str, get_employees_on_shift

cash_file = config.get('site').get('cash_filepath')

page_name = 'Швейный стол'

st.set_page_config(page_title=page_name,
                   page_icon="🧵",
                   layout="wide")


def save_employee(position):
    st.session_state[position] = st.session_state[position]


@st.experimental_fragment(run_every="5s")
def employee_choose(position: str):
    """Возвращает список сотрудников, находящихся на смене. Поиск по должности"""

    st.selectbox('Ответственный',
                 options=get_employees_on_shift(position),
                 placeholder="Выберите сотрудника",
                 index=None,
                 key=position,
                 on_change=save_employee, args=(position,))


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
                employee = ''
                if "selected_employee" in st.session_state:
                    employee = st.session_state.selected_employee
                history_note = f'({datetime.now().strftime("%H:%M")}) -> Матрас сшит [ {employee} ]\n'
                data.at[index, 'history'] += history_note
                save_to_file(data, cash_file)
                st.rerun()
            box.markdown(box_text)

        count += 1

################################################ Page ###################################################


col1, col2 = st.columns([3, 1])
with col1:
    icon.show_icon("🧵")
with col2:
    employee_choose('швейный стол')
show_sewing_tasks(4)

#st.write(st.session_state['швейный стол'])

