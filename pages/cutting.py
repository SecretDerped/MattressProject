import streamlit as st

from utils.app_core import ManufacturePage
from utils.tools import config, side_eval


class CuttingPage(ManufacturePage):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)
        self.cutting_columns_config = {
            'deadline': st.column_config.DateColumn("Дата", format="DD.MM", disabled=True),
            'fabric_is_done': st.column_config.CheckboxColumn("Готово", default=False),
            'article': st.column_config.TextColumn("Артикул", disabled=True),
            'base_fabric': st.column_config.TextColumn("Ткань (Верх / Низ)", disabled=True),
            'side_fabric': st.column_config.TextColumn("Ткань (Бочина)", disabled=True),
            'size': st.column_config.TextColumn("Размер", disabled=True),
            'side': st.column_config.TextColumn("Бочина", disabled=True),
            'comment': st.column_config.TextColumn("Комментарий", disabled=True),
            'photo': st.column_config.ImageColumn("Фото")
        }
        self.showed_articles = config['components']['showed_articles']

    @st.fragment(run_every=2)
    def cutting_frame(self):

        employee = st.session_state.get(self.page_name)
        if not employee:
            st.warning("Сначала отметьте сотрудника.")
            return

        all_tasks = self.get_sorted_tasks()
        if all_tasks is None or all_tasks.empty:
            st.info("Заявки закончились.")
            return

        tasks = self.filter_incomplete_tasks(all_tasks, {'fabric_is_done': False})

        # Создаем копию, чтобы избежать цепных изменений одной и той же таблицы
        tasks = tasks.copy()
        # Формируем колонку с информацией о длине бочины, вычисляеммой динамически. Её не требуется сохранять
        tasks.loc[:, 'side'] = tasks['size'].apply(side_eval, args=(str(tasks['side_fabric']),))

        # Формируем порядок показа полей от словаря конфигурации
        columns_order = list(self.cutting_columns_config)
        return st.data_editor(tasks[columns_order],
                              column_config=self.cutting_columns_config,
                              hide_index=False,
                              height=750)

    def cutting_table(self):
        submit = st.button(label='Подтвердить')

        edited_df = self.cutting_frame()

        if not submit or edited_df is None:
            return

        self.update_tasks(edited_df, 'fabric_is_done')
        st.rerun()


Page = CuttingPage(page_name='Нарезка',
                   icon="✂️")

col_table, col_info = st.columns([4, 1])

with col_table:
    Page.cutting_table()

with col_info:
    st.info('Вы можете сортировать заявки, нажимая на поля таблицы.', icon="ℹ️")
    st.info('Можно отметить много нарезанных заявок за раз и нажать кнопку "Подтвердить"', icon="ℹ️")
    st.warning("По умолчанию заявки располагаются сверху вниз в порядке приоритета. Самые срочные наверху.", icon="ℹ️")
