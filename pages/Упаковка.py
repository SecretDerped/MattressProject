import streamlit as st
from utils import icon
from utils.tools import read_file, config, save_to_file, get_cash_rows_without, get_date_str

cash_file = config.get('site').get('cash_filepath')
st.set_page_config(page_title="Упаковка",
                   page_icon="📦",
                   layout="wide")

columns_to_display = ['article', 'deadline', 'address', 'comment']
@st.experimental_fragment(run_every="5s")
def show_packing_tasks():
    # Загрузка данных
    tasks = get_cash_rows_without('packing_is_done')
    for index, row in tasks.iterrows():
        comment = row.get('comment', '')
        deadline = get_date_str(row['deadline'])

        text_color = 'red' if row['high_priority'] else 'gray'
        box_text = f""":{text_color}[**Артикул:** {row['article']}
                                     **Размер**: {row['size']}
                                     **Тип доставки**: {row['delivery_type']}
                                     **Адрес:** {row['address']}
                                     **Клиент:** {row.get('client')}
                                     **Срок**: {deadline}"""
        if row['comment']:
            box_text += f"**Комментарий**: {comment}  "

        box_text += ']'

    st.dataframe(sorted_df[columns_to_display],
                 column_config={'deadline': st.column_config.DateColumn("Дата", format="DD.MM"),
                                'article': st.column_config.TextColumn("Артикул"),
                                'attributes': st.column_config.TextColumn("Состав"),
                                'comment': st.column_config.TextColumn("Комментарий")})

'''    
        size = get_size_int(row['size'])
        side = side_eval(size, row['fabric'])
        deadline = get_date_str(row['deadline'])
        comment = row.get('comment', '')
        if count % num_columns == 0:
            row_container = st.columns(num_columns)
        box = row_container[count % num_columns].container(height=225, border=True)

        text_color = 'red' if row['high_priority'] else 'gray'

        box_text = f""":{text_color}[**Артикул:** {row['article']}  
                                     **Тип**: {row['fabric']}  
                                     **Размер:** {row['size']} ({side})  
                                     **Срок**: {deadline}  """
        if row['comment']:
            box_text += f"**Комментарий**: {comment}  "
        box_text += ']'

        with box:
            if box.button(":orange[**Выполнено**]", key=index):
                data.at[index, 'fabric_is_done'] = True
                save_to_file(data, cash_file)
                st.rerun()
            box.markdown(box_text)'''


icon.show_icon("📦")
show_packing_tasks()
