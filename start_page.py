import streamlit as st
from utils.app_core import Page
from utils.tools import local_ip, config


class StartPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)

        self.flask_port = config.get('site').get('flask_port')
        self.streamlit_port = config.get('site').get('streamlit_port')

    def show_buttons(self):
        st_port = self.streamlit_port
        fl_port = self.flask_port

        st.link_button('**Бригадир**', f'http://{local_ip}:{st_port}/Командный_экран', type="primary")

        st.link_button('**Заявки**', f'https://youtube.com', type="primary")

        st.link_button('**Заготовка**', f'http://{local_ip}:{st_port}/Заготовка_материалов')

        st.link_button('**Нарезка**', f'http://{local_ip}:{st_port}/Нарезка_ткани')

        st.link_button('**Упаковка**', f'http://{local_ip}:{st_port}/Упаковка')

        st.link_button('**Сборка**', f'http://{local_ip}:{fl_port}]/gluing')

        st.link_button('**Швейный стол**', f'http://{local_ip}:{fl_port}/sewing')


Page = StartPage("Начальная страница", "🛠️")

Page.header()
st.info("С этой страницы можно открыть любой экран.")

st.divider()

Page.show_buttons()
