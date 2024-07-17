import streamlit as st
from utils.app_core import Page


class ComponentsPage(Page):
    def __init__(self, page_name, icon, columns_order):
        super().__init__(page_name, icon)
        self.columns_order = columns_order
        self.components_columns_config = {
            'deadline': st.column_config.DateColumn("Дата", format="DD.MM"),
            'article': st.column_config.TextColumn("Артикул"),
            'size': st.column_config.TextColumn("Размер"),
            'attributes': st.column_config.TextColumn("Состав", width='large'),
            'comment': st.column_config.TextColumn("Комментарий", width='large'),
            'photo': st.column_config.ImageColumn("Фото"),
        }

    @st.experimental_fragment(run_every="1s")
    def show_materials_tasks(self, tasks):
        st.dataframe(data=tasks[self.columns_order],
                     column_config=self.components_columns_config,
                     hide_index=True)

################################################ Page ###################################################


Page = ComponentsPage(page_name='Заготовка',
                      icon="🧱",
                      columns_order=['deadline', 'article', 'size', 'attributes', 'comment', 'photo'])

data = Page.load_tasks()

components_tasks = data[(data['sewing_is_done'] == False) &
                        (data['gluing_is_done'] == False) &
                        (data['packing_is_done'] == False) &
                        (data['comment'] != '')]

half_screen_1, half_screen_2 = st.columns([2, 1])
with half_screen_1:
    Page.header()
with half_screen_2:
    st.info('Вы можете сортировать наряды, нажимая на поля таблицы. '
            'Заявка исчезнет, когда для неё соберут основу матраса. ', icon="ℹ️")

Page.show_materials_tasks(components_tasks)
