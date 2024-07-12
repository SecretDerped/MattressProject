from utils.app_core import ManufacturePage
from utils.tools import get_date_str


class SewingPage(ManufacturePage):
    def __init__(self, name, icon):
        super().__init__(name, icon)

    @staticmethod
    def inner_box_text(row):
        return (f"**Артикул:** {row.get('article')}  \n"
                f"**Ткань (верх/низ)**: {row.get('base_fabric')}  \n"
                f"**Ткань (бочина)**: {row.get('base_fabric')}  \n"
                f"**Срок**: {get_date_str(row.get('deadline'))}  \n")


Page = SewingPage("Швейный стол", "🧵")

data = Page.load_tasks()
# Фильтруем наряды. Показываются те, что не пошиты,
# но на которые нарезали ткань и собрали основу.
# Не меняй "==" на "is" по стандарту PEP 8, иначе фильтр не будет работать.
sewing_tasks = data[(data['sewing_is_done'] == False) &
                    (data['gluing_is_done'] == True) &
                    (data['fabric_is_done'] == True) &
                    (data['packing_is_done'] == False)]

Page.show_tasks_tiles(sewing_tasks, 'sewing_is_done', 4)
