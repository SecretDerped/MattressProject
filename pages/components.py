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
        self.showed_articles = [
            '0', '000', '807', '808', '809', '901', '902', '903', '904', '905', '906', '907', '908', '909', '911', '912'
        ]

    def components_tasks(self):
        data = super().load_tasks()
        # Артикулы с нужными номерами отображаются, потому что в web_app есть функция, по умолчанию ставящая
        # всем артикулам в списке showed_articles из app_config значение components_is_done == False.
        # Остальным ставит True
        return data[(data['components_is_done'] == False) &
                    (data['sewing_is_done'] == False) &
                    (data['gluing_is_done'] == False) &
                    (data['packing_is_done'] == False)]

    @st.experimental_fragment(run_every="1s")
    def components_frame(self):
        tasks = self.components_tasks()
        return st.data_editor(tasks[self.columns_order],
                              column_config=self.components_columns_config,
                              hide_index=True)

    def components_table(self):
        tasks = super().load_tasks()
        # Создаем форму для обработки изменений в таблице
        with st.form(key='tasks_components_form'):
            inner_col_1, inner_col_2 = st.columns([4, 1])
            with inner_col_1:
                edited_tasks_df = self.components_frame()

            with inner_col_2:
                st.write('Можно отметить много готовых заявок за раз и нажать кнопку:')
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
                        save_to_file(tasks, self.task_cash)
                        st.rerun()


Page = ComponentsPage(page_name='Заготовка',
                      icon="🧱",
                      columns_order=['components_is_done', 'deadline', 'article', 'size', 'attributes', 'comment',
                                     'photo'])

col_table, col_info = st.columns([4, 1])

with col_table:
    Page.components_table()

with col_info:
    st.info('Вы можете сортировать наряды, нажимая на поля таблицы. ', icon="ℹ️")

