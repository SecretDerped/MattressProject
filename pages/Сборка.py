import streamlit as st
from utils import icon, tools

cash_file = tools.config.get('site').get('cash_filepath')

columns_to_display = ['deadline', 'article', 'size', 'attributes', 'comment', 'photo']

icon.show_icon("🔨")


@st.experimental_fragment(run_every="5s")
def show_gluing_tasks():
    # Загрузка данных
    data = tools.read_file(cash_file)
    tasks_todo = data[data['gluing_is_done'] == False]

    sorted_df = tasks_todo.sort_values(by=['high_priority', 'deadline'], ascending=[False, True])

    st.dataframe(sorted_df[columns_to_display],
                 column_config={'deadline': st.column_config.DateColumn("Дата", format="DD.MM"),
                                'article': st.column_config.TextColumn("Артикул"),
                                'size': st.column_config.TextColumn("Размер"),
                                'photo': st.column_config.ImageColumn("Фото"),
                                'attributes': st.column_config.TextColumn("Состав"),
                                'comment': st.column_config.TextColumn("Комментарий")}
                 )


show_gluing_tasks()
