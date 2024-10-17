import pandas as pd
import streamlit as st

from utils.app_core import ManufacturePage


class ComponentsPage(ManufacturePage):
    def __init__(self, page_name, icon, columns_order):
        super().__init__(page_name, icon)
        self.columns_order = columns_order
        self.components_columns_config = {
            'id': st.column_config.NumberColumn("Матрас", disabled=True),
            'components_is_done': st.column_config.CheckboxColumn("Готово"),
            'deadline': st.column_config.DateColumn("Дата", format="DD.MM", disabled=True),
            'article': st.column_config.TextColumn("Артикул", disabled=True),
            'size': st.column_config.TextColumn("Размер", disabled=True),
            'attributes': st.column_config.TextColumn("Состав", width='large', disabled=True),
            'comment': st.column_config.TextColumn("Комментарий", width='medium', disabled=True),
            'photo': st.column_config.ImageColumn("Фото"),
            'history': st.column_config.TextColumn("История", width='large', disabled=True)
        }

    @staticmethod
    def get_components_df(orders):
        data = []
        for order in orders:
            for mattress_request in order.mattress_requests:
                if not mattress_request.components_is_done:
                    row = {
                        'id': mattress_request.id,
                        'order_id': order.id,
                        'high_priority': mattress_request.high_priority,
                        'deadline': order.deadline,
                        'article': mattress_request.article,
                        'size': mattress_request.size,
                        'base_fabric': mattress_request.base_fabric,
                        'side_fabric': mattress_request.side_fabric,
                        'photo': mattress_request.photo,
                        'comment': mattress_request.comment,
                        'springs': mattress_request.springs,
                        'attributes': mattress_request.attributes,
                        'components_is_done': mattress_request.components_is_done,
                        'fabric_is_done': mattress_request.fabric_is_done,
                        'gluing_is_done': mattress_request.gluing_is_done,
                        'sewing_is_done': mattress_request.sewing_is_done,
                        'packing_is_done': mattress_request.packing_is_done,
                        'history': mattress_request.history,
                        'organization': order.organization,
                        'delivery_type': order.delivery_type,
                        'address': order.address,
                        'region': order.region,
                        'created': mattress_request.created,
                    }
                    data.append(row)

        return pd.DataFrame(data)

    def components_tasks(self):
        orders = self.get_orders_with_mattress_requests()
        df = self.get_components_df(orders)
        if df.empty:
            st.write('Активных нарядов нет')
            return

        df.sort_values(by=['high_priority', 'deadline', 'order_id', 'delivery_type'],
                       ascending=[False, True, True, True],
                       inplace=True)
        if 'id' in df.columns:
            df.set_index('id', inplace=True)  # Set 'id' as the index

        return df

    @st.fragment(run_every=2)
    def components_frame(self):

        employee = st.session_state.get(self.page_name)
        if not employee:
            st.warning("Сначала отметьте сотрудника.")
            return

        tasks = self.components_tasks()
        if tasks.empty:
            st.info("Срочных заявок нет. Продолжайте нарезать обычные материалы.")
            return

        return st.data_editor(tasks[self.columns_order],
                              column_config=self.components_columns_config,
                              hide_index=False,
                              height=750)

    def components_table(self):
        submit = st.button(label='Подтвердить')

        edited_df = self.components_frame()

        if not submit or edited_df is None:
            return

        self.update_tasks(edited_df, 'components_is_done')
        st.rerun()
#  + нужно тянуть записи из базы с помощью SQLAlchemy
#  + нужно починить экран нарезки


Page = ComponentsPage(page_name='Заготовка',
                      icon="🧱",
                      columns_order=['deadline',
                                     'components_is_done',
                                     'article',
                                     'size',
                                     'attributes',
                                     'comment',
                                     'photo',
                                     'history'])

col_table, col_info = st.columns([4, 1])

with col_table:
    Page.components_table()

with col_info:
    st.info('Вы можете сортировать наряды, нажимая на поля таблицы. ', icon="ℹ️")
    st.info('Можно отметить много готовых заявок за раз и нажать кнопку "Подтвердить"', icon="ℹ️")
