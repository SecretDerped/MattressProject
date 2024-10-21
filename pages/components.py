import streamlit as st

from utils.app_core import ManufacturePage


class ComponentsPage(ManufacturePage):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)
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

    @st.fragment(run_every=2)
    def components_frame(self):

        employee = st.session_state.get(self.page_name)
        if not employee:
            st.warning("Сначала отметьте сотрудника.")
            return

        all_tasks = self.get_sorted_tasks()
        if all_tasks is None or all_tasks.empty:
            st.info("Заявки закончились.")
            return

        tasks = self.filter_incomplete_tasks(all_tasks, {'components_is_done': False})
        # Формируем порядок показа полей от словаря конфигурации
        columns_order = list(self.components_columns_config)[1:]
        return st.data_editor(tasks[columns_order],
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


Page = ComponentsPage(page_name='Заготовка',
                      icon="🧱")

col_table, col_info = st.columns([4, 1])

with col_table:
    Page.components_table()

with col_info:
    st.info('Вы можете сортировать наряды, нажимая на поля таблицы. ', icon="ℹ️")
    st.info('Можно отметить много готовых заявок за раз и нажать кнопку "Подтвердить"', icon="ℹ️")
    st.warning("По умолчанию заявки располагаются сверху вниз в порядке приоритета. Самые срочные наверху.", icon="ℹ️")
