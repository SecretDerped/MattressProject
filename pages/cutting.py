import streamlit as st

from utils.app_core import ManufacturePage
from utils.tools import config, side_eval, save_to_file, time_now


class CuttingPage(ManufacturePage):
    def __init__(self, page_name, icon, columns_order):
        super().__init__(page_name, icon)
        self.columns_order = columns_order
        self.cutting_columns_config = {
            'fabric_is_done': st.column_config.CheckboxColumn("Готово"),
            'base_fabric': st.column_config.TextColumn("Ткань (Верх / Низ)", disabled=True),
            'side_fabric': st.column_config.TextColumn("Ткань (Бочина)", disabled=True),
            'size': st.column_config.TextColumn("Размер", disabled=True),
            'side': st.column_config.TextColumn("Бочина", disabled=True),
            'article': st.column_config.TextColumn("Артикул", disabled=True),
            'deadline': st.column_config.DateColumn("Срок", format="DD.MM", disabled=True),
            'comment': st.column_config.TextColumn("Комментарий", disabled=True),
        }
        self.showed_articles = config['components']['showed_articles']

    def cutting_tasks(self, file):
        data = super().load_tasks(file)
        return data[(data['components_is_done'] == True) &
                    (data['fabric_is_done'] == False) &
                    (data['sewing_is_done'] == False) &
                    (data['packing_is_done'] == False)]

    @st.experimental_fragment(run_every="1s")
    def cutting_frame(self, file):
        tasks = self.cutting_tasks(file)
        # Вычисляемое поле размера бочины.
        tasks['side'] = tasks['size'].apply(side_eval, args=(str(tasks['side_fabric']),))
        return st.data_editor(tasks[self.columns_order],  # width=600, height=600,
                              column_config=self.cutting_columns_config,
                              hide_index=True)

    def cutting_table(self, file):
        tasks = super().load_tasks(file)
        # Создаем форму для обработки изменений в таблице
        with st.form(key=f'{file}_tasks_cutting_form'):
            inner_col_1, inner_col_2 = st.columns([4, 1])
            with inner_col_1:
                edited_tasks_df = self.cutting_frame(file)

            with inner_col_2:
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
                        save_to_file(tasks, file)
                        st.rerun()

    def tables_row(self):
        for file in self.task_cash.iterdir():
            if file.is_file():
                # Флаг для показа/скрытия таблицы
                if not self.cutting_tasks(file).empty:
                    self.cutting_table(file)


Page = CuttingPage(page_name='Нарезка',
                   icon="✂️",
                   columns_order=['fabric_is_done', 'base_fabric', 'side_fabric', 'size', 'side', 'article',
                                  'comment'])

col_table, col_info = st.columns([4, 1])

with col_table:
    Page.tables_row()

with col_info:
    st.info('Вы можете сортировать заявки, нажимая на поля таблицы. '
            'Попробуйте отсортировать по размеру!', icon="ℹ️")

    st.info('Можно отметить много нарезанных заявок за раз и нажать кнопку "Подтвердить"', icon="ℹ️")
