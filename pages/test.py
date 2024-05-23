from datetime import datetime
from typing import List, Dict

import streamlit as st
from utils import icon
from utils.tools import read_file, config, save_to_file, get_date_str

cash_file = config.get('site').get('cash_filepath')

st.set_page_config(page_title="Клейка", page_icon="🧵", layout="wide")


class GluingTaskManager:
    def __init__(self, cash: str, num_columns: int = 2):
        self.cash_file = cash
        self.num_columns = num_columns
        self.data = read_file(cash)
        self.tasks = self.load_gluing_tasks()

    def load_gluing_tasks(self) -> List[Dict]:
        """Загружает и сортирует задания на клейку."""
        data_df = self.data[self.data['gluing_is_done'] == False]
        return data_df.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                   ascending=[False, True, True, False]).to_dict('records')

    @staticmethod
    def generate_box_text(row: Dict) -> str:
        """Создаёт текст для контейнера задачи."""
        text_color = 'red' if row['high_priority'] else 'gray'
        deadline = get_date_str(row['deadline'])
        box_text = f""":{text_color}[**Арт.:** {row['article']} | **Размер:** {row['size']}   
        **Состав:** {row['attributes']}  
        **Срок:** {deadline}  
"""

        comment = row.get('comment', '')
        if comment:
            box_text += f"  **Комментарий**: {comment}  "
        box_text += ']'
        return box_text

    def mark_task_as_done(self, index: int):
        """Отмечает задачу как выполненную и сохраняет изменения."""
        self.data.at[index, 'gluing_is_done'] = True
        self.data.at[index, 'history'] += f' -> Основа собрана ({datetime.now().strftime("%H:%M")})'
        save_to_file(self.data, self.cash_file)
        st.rerun()

    def display_task(self, row: Dict, key: int):
        """Отображает одну задачу с соответствующими элементами управления."""
        box_text = self.generate_box_text(row)

        if row.get('photo'):
            col1, col2, col3, buff = st.columns([6, 4, 1, 1])
            col3.image(row['photo'], caption='Фото', width=70)
        else:
            col1, col2 = st.columns([3, 2])

        with col1:
            col1.markdown(box_text)
        with col2:
            st.header('')
            if col2.button(":orange[**Выполнено**]", key=key):
                self.mark_task_as_done(key)

    def show_tasks(self):
        """Отображает задачи на клейку в виде сетки контейнеров."""
        row_container = st.columns(self.num_columns)

        for count, row in enumerate(self.tasks):
            if count % self.num_columns == 0:
                row_container = st.columns(self.num_columns)
            with row_container[count % self.num_columns].container(height=135, border=True):
                self.display_task(row, key=count)


icon.show_icon("🧵")

# Создаём экземпляр класса и отображаем задачи
task_manager = GluingTaskManager(cash=cash_file, num_columns=2)
task_manager.show_tasks()
