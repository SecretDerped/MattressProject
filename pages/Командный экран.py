import streamlit as st

from utils.app_core import Page
from utils.tools import config, show_table, clear_cash, read_file, create_cashfile_if_empty, cashing, \
    get_cash, save_to_file, barcode_link
import datetime


class CommandPage(Page):
    def __init__(self, name, icon):
        super().__init__(name, icon)
        self.task_cash = self.cash
        self.employees_cash = config.get('site').get('employees_cash_filepath')
        self.EMPLOYEE_STATE = 'employee_dataframe'
        self.TASK_STATE = 'task_dataframe'
        self.SHOW_TABLE = 'show_table'

        self.employee_columns_config = {
            "is_on_shift": st.column_config.CheckboxColumn("На смене", default=False),
            "name": st.column_config.TextColumn("Имя / Фамилия"),
            "position": st.column_config.TextColumn("Роли", width='medium'),
            "barcode": st.column_config.LinkColumn("Штрих-код", display_text="Открыть"),
        }

        self.tasks_columns_config = {
            "high_priority": st.column_config.CheckboxColumn("Приоритет", default=False),
            "deadline": st.column_config.DateColumn("Срок",
                                                    min_value=datetime.date(2000, 1, 1),
                                                    max_value=datetime.date(2999, 12, 31),
                                                    format="DD.MM.YYYY",
                                                    step=1,
                                                    default=datetime.date.today()),
            "article": "Артикул",
            "size": "Размер",
            "base_fabric": st.column_config.TextColumn("Ткань (Верх / Низ)",
                                                       default='Текстиль'),
            "side_fabric": st.column_config.TextColumn("Ткань (Бок)",
                                                       default='Текстиль'),
            "photo": st.column_config.ImageColumn("Фото", help="Кликните, чтобы развернуть"),
            "comment": st.column_config.TextColumn("Комментарий",
                                                   default='',
                                                   width='small'),
            "springs": st.column_config.TextColumn("Пружины",
                                                   default=''),
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
                                                              options=config.get('site').get('delivery_types'),
                                                              default=config.get('site').get('delivery_types')[0],
                                                              required=True),
            "address": st.column_config.TextColumn("Адрес",
                                                   default='Наш склад',
                                                   width='large'),
            "region": st.column_config.SelectboxColumn("Регион",
                                                       width='medium',
                                                       options=config.get('site').get('regions'),
                                                       default=config.get('site').get('regions')[0],
                                                       required=True),
            "created": st.column_config.DatetimeColumn("Создано",
                                                       format="D.MM.YYYY | HH:MM",
                                                       disabled=True),
        }

    def show_employees_table(self):
        # Создаёт таблицу из настроек колонн, если её нет
        create_cashfile_if_empty(self.employee_columns_config, self.employees_cash)

        if self.EMPLOYEE_STATE not in st.session_state:
            dataframe = read_file(self.employees_cash)
            dataframe['barcode'] = dataframe['_index'].apply(barcode_link)
            cashing(dataframe, self.EMPLOYEE_STATE)

        edited_df = get_cash(self.EMPLOYEE_STATE)
        editor = st.data_editor(
            edited_df,
            column_config=self.employee_columns_config,
            hide_index=False,
            num_rows="dynamic",
            on_change=cashing, args=(edited_df, self.EMPLOYEE_STATE),
        )
        save_to_file(editor, self.employees_cash)

    def show_tasks_table(self, can_add_lines: bool = False):
        """База данных в этом проекте представляет собой файл pkl с датафреймом библиотеки pandas.
        Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
        а кэш делается из session_state - текущего состояния таблицы. Каждое изменение таблицы
        провоцируют on_change методы, а потом обновление всей страницы. Поэтому система
        такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
        Как только какое-то поле было изменено, то изменения записываются в кэш,
        потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями
        сохраняется в базу."""

        # Создаётся таблица из настроек колонн, если её нет
        create_cashfile_if_empty(self.tasks_columns_config, self.task_cash)

        # Со страницы создания заявки возвращаются только строки, поэтому тут
        # некоторые столбцы преобразуются в типы, читаемые для pandas.
        dataframe_columns_types = {'deadline': "datetime64[ns]",
                                   'created': "datetime64[ns]"}
        if self.TASK_STATE not in st.session_state:
            dataframe = read_file(self.task_cash)
            # Проверка наличия нужных колонок в датафрейме
            for col in dataframe_columns_types.keys():
                if col in dataframe.columns:
                    dataframe[col] = dataframe[col].astype(dataframe_columns_types[col])
            cashing(dataframe, self.TASK_STATE)

        edited_df = get_cash(self.TASK_STATE)
        editor = st.data_editor(
            edited_df,
            column_config=self.tasks_columns_config,
            hide_index=True,
            num_rows="fixed",
            on_change=cashing, args=(edited_df, self.TASK_STATE),
            height=420
        )
        save_to_file(editor, self.task_cash)
################################################ Page ####################################################

Command = CommandPage(name='Производственный терминал',
                      icon='🛠️')

tasks_tab, employee_tab = st.tabs(['Наряды', 'Сотрудники'])

with tasks_tab:
    # В SHOW_TABLE хранится название для переменной session_state,
    # в которой булево значение "Показывать/Не показывать таблицу".
    # Тут происходит инициализация переменной. По умолчанию show_table = False
    if Command.SHOW_TABLE not in st.session_state:
        st.session_state[Command.SHOW_TABLE] = False

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
        redact_table(tasks_columns, task_cash, TASK_STATE)
    if not st.session_state[SHOW_TABLE]:
        show_table(tasks_columns, task_cash)

# TODO: совместный табель - история смен сотрудников
with employee_tab:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.title("👷 Сотрудники")
        redact_table(employee_columns, employees_cash, EMPLOYEE_STATE, True)
    with col2:
        st.write(' ')
        st.info('Выставляйте рабочих на смену. Они будут активны при выборе ответственного на нужном экране. ',
                icon="ℹ️")
        st.info('В поле "Роли" пропишите рабочее место сотруднику. Можно вписать несколько.'
                'Доступно: сборка основы, нарезка ткани, швейный стол, упаковка',
                icon="ℹ️")
        st.info('Задайте сотрудникам уникальные коды. Они должны состоять из 3-х символов:'
                'латинские буквы и цифры. Например: LA7, 123, ABC, t9L, kek',
                icon="ℹ️")
