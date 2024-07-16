import datetime

import pandas
import streamlit as st

from utils.tools import config, read_file, side_eval, get_date_str, save_to_file, time_now, create_cashfile_if_empty


class Page:
    def __init__(self, page_name, icon):
        self.page_name = page_name
        self.icon = icon

        self.task_cash = config.get('site').get('tasks_cash_filepath')
        self.employees_cash = config.get('site').get('employees_cash_filepath')

        self.employee_columns_config = {
            "is_on_shift": st.column_config.CheckboxColumn("На смене", default=False),
            "name": st.column_config.TextColumn("Имя / Фамилия", default=''),
            "position": st.column_config.TextColumn("Роли", width='medium', default=''),
            "barcode": st.column_config.LinkColumn("Штрих-код", display_text="Открыть", disabled=True),
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

        st.set_page_config(page_title=self.page_name,
                           page_icon=self.icon,
                           layout="wide")

    def load_tasks(self):
        # Создаётся таблица из настроек колонн, если её нет
        create_cashfile_if_empty(self.tasks_columns_config, self.task_cash)
        data = read_file(self.task_cash)
        return data.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                ascending=[False, True, True, False])


class ManufacturePage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)
        self.reserve_button_text = 'Взять'
        self.done_button_text = 'Готово'
        self.header()

    def header(self):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f'{self.icon} {self.page_name}')
        with col2:
            self.employee_choose()

    def employees_on_shift(self, searching_position: str) -> list:
        """Принимает строку для фильтрации по роли сотрудника (position).
        Читает .pkl из employees_cash_filepath, преобразует в датафрейм.
        Фильтрует записи, где значение в "is_on_shift" стоит True,
        а в колонке "position" есть подстрока из аргумента функции (независимо от регистра).
        Возвращает [список имен сотрудников на смене по искомой роли]"""
        create_cashfile_if_empty(self.employee_columns_config, self.employees_cash)
        dataframe = read_file(self.employees_cash)
        if 'is_on_shift' not in dataframe.columns or 'position' not in dataframe.columns:
            raise ValueError("В датафрейме сотрудников должны быть колонки 'is_on_shift' и 'position'")

        filtered_df = dataframe[(dataframe['is_on_shift'] == True) & (
            dataframe['position'].str.contains(searching_position, case=False, na=False))]

        return filtered_df['name'].tolist()

    @st.experimental_fragment(run_every="4s")
    def employee_choose(self):
        """Виджет для выбора активного сотрудника для рабочего места.
        Рабочее место - строка в качестве аргумента.
        Показывает выпадающий список из сотрудников, находящихся на смене.
        При выборе сотрудника в session_state сохраняется строка с именем сотрудника под ключом с названием должности.
        Пример: st.session_state['швейный стол'] == 'Полиграф Полиграфович'"""

        def save_employee(position):
            """Метод для работы эффекта on_change виджета из employee_choose.
            Без него выбираемый сотрудник корректно не записывается в session_state."""
            st.session_state[position] = st.session_state[position]

        st.selectbox('Ответственный',
                     options=self.employees_on_shift(self.page_name),
                     placeholder="Выберите сотрудника",
                     index=None,
                     key=self.page_name,
                     on_change=save_employee, args=(self.page_name,))

    # Функция для проверки состояния кнопки бронирования
    def reserve_check(self, index):
        return st.session_state.get(f'{self.page_name}_reserved_{index}', False)

    # Функция для установки состояния кнопки бронирования
    def set_reserved_state(self, index, state):
        st.session_state[f'{self.page_name}_reserved_{index}'] = state

    # Функция для получения имени пользователя, который забронировал
    def get_reserver(self, index):
        return st.session_state.get(f'{self.page_name}_reserver_{index}', '')

    # Функция для установки имени пользователя, который забронировал
    def set_reserver(self, index, name):
        st.session_state[f'{self.page_name}_reserver_{index}'] = name

    @staticmethod
    def inner_box_text(row):
        """Метод, выдающий текст внутри бокса. Для каждой страницы с плитками заявок можно переопределять этот метод."""
        return (f"**Артикул:** {row.get('article')}  \n"
                f"**Ткань**: {row.get('base_fabric')}  \n"
                f"**Тип доставки**: {row.get('delivery_type')}  \n"
                f"**Адрес:** {row.get('address')}  \n"
                f"**Клиент:** {row.get('client')}  \n"
                f"**Верх/Низ**: {row.get('base_fabric')}  \n"
                f"**Бочина**: {row.get('side_fabric')}  \n"
                f"**Состав:** {row.get('attributes')}  \n"
                f"**Размер:** {row.get('size')} ({side_eval(row.get('size'), row.get('side_fabric'))}  \n"
                f"**Срок**: {get_date_str(row.get('deadline'))}  \n")

    def _form_box_text(self, index, row):
        # Текст контейнера красится в красный, когда у наряда приоритет
        text_color = 'red' if row['high_priority'] else 'gray'
        box_text = ''

        # Проверка на бронирование
        if self.reserve_check(index):
            reserver = self.get_reserver(index)
            box_text += f":orange[**Взято - {reserver}**]  \n"
        box_text += f':{text_color}[{self.inner_box_text(row)}'
        if row['comment']:
            box_text += f"**Комментарий**: {row['comment']}  "

        box_text += ']'
        return box_text

    @st.experimental_fragment(run_every="1s")
    def show_tasks_tiles(self, data: pandas.DataFrame, stage_to_done: str, num_columns: int = 3) -> bool:

        page = self.page_name

        if len(data) == 0:
            return st.header('Все заявки выполнены! Хорошая работа 🏖️')

        row_container = st.columns(num_columns)
        count = 0
        for index, row in data.iterrows():

            if count % num_columns == 0:
                row_container = st.columns(num_columns)

            box = row_container[count % num_columns].container(height=250, border=True)

            with box:
                photo = row['photo']
                if photo:
                    col1, col2, buff, col3 = st.columns([12, 3, 1, 6])
                    col2.image(photo, caption='Фото', width=80)
                else:
                    col1, col3 = st.columns([3, 1])

                with col1:
                    st.markdown(self._form_box_text(index, row))
                with col3:
                    st.title('')
                    st.subheader('')
                    if page in st.session_state and st.session_state[page]:
                        if self.reserve_check(index):
                            if st.button(f":green[**{self.done_button_text}**]", key=f'{page}_done_{index}'):
                                data.at[index, stage_to_done] = True
                                employee = st.session_state[page]
                                history_note = f'({time_now()}) {page} [ {employee} ] -> {self.done_button_text}; \n'
                                data.at[index, 'history'] += history_note
                                save_to_file(data, self.task_cash)
                                st.rerun()
                        else:
                            if st.button(f":blue[**{self.reserve_button_text}**]",
                                         key=f'{page}_reserve_{index}'):
                                employee = st.session_state[page]
                                history_note = f'({time_now()}) {page} [ {employee} ] -> {self.reserve_button_text}; \n'
                                data.at[index, 'history'] += history_note
                                self.set_reserver(index, employee)
                                self.set_reserved_state(index, True)
                                save_to_file(data, self.task_cash)
                                st.rerun()
            count += 1
        return True
