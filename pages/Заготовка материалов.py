import streamlit as st
from utils import tools
from utils.tools import read_file

page_name = 'Заготовка материалов'
page_icon = "🧱"
cash_file = tools.config.get('site').get('cash_filepath')
st.set_page_config(page_title=page_name,
                   page_icon=page_icon,
                   layout="wide")


@st.experimental_fragment(run_every="1s")
def show_materials_tasks(columns_to_display: list[str]):
    data = read_file(cash_file)
    data_df = data[(data['sewing_is_done'] == False) &
                   (data['gluing_is_done'] == False) &
                   (data['packing_is_done'] == False)]
    data_df = data_df[data_df['comment'] != '']
    tasks = data_df.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                ascending=[False, True, True, False])
    st.dataframe(tasks[columns_to_display],
                 column_config={'deadline': st.column_config.DateColumn("Дата", format="DD.MM"),
                                'article': st.column_config.TextColumn("Артикул"),
                                'size': st.column_config.TextColumn("Размер"),
                                'photo': st.column_config.ImageColumn("Фото"),
                                'attributes': st.column_config.TextColumn("Состав", width='large'),
                                'comment': st.column_config.TextColumn("Комментарий", width='large')}
                 )

################################################ Page ###################################################


half_screen_1, half_screen_2 = st.columns(2)
with half_screen_1:
    st.title(f'{page_icon} {page_name}')
with half_screen_2:
    st.info('Вы можете сортировать наряды, нажимая на поля таблицы. '
            'Заявка исчезнет, когда для неё соберут основу матраса. ')

columns = ['deadline', 'article', 'size', 'attributes', 'comment', 'photo']
show_materials_tasks(columns)
