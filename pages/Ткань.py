import streamlit as st
from utils import icon
from utils.tools import get_size_int, side_eval, config, read_file, save_to_file

cash_file = config.get('site').get('cash_filepath')

st.set_page_config(page_title="Нарезка ткани",
                   page_icon="✂️",
                   layout="wide")

# TODO:
@st.experimental_fragment(run_every="5s")
def show_cutting_tasks():
    # Загрузка данных
    data = read_file(cash_file)
    tasks_todo = data[data['fabric_is_done'] == False]

    sorted_df = tasks_todo.sort_values(by=['high_priority', 'deadline'], ascending=[False, True])
    columns_to_display = ['fabric', 'size', 'article', 'deadline']

    #st.table(sorted_df[columns_to_display])

    tasks_quantity = len(sorted_df)
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

    num_columns = 4

    # Группировка данных по 4 записи в строке
    for i in range(0, len(sorted_df), num_columns):
        row_data = sorted_df.iloc[i:i + num_columns]
        row_container = st.columns(num_columns)

        for j in range(num_columns):
            if j >= len(row_data):
                break
            with row_container[j]:
                st.write(str(j))
                st.write(f"Fabric: {row_data.iloc[j]['fabric']}")
                st.write(f"Deadline: {row_data.iloc[j]['deadline']}")
                st.write(f"High Priority: {row_data.iloc[j]['high_priority']}")
                
                """if st.button("Mark as Done", key=j):
                    sorted_df.at[row_data.index[j], 'fabric_is_done'] = True"""


st.title('✂️ Нарезка ткани')
show_cutting_tasks()
