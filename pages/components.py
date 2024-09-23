import streamlit as st
from utils.app_core import ManufacturePage
from utils.tools import time_now, save_to_file


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

    def components_tasks(self, file):
        data = super().load_tasks(file)
        # Артикулы с нужными номерами отображаются, потому что в web_app есть функция, по умолчанию ставящая
        # всем артикулам в списке showed_articles из app_config значение components_is_done == False.
        # Остальным ставит True
        return data[(data['components_is_done'] == False) &
                    (data['sewing_is_done'] == False) &
                    (data['gluing_is_done'] == False) &
                    (data['packing_is_done'] == False)]

    @st.experimental_fragment(run_every="1s")
    def components_frame(self, file):
        tasks = self.components_tasks(file)
        return st.data_editor(tasks[self.columns_order],
                              column_config=self.components_columns_config,
                              hide_index=True)

    def components_table(self, file):
        tasks = super().load_tasks(file)
        # Создаем форму для обработки изменений в таблице
        with st.form(key=f'{file}_tasks_components_form'):
            inner_col_1, inner_col_2 = st.columns([4, 1])
            with inner_col_1:
                edited_tasks_df = self.components_frame(file)

            with inner_col_2:
                # Добавляем кнопку подтверждения
                submit_button = st.form_submit_button(label='Подтвердить')
                if submit_button:
                    employee = st.session_state.get(self.page_name)
                    if not employee:
                        st.warning("Сначала отметьте сотрудника.")
                    else:
                        for index, row in edited_tasks_df.iterrows():
                            if row['components_is_done']:
                                history_note = f'({time_now()}) {self.page_name} [ {employee} ] -> {self.done_button_text}; \n'
                                tasks.at[index, 'history'] += history_note
                                tasks.at[index, 'components_is_done'] = True
                        save_to_file(tasks, file)
                        st.rerun()

    def tables_row(self):
        for file in self.task_cash.iterdir():
            if file.is_file():
                # Флаг для показа/скрытия таблицы
                if not self.components_tasks(file).empty:
                    self.components_table(file)


Page = ComponentsPage(page_name='Заготовка',
                      icon="🧱",
                      columns_order=['components_is_done', 'article', 'size', 'attributes', 'comment',
                                     'photo'])

col_table, col_info = st.columns([4, 1])

with col_table:
    Page.tables_row()

with col_info:
    st.info('Вы можете сортировать наряды, нажимая на поля таблицы. ', icon="ℹ️")
    st.info('Можно отметить много готовых заявок за раз и нажать кнопку "Подтвердить"', icon="ℹ️")

