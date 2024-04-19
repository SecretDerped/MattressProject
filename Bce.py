import streamlit as st
import sbis_manager
from production_screen.utils import icon
import sys
sys.path.append('sbis_manager.py')


st.set_page_config(page_title="Производственный терминал",
                   page_icon="🛠️",
                   layout="wide")

icon.show_icon("🏭")
st.title("Производственный терминал")
st.sidebar.write('Экраны')
tab1, tab2 = st.sidebar.tabs(["Все заявки", "Экран нарезки"])

tab1.write("Заявки на производство")
tab1.button('да')

tab2.write("Линия НАААрЕЕЕЗкИИИ")

LOGIN = 'ХарьковскийАМ'
PASSWORD = 'Retread-Undusted9-Catalyst-Unseated'
SALE_POINT_NAME = 'Кесиян Давид Арсенович, ИП'
PRICE_LIST_NAME = 'Тестовые матрацы'
sbis = sbis_manager.SBISWebApp(LOGIN, PASSWORD, SALE_POINT_NAME, PRICE_LIST_NAME)

print(sbis.get_articles())
