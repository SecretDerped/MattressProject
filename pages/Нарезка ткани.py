import streamlit as st
from utils.tools import side_eval, config, read_file, save_to_file, get_date_str, employee_choose, \
    is_reserved, get_reserver, time_now, set_reserver, set_reserved

page_name = 'Нарезка ткани'
page_icon = "✂️"
reserve_button_text = 'Взять'
done_button_text = 'Готово'
columns_to_display = ['base_fabric', 'side_fabric', 'size', 'side', 'article', 'deadline', 'comment', 'fabric_is_done']

cash_file = config.get('site').get('cash_filepath')
st.set_page_config(page_title=page_name, page_icon=page_icon, layout="wide")


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
        side = side_eval(row['size'], row['side_fabric'])
        deadline = get_date_str(row['deadline'])
        comment = row.get('comment', '')
        if count % num_columns == 0:
            row_container = st.columns(num_columns)

        box = row_container[count % num_columns].container(height=195, border=True)
        box_text = ''
        # Текст контейнера красится в красный, когда у наряда приоритет
        text_color = 'red' if row['high_priority'] else 'gray'
        # Проверка на бронирование
        if is_reserved(page_name, index):
            reserver = get_reserver(page_name, index)
            box_text += f":orange[**Взято - {reserver}**]  \n"
        box_text += f""":{text_color}[**Артикул:** {row['article']}  
                                     **Верх/Низ**: {row['base_fabric']}  
                                     **Бочина**: {row['side_fabric']}  
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


def show_cutting_table(tasks_df):
    with st.form(key='tasks_form'):
        inner_col_1, inner_col_2 = st.columns([4, 1])
        with inner_col_1:
            edited_tasks_df = st.data_editor(tasks_df[columns_to_display],  # width=600, height=600,
                                             column_config={
                                                 'base_fabric': st.column_config.TextColumn("Ткань (Верх / Низ)",
                                                                                            width="medium",
                                                                                            disabled=True),
                                                 'side_fabric': st.column_config.TextColumn("Ткань (Бочина)",
                                                                                            width="medium",
                                                                                            disabled=True),
                                                 'size': st.column_config.TextColumn("Размер", disabled=True),
                                                 'side': st.column_config.TextColumn("Бочина", disabled=True),
                                                 'article': st.column_config.TextColumn("Артикул", disabled=True),
                                                 'deadline': st.column_config.DateColumn("Срок", format="DD.MM",
                                                                                         disabled=True),
                                                 'comment': st.column_config.TextColumn("Комментарий", disabled=True),
                                                 'fabric_is_done': st.column_config.CheckboxColumn("Готово")},
                                             hide_index=True)

        with inner_col_2:
            st.write('Можно отметить много заявок за раз и нажать кнопку:')
            # Добавляем кнопку подтверждения
            submit_button = st.form_submit_button(label='Подтвердить')

            if submit_button:
                employee = st.session_state.get(page_name)
                if not employee:
                    st.warning("Сначала отметьте сотрудника.")
                else:
                    for index, row in edited_tasks_df.iterrows():
                        if row['fabric_is_done']:
                            history_note = f'({time_now()}) {page_name} [ {employee} ] -> {done_button_text}; \n'
                            tasks_df.at[index, 'history'] += history_note
                            tasks_df.at[index, 'fabric_is_done'] = True
                    save_to_file(tasks_df, cash_file)
                    st.rerun()


def header():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f'{page_icon} {page_name}')
    with col2:
        employee_choose(page_name)


################################################ Page ###################################################


header()

tab1, tab2 = st.tabs(['Плитки', 'Таблица'])

with tab1:
    show_cutting_tasks(3)

with tab2:
    table = read_file(cash_file)
    tasks_df = table[(table['fabric_is_done'] == False) &
                     (table['sewing_is_done'] == False) &
                     (table['packing_is_done'] == False)]
    sorted_df = tasks_df.sort_values(by=['high_priority', 'deadline', 'region', 'comment'],
                                     ascending=[False, True, False, False])
    # Вычисляемое поле размера бочины.
    sorted_df['side'] = sorted_df['size'].apply(side_eval, args=(str(sorted_df['side_fabric']),))

    col_1, col_2 = st.columns([4, 1])

    with col_1:
        # Создаем форму для обработки изменений в таблице
        show_cutting_table(sorted_df)

    with col_2:
        st.info('Вы можете сортировать заявки, нажимая на поля таблицы. '
                'Попробуйте отсортировать по размеру!', icon="ℹ️")
