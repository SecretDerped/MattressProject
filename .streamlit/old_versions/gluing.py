from utils.app_core import ManufacturePage
from utils.tools import get_date_str, get_filtered_tasks


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
filter_conditions = [
        "gluing_is_done == False",
        "sewing_is_done == False",
        "packing_is_done == False"
    ]

packing_tasks = get_filtered_tasks(data, filter_conditions)

Page.show_tasks_tiles(packing_tasks, 'gluing_is_done', 2)
