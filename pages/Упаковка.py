import streamlit as st
from utils.tools import read_file, config, save_to_file, get_date_str, employee_choose, is_reserved, get_reserver, \
    time_now, set_reserver, set_reserved

page_name = 'Упаковка'
page_icon = "📦"
reserve_button_text = 'Взять'
done_button_text = 'Готово'
columns_to_display = ['deadline', 'article', 'address', 'delivery_type', 'region', 'comment']


cash_file = config.get('site').get('cash_filepath')
st.set_page_config(page_title=page_name,
                   page_icon=page_icon,
                   layout="wide")


@st.experimental_fragment(run_every="1s")
def show_packing_tasks(num_columns: int = 3):
    data = read_file(cash_file)
    data_df = data[(data['packing_is_done'] == False) &
                   (data['sewing_is_done'] == True)]
    tasks = data_df.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                ascending=[False, True, True, False])

    row_container = st.columns(num_columns)
    count = 0
    for index, row in tasks.iterrows():
        deadline = get_date_str(row['deadline'])
        comment = row.get('comment', '')
        if count % num_columns == 0:
            row_container = st.columns(num_columns)

        box = row_container[count % num_columns].container(height=291, border=True)
        box_text = ''
        text_color = 'red' if row['high_priority'] else 'gray'
        if is_reserved(page_name, index):
            reserver = get_reserver(page_name, index)
            box_text += f":orange[**Взято - {reserver}**]  \n"
        box_text += f""":{text_color}[**Артикул:** {row['article']}  
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
            if page_name in st.session_state and st.session_state[page_name]:
                if is_reserved(page_name, index):
                    if st.button(f":green[**{done_button_text}**]", key=f'{page_name}_done_{index}'):
                        data.at[index, 'packing_is_done'] = True
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
            box.markdown(box_text)
        count += 1

################################################ Page ###################################################


col1, col2 = st.columns([3, 1])
with col1:
    st.title(f'{page_icon} {page_name}')
with col2:
    employee_choose(page_name)
show_packing_tasks()
