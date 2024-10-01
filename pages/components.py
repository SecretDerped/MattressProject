import pandas as pd
import streamlit as st
from pandas.core.interchange.dataframe_protocol import DataFrame

from utils.app_core import ManufacturePage
from utils.models import MattressRequest
from utils.tools import time_now


class ComponentsPage(ManufacturePage):
    def __init__(self, page_name, icon, columns_order):
        super().__init__(page_name, icon)
        self.columns_order = columns_order
        self.components_columns_config = {
            'components_is_done': st.column_config.CheckboxColumn("Готово"),
            'deadline': st.column_config.DateColumn("Дата", format="DD.MM"),
            'article': st.column_config.TextColumn("Артикул"),
            'size': st.column_config.TextColumn("Размер"),
            'attributes': st.column_config.TextColumn("Состав", width='large'),
            'comment': st.column_config.TextColumn("Комментарий", width='medium'),
            'photo': st.column_config.ImageColumn("Фото"),
        }

    def components_tasks(self):
        mattress_requests = self.load_tasks()
        data = []
        for task in mattress_requests:
            if not (task.components_is_done or
                    task.sewing_is_done or
                    task.gluing_is_done or
                    task.packing_is_done):
                row = {
                    'id': task.id,
                    'components_is_done': task.components_is_done,
                    'deadline': task.deadline,
                    'article': task.article,
                    'size': task.size,
                    'attributes': task.attributes,
                    'comment': task.comment,
                    'photo': task.photo,
                    'history': task.history  # Include history for updates
                }
                data.append(row)
        if data:
            df = pd.DataFrame(data)
            df.set_index('id', inplace=True)  # Set 'id' as the index
            return df[self.columns_order]
        else:
            return "Нет заявок"

    def components_frame(self):
        tasks = self.components_tasks()
        return st.data_editor(tasks,
                              column_config=self.components_columns_config,
                              hide_index=True)

    def components_table(self):
        tasks_df = self.components_tasks()
        with st.form(key=f'tasks_components_form'):
            inner_col_1, inner_col_2 = st.columns([4, 1])
            with inner_col_1:
                edited_tasks_df = self.components_frame()
            with inner_col_2:
                submit_button = st.form_submit_button(label='Подтвердить')
                if submit_button:
                    employee = st.session_state.get(self.page_name)
                    if not employee:
                        st.warning("Сначала отметьте сотрудника.")
                    else:
                        for index, row in edited_tasks_df.iterrows():
                            if row['components_is_done']:
                                history_note = f'({time_now()}) {self.page_name} [ {employee} ] -> {self.done_button_text}; \n'
                                tasks_df.at[index, 'history'] += history_note
                                tasks_df.at[index, 'components_is_done'] = True
                        self.save_changes_to_db(tasks_df, MattressRequest)
                        st.rerun()


Page = ComponentsPage(page_name='Заготовка',
                      icon="🧱",
                      columns_order=['components_is_done', 'article', 'size', 'attributes', 'comment',
                                     'photo'])

col_table, col_info = st.columns([4, 1])

with col_table:
    Page.components_table()

with col_info:
    st.info('Вы можете сортировать наряды, нажимая на поля таблицы. ', icon="ℹ️")
    st.info('Можно отметить много готовых заявок за раз и нажать кнопку "Подтвердить"', icon="ℹ️")
