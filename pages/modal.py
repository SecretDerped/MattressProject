import streamlit as st
from streamlit_elements import elements, mui, event

frame = elements("callbacks_hotkey")

st.info('Убедитесь, что сканер включён.')

# Инициализация состояния
if 'show_input' not in st.session_state:
    st.session_state['show_input'] = False

if 'input_text' not in st.session_state:
    st.session_state['input_text'] = ""

if 'employee' not in st.session_state:
    st.session_state['employee'] = ""

# Функция для обработки горячей клавиши "!"
def hotkey_pressed():
    st.session_state.input_text = ""
    st.session_state.show_input = True

# Функция для сохранения введенного текста по горячей клавише "*"
def save_input():
    if st.session_state.input_text:
        st.session_state.employee = st.session_state.input_text
        st.session_state.show_input = False

# Кнопка для включения сканера
def button_pressed():
    st.toast('Сканер включён!', icon='🚨')

with frame:
    # Обработчики горячих клавиш
    event.Hotkey("!", hotkey_pressed, bindInputs=True)
    event.Hotkey("*", save_input, bindInputs=True)

    scaner_button = mui.Button(onClick=button_pressed)
    with scaner_button:
        mui.icon.EmojiPeople()
        mui.Typography("Включить сканер")

    # Поле ввода всегда на странице, но управляется состоянием
    if st.session_state.show_input:
        mui.TextField(
            label="Чтение карточки...",
            value=st.session_state.input_text,
            onChange=lambda e: setattr(st.session_state, 'input_text', e.target.value),
            autoFocus=True,
        )

    if st.session_state.employee:
        mui.Typography(st.session_state.employee)
