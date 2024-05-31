import streamlit as st
from utils.tools import config, redact_table, show_table, clear_cash
import datetime

site_conf = config.get('site')

task_cash = site_conf.get('cash_filepath')
employees_cash = site_conf.get('employees_cash_filepath')

delivery_type = site_conf.get('delivery_types')
regions = site_conf.get('regions')
# TODO: внедрить типаж тканей и название
fabrics = list(config.get('fabric_corrections'))

st.set_page_config(page_title="Производственный терминал",
                   page_icon="🛠️",
                   layout="wide")

TASK_STATE = 'task_dataframe'
EMPLOYEE_STATE = 'employee_dataframe'
SHOW_TABLE = 'show_table'

employee_columns = {
    "is_on_shift": st.column_config.CheckboxColumn("На смене", default=False),
    "name": st.column_config.TextColumn("Имя / Фамилия"),
    "position": st.column_config.TextColumn("Роли")
}

editors_columns = {
    "high_priority": st.column_config.CheckboxColumn("Приоритет", default=False),
    "deadline": st.column_config.DateColumn("Срок",
                                            min_value=datetime.date(2020, 1, 1),
                                            max_value=datetime.date(2199, 12, 31),
                                            format="DD.MM.YYYY",
                                            step=1,
                                            default=datetime.date.today()),
    "article": "Артикул",
    "size": "Размер",
    "fabric": st.column_config.SelectboxColumn("Тип ткани",
                                               options=fabrics,
                                               default=fabrics[0],
                                               required=True),
    "photo": st.column_config.ImageColumn("Фото", help="Кликните, чтобы развернуть"),
    "comment": st.column_config.TextColumn("Комментарий",
                                           default='',
                                           width='small'),
    "attributes": st.column_config.TextColumn("Состав начинки",
                                              default='',
                                              width='medium'),
    "fabric_is_done": st.column_config.CheckboxColumn("Нарезано",
                                                      default=False),
    "gluing_is_done": st.column_config.CheckboxColumn("Собран",
                                                      default=False),
    "sewing_is_done": st.column_config.CheckboxColumn("Пошит",
                                                      default=False),
    "packing_is_done": st.column_config.CheckboxColumn("Упакован",
                                                       default=False),
    "history": st.column_config.TextColumn("Действия",
                                           width='small',
                                           disabled=True),
    "client": st.column_config.TextColumn("Заказчик",
                                          default='',
                                          width='medium'),
    "delivery_type": st.column_config.SelectboxColumn("Тип доставки",
                                                      options=delivery_type,
                                                      default=delivery_type[0],
                                                      required=True),
    "address": st.column_config.TextColumn("Адрес",
                                           default='Наш склад',
                                           width='large'),
    "region": st.column_config.SelectboxColumn("Регион",
                                               width='medium',
                                               options=regions,
                                               default=regions[0],
                                               required=True),
    "created": st.column_config.DatetimeColumn("Создано",
                                               format="D.MM.YYYY | HH:MM",
                                               # Этот параметр не позволяет создать
                                               # запись прямо в таблице, минуя окно формирования заявок.
                                               default=datetime.datetime.now(),
                                               disabled=True),
}

tab1, tab2 = st.tabs(['Наряды', 'Сотрудники'])

with tab1:
    if SHOW_TABLE not in st.session_state:
        st.session_state[SHOW_TABLE] = False

    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("🏭 Все наряды")
        # Кнопка для отображения/скрытия таблицы с изменением текста
        button_text = '**Перейти в режим редактирования**' if not st.session_state[
            SHOW_TABLE] else ":red[**Сохранить и вернуть режим просмотра**]"
        if st.button(button_text):
            clear_cash(TASK_STATE)  # Очистить данные, если таблица скрывается
            st.session_state[SHOW_TABLE] = not st.session_state[SHOW_TABLE]
            st.rerun()

    with col2:
        st.write(' ')
        st.info('''Чтобы поправить любой наряд, включите режим редактирования.
        Он обладает высшим приоритетом - пока активен режим редактирования,
        изменения других рабочих не сохраняются. **Не забывайте сохранять таблицу!**''', icon="ℹ️")

    # Отображение таблицы в зависимости от состояния
    if st.session_state[SHOW_TABLE]:
        redact_table(editors_columns, task_cash, TASK_STATE)
    if not st.session_state[SHOW_TABLE]:
        show_table(editors_columns, task_cash)

with tab2:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.title("👷 Сотрудники")
    with col2:
        st.write(' ')
        st.info('Выставляйте рабочих на смену. Они будут отображаться при выборе ответственного на нужном экране. '
                'В поле "Роли" пропишите рабочее место сотруднику.'
                'Можно вписать несколько. Доступно: сборка основы, нарезка ткани, швейный стол, упаковка', icon="ℹ️")

    redact_table(employee_columns, employees_cash, EMPLOYEE_STATE, True)
