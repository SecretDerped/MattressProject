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
        self.showed_articles = [
            '000', '807', '808', '809', '901', '902', '903', '904', '905', '906', '907', '908', '909', '911', '912'
        ]

    def components_tasks(self):
        data = super().load_tasks()
        return data[(data['article'] in self.showed_articles) |
                    (data['components_is_done'] == False) &
                    (data['sewing_is_done'] == False) &
                    (data['gluing_is_done'] == False) &
                    (data['packing_is_done'] == False)]

    @st.experimental_fragment(run_every="1s")
    def components_table(self, tasks):
        st.dataframe(data=tasks[self.columns_order],
                     column_config=self.components_columns_config,
                     hide_index=True)


Page = ComponentsPage(page_name='Заготовка',
                      icon="🧱",
                      columns_order=['deadline', 'article', 'size', 'attributes', 'comment', 'photo'])

col_table, col_info = st.columns([2, 1])

with col_table:
    Page.header()

with col_info:
    st.info('Вы можете сортировать наряды, нажимая на поля таблицы. ', icon="ℹ️")

Page.show_materials_tasks(components_tasks)
