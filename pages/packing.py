from utils.app_core import ManufacturePage
from utils.tools import get_date_str
import streamlit as st


class PackingPage(ManufacturePage):
    def __init__(self, name, icon):
        super().__init__(name, icon)

    def packing_tasks(self):
        data = super().load_tasks()
        # Фильтруем наряды. Показываются те, что не пошиты,
        # но на которые нарезали ткань и собрали основу.
        # Не меняй "==" на "is" по стандарту PEP 8, иначе фильтр не будет работать.
        return data[(data['packing_is_done'] == False) &
                    (data['sewing_is_done'] == True)]

    @staticmethod
    def inner_box_text(row):
        return (f"**Артикул:** {row['article']}  \n"
                f"**Размер**: {row['size']}  \n"
                f"**Тип доставки:** {row['delivery_type']}  \n"
                f"**Адрес:** {row['address']}  \n"
                f"**Клиент:** {row.get('client')}  \n"
                f"**Срок:** {get_date_str(row.get('deadline'))}  \n")

    @st.experimental_fragment(run_every="1s")
    def packing_tiles(self):
        super().show_tasks_tiles(self.packing_tasks(), 'packing_is_done', 3)


Page = PackingPage("Упаковка", "📦")

Page.packing_tiles()
