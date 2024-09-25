import streamlit as st

from utils.app_core import Page
from utils.tools import local_ip, config


class StartPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)

        self.site_port = config.get('site').get('site_port')
        self.streamlit_port = config.get('site').get('streamlit_port')

    def show_buttons(self):
        st_port = self.streamlit_port
        site_port = self.site_port

        # От выбранного порта зависит выбор приложения
       # st.link_button('**Бригадир**', f'http://{local_ip}:{st_port}/command', type="primary")

       # st.link_button('**Заявки**', f'http://{local_ip}:{site_port}', type="primary")

        st.link_button('**Заготовка**', f'http://{local_ip}:{st_port}/components')

        st.link_button('**Нарезка**', f'http://{local_ip}:{st_port}/cutting')

        st.link_button('**Упаковка**', f'http://{local_ip}:{st_port}/packing')

        st.link_button('**Сборка**', f'http://{local_ip}:{site_port}/gluing')

        st.link_button('**Швейный стол**', f'http://{local_ip}:{site_port}/sewing')


Page = StartPage("Начальная страница", "🛠️")

Page.header()
st.info("С этой страницы можно открыть любой экран.")

st.divider()

Page.show_buttons()
