import locale

import streamlit as st
from utils.tools import get_size_int, side_eval, config, read_file, save_to_file, get_date_str, employee_choose, \
    is_reserved, get_reserver, time_now, set_reserver, set_reserved

page_name = 'Нарезка ткани'
page_icon = "✂️"
reserve_button_text = 'Взять'
done_button_text = 'Готово'
columns_to_display = ['fabric', 'size', 'article', 'deadline', 'comment']


cash_file = config.get('site').get('cash_filepath')
st.set_page_config(page_title=page_name,
                   page_icon=page_icon,
                   layout="wide")


@st.experimental_fragment(run_every="1s")
def show_cutting_tasks(num_columns: int = 4):
    data = read_file(cash_file)
    data_df = data[(data['fabric_is_done'] == False) &
                   (data['sewing_is_done'] == False) &
                   (data['packing_is_done'] == False)]
    tasks = data_df.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                ascending=[False, True, True, False])

    row_container = st.columns(num_columns)
    count = 0
    for index, row in tasks.iterrows():
        size = get_size_int(row['size'])
        side = side_eval(size, row['fabric'])
        deadline = get_date_str(row['deadline'])
        comment = row.get('comment', '')
        if count % num_columns == 0:
            row_container = st.columns(num_columns)

        box = row_container[count % num_columns].container(height=185, border=True)
        box_text = ''
        # Текст контейнера красится в красный, когда у наряда приоритет
        text_color = 'red' if row['high_priority'] else 'gray'
        # Проверка на бронирование
        if is_reserved(page_name, index):
            reserver = get_reserver(page_name, index)
            box_text += f":orange[**Взято - {reserver}**]  \n"
        box_text += f""":{text_color}[**Артикул:** {row['article']}  
                                     **Ткань**: {row['fabric']}  
                                     **Размер:** {row['size']} ({side})  
                                     **Срок**: {deadline}  
"""
        if row['comment']:
            box_text += f"**Комментарий**: {comment}  "
        box_text += ']'

        with box:
            photo = row['photo']
            if photo:
                col1, col2, buff, col3 = st.columns([12, 3, 1, 6])
                col2.image(photo, caption='Фото', width=80)
            else:
                col1, col3 = st.columns([3, 1])

            with col1:
                st.markdown(box_text)
            with col3:
                st.title('')
                st.subheader('')
                if page_name in st.session_state and st.session_state[page_name]:
                    if is_reserved(page_name, index):
                        if st.button(f":green[**{done_button_text}**]", key=f'{page_name}_done_{index}'):
                            data.at[index, 'fabric_is_done'] = True
                            employee = st.session_state[page_name]
                            history_note = f'({time_now()}) {page_name} [ {employee} ] -> {done_button_text}; \n'
                            data.at[index, 'history'] += history_note
                            save_to_file(data, cash_file)
                            st.rerun()
                    else:
                        if st.button(f":blue[**{reserve_button_text}**]", key=f'{page_name}_reserve_{index}'):
                            employee = st.session_state[page_name]
                            history_note = f'({time_now()}) {page_name} [ {employee} ] -> {reserve_button_text}; \n'
                            data.at[index, 'history'] += history_note
                            set_reserver(page_name, index, employee)
                            set_reserved(page_name, index, True)
                            save_to_file(data, cash_file)
                            st.rerun()

        count += 1

################################################ Page ###################################################


tab1, tab2 = st.tabs(['Плитки', 'Таблица'])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f'{page_icon} {page_name}')
    with col2:
        employee_choose(page_name)
    show_cutting_tasks(3)

with tab2:
    table = read_file(cash_file)
    tasks_df = table[table['fabric_is_done'] == False]
    sorted_tasks_df = tasks_df.sort_values(by=['high_priority', 'deadline', 'region', 'comment'], ascending=[False, True, False, False])

    col_1, col_2 = st.columns(2)

    with col_1:
        st.dataframe(sorted_tasks_df[columns_to_display],# width=600, height=600,
                     column_config={'fabric': st.column_config.TextColumn("Ткань"),
                                    'size': st.column_config.TextColumn("Размер"),
                                    'article': st.column_config.TextColumn("Артикул"),
                                    'deadline': st.column_config.DateColumn("Дата", format="DD.MM"),
                                    'comment': st.column_config.TextColumn("Комментарий")})
    with col_2:
        st.subheader('Табличное отображение данных')
        st.info('Вы можете сортировать заявки, нажимая на поля таблицы. '
                'Попробуйте отсортировать по размеру!', icon="ℹ️")

