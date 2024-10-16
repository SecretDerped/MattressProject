import pandas as pd
import streamlit as st

from utils.app_core import ManufacturePage
from utils.models import MattressRequest
from utils.tools import config, side_eval


class CuttingPage(ManufacturePage):
    def __init__(self, page_name, icon, columns_order):
        super().__init__(page_name, icon)
        self.columns_order = columns_order
        self.cutting_columns_config = {
            'fabric_is_done': st.column_config.CheckboxColumn("Готово", default=False),
            'base_fabric': st.column_config.TextColumn("Ткань (Верх / Низ)", disabled=True),
            'side_fabric': st.column_config.TextColumn("Ткань (Бочина)", disabled=True),
            'size': st.column_config.TextColumn("Размер", disabled=True),
            'side': st.column_config.TextColumn("Бочина", disabled=True),
            'article': st.column_config.TextColumn("Артикул", disabled=True),
            'comment': st.column_config.TextColumn("Комментарий", disabled=True)
        }
        self.showed_articles = config['components']['showed_articles']

    def cutting_tasks(self):
        mattress_requests = self.load_tasks()
        data = []
        for mattress_request in mattress_requests:
            if mattress_request.fabric_is_done:
                continue
            row = {
                'id': mattress_request.id,
                'deadline': mattress_request.deadline,
                'high_priority': mattress_request.high_priority,
                'fabric_is_done': mattress_request.fabric_is_done,
                'base_fabric': mattress_request.base_fabric,
                'side_fabric': mattress_request.side_fabric,
                'size': mattress_request.size,
                'article': mattress_request.article,
                'comment': mattress_request.comment,
                'delivery_type': mattress_request.delivery_type,
                'history': mattress_request.history  # Include history for updates
            }
            data.append(row)

        if not data:
            return None

        df = pd.DataFrame(data)
        df.sort_values(by=['deadline', 'delivery_type', 'high_priority'],
                       ascending=[True, True, False],
                       inplace=True)
        if 'id' in df.columns:
            df.set_index('id', inplace=True)  # Set 'id' as the index

        return df

    @st.fragment(run_every=2)
    def cutting_frame(self):

        employee = st.session_state.get(self.page_name)
        if not employee:
            st.warning("Сначала отметьте сотрудника.")
            return

        tasks = self.cutting_tasks()
        if tasks is None or tasks.empty:
            st.info("Заявки закончились.")
            return

        # Формируем колонку с информацией о длине бочины, вычисляеммой динамически. Её ее требуется сохранять
        tasks['side'] = tasks['size'].apply(side_eval, args=(str(tasks['side_fabric']),))
        return st.data_editor(tasks[self.columns_order],  # width=600, height=600,
                              column_config=self.cutting_columns_config,
                              hide_index=True,
                              height=750)

    def cutting_table(self):
        submit = st.button(label='Подтвердить')

        original_df = self.cutting_tasks()
        edited_df = self.cutting_frame()

        if not submit or edited_df is None:
            return

        self.update_tasks(original_df, edited_df, 'fabric_is_done')
        self.save_mattress_df_to_db(original_df, MattressRequest)
        st.rerun()


Page = CuttingPage(page_name='Нарезка',
                   icon="✂️",
                   columns_order=['fabric_is_done', 'base_fabric', 'side_fabric', 'size', 'side', 'article', 'comment'])

col_table, col_info = st.columns([4, 1])

with col_table:
    Page.cutting_table()

with col_info:
    st.info('Вы можете сортировать заявки, нажимая на поля таблицы.', icon="ℹ️")
    st.info('Можно отметить много нарезанных заявок за раз и нажать кнопку "Подтвердить"', icon="ℹ️")
