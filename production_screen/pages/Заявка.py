import streamlit as st
from utils import icon

icon.show_icon("📜")
st.title("Новая заявка")
st.checkbox('Check me out')
delivery_type = st.radio('Тип доставки', ['📍 Самовывоз', '🏡 Город', '🗺️ Край', '🌎 Регионы'])
match delivery_type:
    case '🌎 Регионы':
        st.selectbox('Выберите', ['Краснодарский край', 'Ставропольский край', 'Ростовская область', 'Северный Кавказ', "Хребты безумия"])
    case '🏡 Город' | '🗺️ Край':
        st.text_input('Введите адрес')

st.date_input('Срок')
st.number_input('Предоплата')
st.text_area('Комментарий')
st.file_uploader(label='Прикрепить фото', key='aaaaaaaaaaa')
