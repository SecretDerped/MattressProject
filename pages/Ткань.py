import streamlit as st
from utils import icon
from utils.tools import get_size_int, side_eval, config, read_file, save_to_file

cash_file = config.get('site').get('cash_filepath')


@st.experimental_fragment(run_every="5s")
def show_cutting_tasks():
    # Загрузка данных
    data = read_file(cash_file)
    tasks_todo = data[data['fabric_is_done'] == False]

    sorted_df = tasks_todo.sort_values(by=['high_priority', 'deadline'], ascending=[False, True])
    columns_to_display = ['fabric', 'size', 'article', 'deadline']

    # Вывод таблицы в Streamlit
    st.write("Таблица с сортировкой и группировкой")
    st.table(sorted_df[columns_to_display])

    # Отображение каждой задачи и кнопки для изменения статуса
    for idx, row in tasks_todo.iterrows():
        size = get_size_int(row['size'])
        side = side_eval(size, row['fabric'])
        left, right, buff, buff2, buff3 = st.columns(5)
        with left:
            st.write(f"**Артикул:** {row['article']}  \n"
                     f"**Размер:** {row['size']} ({side})  \n"
                     f"**Тип:** {row['fabric']}")
        with right:
            if st.button('Выполнено', key=idx):
                # Изменение значения поля fabric_is_done на True
                data.at[idx, 'fabric_is_done'] = True
                # Сохранение обновленных данных
                save_to_file(data, cash_file)
                st.rerun()


st.title('✂️ Нарезка ткани')
show_cutting_tasks()

#TODO: наладить экран нарезчика

num_columns = 5
num_rows = len(data) // num_columns + (len(data) % num_columns > 0)  # Вычисляем количество строк

columns = st.columns(num_columns)

for row in range(num_rows):
    for col in range(num_columns):
        index = row * num_columns + col
        if index >= len(data):
            break
        tile = columns[col].container(height=120)
        size = get_size_int(row['size'])
        side = side_eval(size, row['fabric'])
        left, right = st.columns(2)
        tile.title(str(data[index]))

