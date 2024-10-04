import pandas as pd
import streamlit as st

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
            'history': st.column_config.TextColumn("Bcnjhbz", width='large')  # Include history for updates
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

        if not data:
            return None

        df = pd.DataFrame(data)
        df.set_index('id', inplace=True)  # Set 'id' as the index
        return df

    @st.fragment(run_every=2)
    def components_frame(self):

        employee = st.session_state.get(self.page_name)
        if not employee:
            st.warning("Сначала отметьте сотрудника.")
            return

        tasks = self.components_tasks()
        if tasks is None or tasks.empty:
            st.info("Срочных заявок нет. Продолжайте нарезать обычные материалы.")
            return

        return st.data_editor(tasks[self.columns_order],
                              column_config=self.components_columns_config,
                              hide_index=True)

    def components_table(self):
        submit = st.button(label='Подтвердить')

        original_df = self.components_tasks()
        edited_df = self.components_frame()

        if not submit or edited_df is None:
            return

        self.update_tasks(original_df, edited_df, 'components_is_done')
        self.save_changes_to_db(original_df, MattressRequest)
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
