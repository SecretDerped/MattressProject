import streamlit as st

from utils.app_core import ManufacturePage
from utils.tools import side_eval, save_to_file, get_date_str, time_now


class CuttingPage(ManufacturePage):
    def __init__(self, name, icon, columns_order):
        super().__init__(name, icon)
        self.columns_order = columns_order

    def show_cutting_table(self, tasks):
        with st.form(key='tasks_form'):
            inner_col_1, inner_col_2 = st.columns([4, 1])
            with inner_col_1:
                edited_tasks_df = st.data_editor(tasks[self.columns_order],  # width=600, height=600,
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
                st.write('Можно отметить много нарезанных заявок за раз и нажать кнопку:')
                # Добавляем кнопку подтверждения
                submit_button = st.form_submit_button(label='Подтвердить')

                if submit_button:
                    employee = st.session_state.get(self.page_name)
                    if not employee:
                        st.warning("Сначала отметьте сотрудника.")
                    else:
                        for index, row in edited_tasks_df.iterrows():
                            if row['fabric_is_done']:
                                history_note = f'({time_now()}) {self.page_name} [ {employee} ] -> {self.done_button_text}; \n'
                                tasks.at[index, 'history'] += history_note
                                tasks.at[index, 'fabric_is_done'] = True
                        save_to_file(tasks, self.task_cash)
                        st.rerun()

    @staticmethod
    def inner_box_text(row):
        return (f"**Артикул:** {row.get('article')}  \n"
                f"**Ткань (верх/низ)**: {row.get('base_fabric')}  \n"
                f"**Ткань (бочина)**: {row.get('base_fabric')}  \n"
                f"**Размер:** {row.get('size')} ({side_eval(row.get('size'), row.get('side_fabric'))})  \n"
                f"**Срок**: {get_date_str(row.get('deadline'))}  \n")


################################################ Page ###################################################


Page = CuttingPage(name='Нарезка',
                   icon="✂️",
                   columns_order=['fabric_is_done', 'base_fabric', 'side_fabric', 'size', 'side', 'article', 'deadline', 'comment'])

data = Page.load_tasks()

cutting_tasks = data[(data['fabric_is_done'] == False) &
                     (data['sewing_is_done'] == False) &
                     (data['packing_is_done'] == False)]

tab_tiles, tab_table = st.tabs(['Плитки', 'Таблица'])

with tab_tiles:
    Page.show_tasks_tiles(cutting_tasks, 'fabric_is_done', 2)

with tab_table:
    col_table, col_info = st.columns([4, 1])
    with col_table:
        # Вычисляемое поле размера бочины.
        cutting_tasks['side'] = cutting_tasks['size'].apply(side_eval, args=(str(cutting_tasks['side_fabric']),))
        # Создаем форму для обработки изменений в таблице
        Page.show_cutting_table(cutting_tasks)
    with col_info:
        st.info('Вы можете сортировать заявки, нажимая на поля таблицы. '
                'Попробуйте отсортировать по размеру!', icon="ℹ️")
