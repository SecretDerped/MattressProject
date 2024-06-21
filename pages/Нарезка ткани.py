import streamlit as st

from utils.app_core import ManufacturePage
from utils.tools import side_eval, config, read_file, save_to_file, get_date_str, employee_choose, \
    is_reserved, get_reserver, time_now, set_reserver, set_reserved

page_name = 'Нарезка ткани'
page_icon = "✂️"
reserve_button_text = 'Взять'
done_button_text = 'Готово'
columns_to_display = ['fabric_is_done', 'base_fabric', 'side_fabric', 'size', 'side', 'article', 'deadline', 'comment']

cash_file = config.get('site').get('cash_filepath')


def show_cutting_table(tasks):
    with st.form(key='tasks_form'):
        inner_col_1, inner_col_2 = st.columns([4, 1])
        with inner_col_1:
            edited_tasks_df = st.data_editor(tasks[columns_to_display],  # width=600, height=600,
                                             column_config={
                                                 'fabric_is_done': st.column_config.CheckboxColumn("Готово"),
                                                 'base_fabric': st.column_config.TextColumn("Ткань (Верх / Низ)",
                                                                                            disabled=True),
                                                 'side_fabric': st.column_config.TextColumn("Ткань (Бочина)",
                                                                                            disabled=True),
                                                 'size': st.column_config.TextColumn("Размер",
                                                                                     disabled=True),
                                                 'side': st.column_config.TextColumn("Бочина",
                                                                                     disabled=True),
                                                 'article': st.column_config.TextColumn("Артикул",
                                                                                        disabled=True),
                                                 'deadline': st.column_config.DateColumn("Срок", format="DD.MM",
                                                                                         disabled=True),
                                                 'comment': st.column_config.TextColumn("Комментарий",
                                                                                        disabled=True),
                                             },
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
                            tasks.at[index, 'history'] += history_note
                            tasks.at[index, 'fabric_is_done'] = True
                    save_to_file(tasks, cash_file)
                    st.rerun()


################################################ Page ###################################################

cutting_text = """**Артикул:** {row['article']}  
 **Верх/Низ**: {row['base_fabric']}  
 **Бочина**: {row['side_fabric']}  
 **Размер:** {row['size']} ({side_eval(row['size'], row['side_fabric'])})  
 **Срок**: {get_date_str(row['deadline'])}  \n"""

Cutting = ManufacturePage(name=page_name,
                          icon=page_icon,
                          columns_order=columns_to_display,
                          box_text_template=cutting_text)

data = Cutting.load_tasks()

cutting_tasks = data[(data['fabric_is_done'] == False) &
                     (data['sewing_is_done'] == False) &
                     (data['packing_is_done'] == False)]

tab_tiles, tab_table = st.tabs(['Плитки', 'Таблица'])

with tab_tiles:
    Cutting.show_tasks_tiles(cutting_tasks)

with tab_table:
    col_table, col_info = st.columns([4, 1])
    with col_table:
        # Вычисляемое поле размера бочины.
        cutting_tasks['side'] = cutting_tasks['size'].apply(side_eval, args=(str(cutting_tasks['side_fabric']),))
        # Создаем форму для обработки изменений в таблице
        show_cutting_table(cutting_tasks)
    with col_info:
        st.info('Вы можете сортировать заявки, нажимая на поля таблицы. '
                'Попробуйте отсортировать по размеру!', icon="ℹ️")
