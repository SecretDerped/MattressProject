import time

import streamlit as st
from utils import icon
from utils.tools import get_size_int, side_eval
import pandas as pd


def load_data(file_path):
    data = pd.read_csv(file_path)
    return data


# Сохранение данных в CSV-файл
def save_data(data, file_path):
    data.to_csv(file_path, index=False)


@st.experimental_fragment(run_every="2s")
def show_cutting_tasks():
    # Загрузка данных
    data = load_data('cash/cash.csv')

    # Отображение задач, где fabric_is_done == False
    tasks_todo = data[data['fabric_is_done'] == False]

    # Отображение каждой задачи и кнопки для изменения статуса
    for idx, row in tasks_todo.iterrows():
        size = get_size_int(row['size'])
        side = side_eval(size, row['fabric'])

        st.write(f"**Артикул:** {row['article']}  \n"
                 f"**Размер:** {row['size']}  \n"
                 f"**Тип:** {row['fabric']}, **Бочина:** {side}")

        if st.button('Выполнено', key=idx):
            # Изменение значения поля fabric_is_done на True
            data.at[idx, 'fabric_is_done'] = True
            # Сохранение обновленных данных
            save_data(data, 'cash/cash.csv')
            st.success('Статус обновлен успешно!')


icon.show_icon("✂️")
st.title('Нарезка ткани')
show_cutting_tasks()
