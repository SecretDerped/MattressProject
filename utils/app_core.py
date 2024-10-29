import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from sqlalchemy.orm import joinedload

from utils.db_connector import session
from utils.models import MattressRequest, Order, Employee
from utils.tools import config, create_history_note

site_conf = config.get('site')


class Page:
    def __init__(self, page_name, icon):
        self.page_name = page_name
        self.icon = icon

        self.employee_columns_config = {
            "is_on_shift": st.column_config.CheckboxColumn("На смене", default=False),
            "name": st.column_config.TextColumn("Имя", default=''),
            "position": st.column_config.TextColumn("Роли", width='medium', default=''),
            "barcode": st.column_config.LinkColumn("Штрих-код", display_text="Открыть", disabled=False),
            "Удалить": st.column_config.CheckboxColumn("Удалить", default=False),
        }

        self.task_cash = Path(config.get('site').get('hardware').get('tasks_cash_filepath'))
        self.tasks_columns_config = {
            'id': st.column_config.NumberColumn("Матрас", disabled=True),
            'order_id': st.column_config.NumberColumn("Заказ", disabled=True),
            "high_priority": st.column_config.CheckboxColumn("Приоритет", default=False),
            "deadline": st.column_config.DatetimeColumn("Срок",
                                                        format="D.MM",
                                                        disabled=True),
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
                                                              required=True,
                                                              disabled=True),
            "address": st.column_config.TextColumn("Адрес",
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

    def save_mattress_df_to_db(self, edited_df, model):
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
                .all())

    @staticmethod
    def get_tasks_as_df(orders):
        data = []
        for order in orders:
            for mattress_request in order.mattress_requests:
                row = {
                    'id': mattress_request.id,
                    'order_id': order.id,
                    'high_priority': mattress_request.high_priority,
                    'deadline': order.deadline,
                    'article': mattress_request.article,
                    'size': mattress_request.size,
                    'base_fabric': mattress_request.base_fabric,
                    'side_fabric': mattress_request.side_fabric,
                    'photo': mattress_request.photo,
                    'comment': mattress_request.comment,
                    'springs': mattress_request.springs,
                    'attributes': mattress_request.attributes,
                    'components_is_done': mattress_request.components_is_done,
                    'fabric_is_done': mattress_request.fabric_is_done,
                    'gluing_is_done': mattress_request.gluing_is_done,
                    'sewing_is_done': mattress_request.sewing_is_done,
                    'packing_is_done': mattress_request.packing_is_done,
                    'history': mattress_request.history,
                    'organization': order.organization,
                    'delivery_type': order.delivery_type,
                    'address': order.address,
                    'region': order.region,
                    'created': mattress_request.created,
                }
                data.append(row)

        return pd.DataFrame(data)

    @staticmethod
    def filter_incomplete_tasks(df, conditions):
        """
        Фильтрует DataFrame по условиям, переданным в виде словаря.

        :param df: DataFrame с заявками
        :param conditions: Словарь условий, где ключ — это название столбца, а значение — значение для фильтрации
        :return: Отфильтрованный DataFrame
        """
        # Создаем фильтр, объединяя все условия через логическое "или"
        filter_condition = None

        for column, condition_value in conditions.items():
            # Формируем условие для текущего столбца
            current_condition = (df[column] == condition_value)

            # Объединяем условия через логическое "или"
            if filter_condition is None:
                filter_condition = current_condition
            else:
                filter_condition |= current_condition

        # Применяем фильтр к DataFrame и возвращаем результат
        filtered_df = df[filter_condition]
        return filtered_df

    def get_sorted_tasks(self):
        orders = self.get_orders_with_mattress_requests()
        df = self.get_tasks_as_df(orders)
        if df.empty:
            st.write('Активных нарядов нет')
            return

        # Преобразуем поле delivery_type в категорию с определенным порядком
        df['delivery_type'] = pd.Categorical(df['delivery_type'],
                                             categories=site_conf.get('delivery_types'),
                                             ordered=True)

        df.sort_values(by=['high_priority', 'deadline', 'delivery_type'],
                       ascending=[False, True, True],
                       ignore_index=True,
                       inplace=True)
        if 'id' in df.columns:
            df.set_index('id', inplace=True)

        return df


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

    @st.fragment(run_every=3)
    def employees_on_shift(self, searching_position: str) -> list:
        """Возвращает список кортежей (имя сотрудника, ID) сотрудников,
        которые на смене и соответствуют заданной роли."""
        employees = self.session.query(Employee).filter(
            Employee.is_on_shift == True,
            Employee.position.ilike(f'%{searching_position}%')).all()
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

    def update_tasks(self, edited_df, done_field: str):
        for index, row in edited_df.iterrows():
            if not row[done_field]:
                continue

            instance = self.session.get(MattressRequest, index)
            new_history = self.pages_history_note() + row['history']
            setattr(instance, 'history', new_history)
            setattr(instance, done_field, True)

        self.session.commit()

    def pages_history_note(self):
        employee = st.session_state.get(self.page_name)
        return create_history_note(self.page_name, employee, self.done_button_text)
