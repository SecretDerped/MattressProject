import datetime
import logging
from pathlib import Path

import streamlit as st

from sqlalchemy.orm import joinedload

from utils.db_connector import session
from utils.models import MattressRequest, Order
from utils.tools import config, read_file, time_now


class Page:
    def __init__(self, page_name, icon):
        self.page_name = page_name
        self.icon = icon

        self.employees_cash = config.get('site').get('hardware').get('employees_cash_filepath')
        self.employee_columns_config = {
            "is_on_shift": st.column_config.CheckboxColumn("На смене", default=False),
            "name": st.column_config.TextColumn("Имя / Фамилия", default=''),
            "position": st.column_config.TextColumn("Роли", width='medium', default=''),
            "barcode": st.column_config.LinkColumn("Штрих-код", display_text="Открыть", disabled=True),
        }

        self.task_cash = Path(config.get('site').get('hardware').get('tasks_cash_filepath'))
        self.tasks_columns_config = {
            "high_priority": st.column_config.CheckboxColumn("Приоритет", default=False),
            "deadline": st.column_config.DateColumn("Срок",
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
            "components_is_done": st.column_config.CheckboxColumn("Материалы",
                                                                  default=False),
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
            "organization": st.column_config.TextColumn("Заказчик",
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

        self.session = session()
        st.set_page_config(page_title=self.page_name,
                           page_icon=self.icon,
                           layout="wide")

    def update_db(self, task):
        logging.debug(f'Update: {task}')
        try:
            self.session.add(task)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logging.error(f"Error updating database: {e}")
        finally:
            self.session.close()

    def save_changes_to_db(self, edited_df, model):
        for index, row in edited_df.iterrows():
            instance = self.session.get(model, index)
            if instance:
                for column in row.index:
                    if hasattr(instance, column):
                        setattr(instance, column, row[column])
        self.session.commit()

    def header(self):
        st.title(f'{self.icon} {self.page_name}')

    def get_orders_with_mattress_requests(self):
        # Возвращает все заказы в порядке id. Если нужно сортировать в порядке убывания, используй Order.id.desc()
        return (self.session.query(Order)
                .options(joinedload(Order.mattress_requests))
                .order_by(Order.id.desc())
                .limit(50)
                .all())


class ManufacturePage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)
        self.done_button_text = 'Готово'
        self.header()

    def header(self):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f'{self.icon} {self.page_name}')
        with col2:
            self.employee_choose()

    def load_tasks(self):
        return (self.session.query(MattressRequest)
                            .order_by(MattressRequest.id.desc())
                            .limit(300)
                            .all())

    def employees_on_shift(self, searching_position: str) -> list:
        """Принимает строку для фильтрации по роли сотрудника (position).
        Читает .pkl из employees_cash_filepath, преобразует в датафрейм.
        Фильтрует записи, где значение в "is_on_shift" стоит True,
        а в колонке "position" есть подстрока из аргумента функции (независимо от регистра).

        :returns: [список имен сотрудников на смене по искомой роли]"""
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
                     placeholder="Выберите сотрудника",
                     options=self.employees_on_shift(self.page_name),
                     index=None,
                     key=self.page_name,
                     on_change=save_employee, args=(self.page_name,))

    def update_tasks(self, tasks_df, edited_tasks_df, done_field: str):
        for index, row in edited_tasks_df.iterrows():
            if not row[done_field]:
                continue

            tasks_df.at[index, 'history'] += self.create_history_note()
            tasks_df.at[index, done_field] = True

    def create_history_note(self):
        employee = st.session_state.get(self.page_name)
        return f'({time_now()}) {self.page_name} [ {employee} ] -> {self.done_button_text}; \n'

