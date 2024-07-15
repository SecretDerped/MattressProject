from utils.app_core import ManufacturePage
from utils.tools import get_date_str


class PackingPage(ManufacturePage):
    def __init__(self, name, icon):
        super().__init__(name, icon)

    @staticmethod
    def inner_box_text(row):
        return (f"**Артикул:** {row['article']}  \n"
                f"**Размер**: {row['size']}  \n"
                f"**Тип доставки:** {row['delivery_type']}  \n"
                f"**Адрес:** {row['address']}  \n"
                f"**Клиент:** {row.get('client')}  \n"
                f"**Срок:** {get_date_str(row.get('deadline'))}  \n")


Page = PackingPage("Упаковка", "📦")

data = Page.load_tasks()
# Фильтруем наряды. Показываются те, что не пошиты,
# но на которые нарезали ткань и собрали основу.
# Не меняй "==" на "is" по стандарту PEP 8, иначе фильтр не будет работать.
packing_tasks = data[(data['packing_is_done'] == False) &
                     (data['sewing_is_done'] == True)]

Page.show_tasks_tiles(packing_tasks, 'packing_is_done', 3)

columns_to_display = ['deadline', 'article', 'address', 'delivery_type', 'region', 'comment']
