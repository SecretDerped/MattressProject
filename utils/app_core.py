import datetime
import logging
from pathlib import Path

import streamlit as st

from sqlalchemy.orm import joinedload

from utils.db_connector import session
from utils.models import MattressRequest, Order, Employee
from utils.tools import config, time_now


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

    @st.fragment(run_every=5)
    def employees_on_shift(self, searching_position: str) -> list:
        """Возвращает список кортежей (имя сотрудника, ID) сотрудников, которые на смене и соответствуют заданной роли."""
        employees = self.session.query(Employee).filter(
            Employee.is_on_shift == True,
            Employee.position.ilike(f'%{searching_position}%')
        ).all()
        return [(employee.name, employee.id) for employee in employees]

    def employee_choose(self):
        """Виджет для выбора активного сотрудника для рабочего места."""

        employees = self.employees_on_shift(self.page_name)
        if not employees:
            st.warning("Нет доступных сотрудников на смене с соответствующей ролью.")
            return

        employee_names = [name for name, _ in employees]

        # Проверяем, есть ли уже выбранный сотрудник в session_state
        if self.page_name in st.session_state:
            selected_name = st.session_state[self.page_name]
            if selected_name not in employee_names:
                # Если ранее выбранный сотрудник больше не доступен, выбираем первого из списка
                selected_name = employee_names[0]
        else:
            selected_name = employee_names[0]

        # Создаем selectbox для выбора сотрудника
        selected_name = st.selectbox('Выберите сотрудника',
                                     options=employee_names,
                                     index=employee_names.index(selected_name),
                                     key=self.page_name)

        # Сохраняем ID выбранного сотрудника в session_state с уникальным ключом
        selected_employee = next((emp for emp in employees if emp[0] == selected_name), None)
        if selected_employee:
            st.session_state[f"{self.page_name}_employee_id"] = selected_employee[1]

    def update_tasks(self, tasks_df, edited_tasks_df, done_field: str):
        for index, row in edited_tasks_df.iterrows():
            if not row[done_field]:
                continue

            tasks_df.at[index, 'history'] += self.create_history_note()
            tasks_df.at[index, done_field] = True

    def create_history_note(self):
        employee = st.session_state.get(self.page_name)
        return f'({time_now()}) {self.page_name} [ {employee} ] -> {self.done_button_text}; \n'

