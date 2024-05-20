import streamlit as st
from utils import icon, tools
from utils.tools import get_cash_rows_without

cash_file = tools.config.get('site').get('cash_filepath')

columns_to_display = ['deadline', 'article', 'size', 'attributes', 'comment', 'photo']

icon.show_icon("🧱")


@st.experimental_fragment(run_every="5s")
def show_packing_tasks():
    # Загрузка данных
    data = get_cash_rows_without('gluing_is_done')
    st.dataframe(data[columns_to_display],
                 column_config={'deadline': st.column_config.DateColumn("Дата", format="DD.MM"),
                                'article': st.column_config.TextColumn("Артикул"),
                                'size': st.column_config.TextColumn("Размер"),
                                'photo': st.column_config.ImageColumn("Фото"),
                                'attributes': st.column_config.TextColumn("Состав"),
                                'comment': st.column_config.TextColumn("Комментарий")}
                 )

show_packing_tasks()
