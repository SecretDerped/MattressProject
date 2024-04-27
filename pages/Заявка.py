import streamlit as st
from utils import icon


data = [{"position": 'Выбрать...', "quantity": 0, "commentary": None}]

# TODO: Внедрить постгрес. Данные будут дотягиваться из SBISWebApp.get_articles каждые 5 мин.
position_items = ['Кокос',
                  'Трикотаж',
                  'Уникальный матрас']

position_config = st.column_config.SelectboxColumn(
                "Позиция",
                options=position_items,
                width="medium"
            )

quantity_params = st.column_config.NumberColumn(
                "",
                min_value=1,
                max_value=999,
                step=1,
                default=1,
            )


icon.show_icon("📜")
st.title("Новая заявка")

col1, col2, col3 = st.columns(3)


with col1:
    new_task = st.data_editor(
        data=data,
        column_config={
            "position": position_config,
            "quantity": quantity_params,
            "commentary": "Комментарий"
        },
        num_rows="dynamic",
        disabled=["command"],
        hide_index=True,
    )
    print(new_task)

with col2:

    st.text_area('Комментарий ко всем')

    st.file_uploader(label='Прикрепить фото', type=('png', 'jpeg'))


with col3:

    col4, col5 = st.columns(2)

    with col4:
        st.date_input('Срок')
    with col5:
        st.number_input('Предоплата')

    delivery_type = st.radio('Тип доставки', ['📍 Самовывоз', '🏡 Город', '🗺️ Край', '🌎 Регионы'])

    match delivery_type:

        case '🏡 Город' | '🗺️ Край':
            st.text_input('Введите адрес')

        case '🌎 Регионы':
            st.selectbox('Выберите', ['Ставропольский край',
                                      'Ростовская область',
                                      'Северный Кавказ',
                                      "Хребты безумия"])
            st.text_input('Введите адрес')
