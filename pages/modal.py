import streamlit as st
from streamlit_elements import elements, mui, event
def main():
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
        st.toast('Сканер активен!', icon='🚨')
        st.session_state.input_text = ""
        st.session_state.show_input = True

    with frame:
        # Обработчики горячих клавиш
        event.Hotkey("!", hotkey_pressed, bindInputs=True)
        if len(st.session_state.input_text) >= 6:
            save_input()
        scaner_button = mui.Button(onClick=button_pressed)
        with scaner_button:
            mui.icon.EmojiPeople()
            mui.Typography("Активировать сканер")

        # Поле ввода всегда на странице, но управляется состоянием
        input_visibility = 'visible' if st.session_state.show_input else 'hidden'
        input_style = {
            'backgroundColor': 'transparent',
            'color': 'transparent',
            'borderColor': 'transparent'
        } if not st.session_state.show_input else {}

        mui.TextField(
            label="Чтение карточки...",
            value=st.session_state.input_text,
            onChange=lambda e: setattr(st.session_state, 'input_text', e.target.value),
            autoFocus=True,
            style=input_style,
            inputProps={"style": {"visibility": input_visibility}}
        )

        if st.session_state.employee:
            mui.Typography(st.session_state.employee)

if __name__ == "__main__":
    main()