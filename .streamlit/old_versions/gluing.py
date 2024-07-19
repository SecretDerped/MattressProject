from utils.app_core import ManufacturePage
from utils.tools import get_date_str


class GluingPage(ManufacturePage):
    def __init__(self, name, icon):
        super().__init__(name, icon)

    @staticmethod
    def inner_box_text(row):
        return (f"**Артикул:** {row['article']}  \n"
                f"**Состав:** {row['attributes']}  \n"
                f"**Размер:** {row['size']}  \n"
                f"**Срок:** {get_date_str(row.get('deadline'))}  \n")


Page = GluingPage("Сборка основы", "🔨")

data = Page.load_tasks()
# Фильтруем наряды. Показываются те, что не пошиты,
# но на которые нарезали ткань и собрали основу.
# Не меняй "==" на "is" по стандарту PEP 8, иначе фильтр не будет работать.
packing_tasks = data[(data['gluing_is_done'] == False) &
                     (data['sewing_is_done'] == False) &
                     (data['packing_is_done'] == False)]

Page.show_tasks_tiles(packing_tasks, 'gluing_is_done', 2)

#columns_to_display = ['deadline', 'article', 'size', 'attributes', 'comment', 'photo']