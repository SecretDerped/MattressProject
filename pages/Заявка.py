import streamlit as st
from utils import icon

st.set_page_config(page_title="Заявка",
                   page_icon="📜",
                   layout="wide")


data = [{"position": None, "size": None, "fabric": None, "quantity": 1, "commentary": None, }]

article_items = ["905", "Беспружинный матрас", 'Уникальный матрас']
article_config = st.column_config.SelectboxColumn(
    "Артикул",
    options=article_items,
    width="medium"
)

size_params = st.column_config.TextColumn(
    "Размер"
)

fabric_items = ["Жаккард", "Трикотаж"]
fabric_params = st.column_config.SelectboxColumn(
    "Ткань",
    options=fabric_items,
    default=fabric_items[0]
)

quantity_params = st.column_config.NumberColumn(
    "Кол-во",
    min_value=1,
    max_value=999,
    step=1,
    default=1,
)

icon.show_icon("📜")
st.title("Новая заявка")

half_screen_1, half_screen_2 = st.columns(2)
with half_screen_1:
    new_task = st.data_editor(
        data=data,
        column_config={
            "position": article_config,
            "size": size_params,
            "fabric": fabric_params,
            "quantity": quantity_params,
            "commentary": "Комментарий",
        },
        num_rows="dynamic",
        disabled=["command"],
        hide_index=True,
    )
    print(new_task)

    st.text_area('Комментарий ко всему заказу')

    st.file_uploader(label='Прикрепить фото', type=('png', 'jpeg'))

with half_screen_2:
    quarter_screen_1, quarter_screen_2 = st.columns(2)

    with quarter_screen_1:
        st.date_input('Срок')
    with quarter_screen_2:
        st.number_input('Предоплата')

    delivery_type = st.radio('Тип доставки', ['📍 Самовывоз', '🏡 Город', '🗺️ Краснодарский край', '🌎 Другие регионы'])

    match delivery_type:

        case '🏡 Город' | '🗺️ Краснодарский край':
            st.text_input('Введите адрес')

        case '🌎 Другие регионы':
            st.selectbox('Выберите регион', ['Ставропольский край',
                                             'Ростовская область',
                                             'Северный Кавказ',
                                             "Хребты безумия"])
            st.text_input('Введите адрес')
