import streamlit as st

from utils.app_core import ManufacturePage
from utils.tools import fabric_type


class ComponentsPage(ManufacturePage):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)
        self.components_columns_config = {
            'components_is_done': st.column_config.CheckboxColumn("Готово"),
            'deadline': st.column_config.DateColumn("Дата", format="DD.MM", disabled=True),
            'article': st.column_config.TextColumn("Артикул", disabled=True),
            'size': st.column_config.TextColumn("Размер", disabled=True),
            'attributes': st.column_config.TextColumn("Состав", disabled=True),
            'base_fabric_type': st.column_config.TextColumn("Тип ткани (Топ)", disabled=True),
            'side_fabric_type': st.column_config.TextColumn("Тип ткани (Бок)", disabled=True),
            'comment': st.column_config.TextColumn("Комментарий", width='medium', disabled=True),
            'photo': st.column_config.ImageColumn("Фото")
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

        # Создаем копию, чтобы избежать цепных изменений одной и той же таблицы
        tasks = tasks.copy()
        # Формируем колонки с информацией о типе тканей, вычисляеммой динамически. Её не требуется сохранять
        tasks.loc[:, 'base_fabric_type'] = tasks['base_fabric'].apply(fabric_type)
        tasks.loc[:, 'side_fabric_type'] = tasks['side_fabric'].apply(fabric_type)

        # Формируем порядок показа полей от словаря конфигурации
        columns_order = list(self.components_columns_config)
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
