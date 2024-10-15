import logging

import pandas as pd
import streamlit as st
from streamlit import session_state as state

from utils.models import MattressRequest, Employee
from utils.app_core import Page
from utils.tools import clear_cash, barcode_link


class BrigadierPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)

        self.TASK_STATE = 'task_dataframe'
        self.SHOW_DONE_STATE = 'show_done'

    def edit_mode_button(self, table_state, show_state, model, edited_df=None, order_id=None):
        # Кнопка для отображения/скрытия таблицы с изменением текста
        if show_state not in state:
            state[show_state] = False

        button_text = ":red[**Сохранить и вернуть режим просмотра**]" if state.get(
            show_state) else '**Перейти в режим редактирования**'

        if st.button(button_text, key=f'{order_id}_mode_button'):
            # Очистить данные, если таблица скрывается
            if state.get(show_state, False) and edited_df is not None:
                self.save_mattress_df_to_db(edited_df, model)
            clear_cash(table_state)
            state[show_state] = not state[show_state]
            st.rerun()

    def edit_mode_button_2(self, show_state, model, edited_df=None):
        button_text = ":red[**Сохранить и вернуть режим просмотра**]" if state.get(
            show_state) else '**Перейти в режим редактирования**'

        if st.button(button_text, key=f'{model}_mode_button'):
            # Очистить данные, если таблица скрывается
            if state.get(show_state, False) and edited_df is not None:
                self.save_mattress_df_to_db(edited_df, model)
            clear_cash(self.TASK_STATE)
            state[show_state] = not state[show_state]
            st.rerun()

    @st.fragment(run_every=1)
    def all_tasks(self):

        mode_state_all_tasks = 'MattressRequest_redact_mode'
        if mode_state_all_tasks not in state:
            state[mode_state_all_tasks] = False

        show_state_all_tasks = 'MattressRequest_full_mode'
        if show_state_all_tasks not in state:
            state[show_state_all_tasks] = False

        orders = self.get_orders_with_mattress_requests()
        col_1, col_2 = st.columns([1, 1])
        with col_1:
            if state.get(mode_state_all_tasks, False):
                st.error('##### Режим редактирования. Изменения других не сохраняются.', icon="🚧")
            else:
                st.info('##### Режим просмотра. Для изменения нажмите кнопку редактирования внизу.', icon="🔎")

        with col_2:
            full_mode_checkbox = st.checkbox('### Показывать завершённые наряды', key=f"{show_state_all_tasks}_checkbox")
            if full_mode_checkbox:
                state[show_state_all_tasks] = True
            else:
                state[show_state_all_tasks] = False

        data = []
        for order in orders:
            for mattress_request in order.mattress_requests:
                if state[show_state_all_tasks] or not (
                        mattress_request.components_is_done and
                        mattress_request.fabric_is_done and
                        mattress_request.gluing_is_done and
                        mattress_request.sewing_is_done and
                        mattress_request.packing_is_done):
                    row = {
                        'order_id': order.id,
                        'mattress_request_id': mattress_request.id,
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

        df = pd.DataFrame(data)

        if df.empty:
            st.write('Активных нарядов нет')
            return

        df.sort_values(by=['high_priority', 'deadline', 'order_id', 'delivery_type'],
                       ascending=[False, True, True, True], inplace=True)

        if state.get(mode_state_all_tasks, False):
            editor = st.data_editor(data=df,
                                    column_config=self.tasks_columns_config,
                                    column_order=(column for column in self.tasks_columns_config.keys()),
                                    hide_index=True,
                                    key=f"{self.TASK_STATE}_redact_mode",
                                    height=650)
            self.edit_mode_button_2(mode_state_all_tasks, MattressRequest, edited_df=editor)
        else:
            st.dataframe(data=df,
                         column_config=self.tasks_columns_config,
                         column_order=(column for column in self.tasks_columns_config.keys()),
                         hide_index=True,
                         key=self.TASK_STATE,
                         height=650)
            self.edit_mode_button_2(mode_state_all_tasks, MattressRequest)

    @st.fragment(run_every=1)
    def tasks_tables(self):
        orders = self.get_orders_with_mattress_requests()
        for order in orders:

            # Проверяем, есть ли активные заявки на матрасы
            has_active_requests = any(
                not (request.components_is_done and
                     request.fabric_is_done and
                     request.gluing_is_done and
                     request.sewing_is_done and
                     request.packing_is_done)
                for request in order.mattress_requests
            )

            if has_active_requests or state[self.SHOW_DONE_STATE]:
                # В active_mode хранится название для переменной session_state,
                # в которой булево значение "Показывать/Не показывать таблицу".
                # Тут происходит инициализация переменной. По умолчанию show_table = False
                active_mode = f"{order.id}_active_mode"
                # Аналогично и для...
                full_mode = f"{order.id}_full_mode"
                if full_mode not in state:
                    state[full_mode] = False

                with st.expander(
                        f'Заказ №{order.id} - {order.organization or order.contact or "- -"}, Срок: {order.deadline}',
                        expanded=True):
                    task_state = self.TASK_STATE + str(order.id)
                    if state.get(active_mode, False):
                        st.error('##### Режим редактирования. Изменения, сделанные на других экранах, сейчас не сохраняются.', icon="🚧")
                        editor = self.tasks_editor(order)
                        self.edit_mode_button(task_state, active_mode, MattressRequest, editor, order.id)
                    else:
                        self.edit_mode_button(task_state, active_mode, MattressRequest, order_id=order.id)
                        self.tasks_table(order)

    def edit_table(self, model, columns_config, columns_order, order_id=None, state_key='state'):
        try:
            # Fetch data from the database
            if order_id:
                data_query = self.session.query(model).filter(MattressRequest.order_id == order_id).all()
            else:
                data_query = self.session.query(model).all()

            # Convert data to DataFrame
            data = []
            for item in data_query:
                row = item.__dict__.copy()
                row.pop('_sa_instance_state', None)
                data.append(row)
            df = pd.DataFrame(data)
            if 'id' in df.columns:
                df.set_index('id', inplace=True)

            edited_df = st.data_editor(
                df,
                column_config=columns_config,
                column_order=columns_order,
                hide_index=True,
                num_rows='fixed',
                key=f"{state_key}_editor"
            )

            return edited_df
        except Exception as e:
            st.error(f"An error occurred: {e}")
            logging.error(f"Error in edit_table: {e}", exc_info=True)
            st.rerun()

    def tasks_table(self, order):
        """Показывает нередактируемую таблицу данных без индексов."""

        columns = self.tasks_columns_config
        data = []
        order_full_mode = f"{order.id}_full_mode"

        # Так сделано, чтобы настройка была только тут, чтобы
        # нельзя было менять таблицу во время режима редактирования
        full_mode_checkbox = st.checkbox('Показывать завершённые наряды', key=f"{order_full_mode}_checkbox")
        if full_mode_checkbox:
            state[order_full_mode] = True
        else:
            state[order_full_mode] = False

        for mattress_request in order.mattress_requests:
            if state[order_full_mode] or not (
                    mattress_request.components_is_done and
                    mattress_request.fabric_is_done and
                    mattress_request.gluing_is_done and
                    mattress_request.sewing_is_done and
                    mattress_request.packing_is_done
            ):
                row = {
                    'order_id': order.id,
                    'mattress_request_id': mattress_request.id,
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

        df = pd.DataFrame(data)

        if not df.empty:
            st.dataframe(data=df,
                         column_config=columns,
                         column_order=(column for column in columns.keys()),
                         hide_index=True)
        else:
            st.write('Активных нарядов нет')

    def tasks_editor(self, order):
        # Define filter conditions for the tasks
        columns_order = list(self.tasks_columns_config.keys())

        state_key = f"tasks_state_{order.id}"

        return self.edit_table(
            model=MattressRequest,
            columns_config=self.tasks_columns_config,
            columns_order=columns_order,
            order_id=order.id,
            state_key=state_key,
        )

    def get_employees(self):
        return self.session.query(Employee).all()

    def add_employee(self):
        with st.form(key='add_employee'):
            name = st.text_input("Имя")
            position = st.text_input("Роли", placeholder="Перечислите через запятую")

            if st.form_submit_button("Внести"):
                if not name or not position:
                    st.error("Пожалуйста, заполните оба поля.")
                else:
                    new_employee = Employee(
                        is_on_shift=False,
                        name=name,
                        position=position,
                        barcode=None,
                    )
                    self.session.add(new_employee)
                    self.session.commit()
                    st.rerun()

    def employees_editor(self):
        # Получаем сотрудников из базы данных
        employees = self.get_employees()

        # Подготавливаем данные для отображения
        data = []
        for employee in employees:
            row = {
                'id': employee.id,
                'is_on_shift': employee.is_on_shift,
                'name': employee.name,
                'position': employee.position,
                'barcode': barcode_link(employee.id),
                'Удалить': False  # Инициализируем флаг удаления как False
            }
            data.append(row)
        df = pd.DataFrame(data)
        if 'id' in df.columns:
            df.set_index('id', inplace=True)

        # Настройки колонок для отображения
        self.employee_columns_config = {
            "is_on_shift": st.column_config.CheckboxColumn("На смене", default=False),
            "name": st.column_config.TextColumn("Имя", default=''),
            "position": st.column_config.TextColumn("Роли", width='medium', default=''),
            "barcode": st.column_config.LinkColumn("Штрих-код", display_text="Открыть", disabled=False),
            "Удалить": st.column_config.CheckboxColumn("Удалить", default=False),
        }
        # Отображаем таблицу редактирования
        edited_df = st.data_editor(
            df,
            column_config=self.employee_columns_config,
            column_order=['is_on_shift', 'name', 'position', 'Удалить', 'barcode'],
            hide_index=True,
            num_rows='fixed',
            key='employee_editor'
        )
        # Кнопка для сохранения изменений
        if st.button('Сохранить'):
            self.save_employee_changes(edited_df)

    def save_employee_changes(self, edited_df):
        # Итерируемся по строкам DataFrame
        for index, row in edited_df.iterrows():
            employee = self.session.get(Employee, index)
            if row['Удалить']:
                # Удаляем сотрудника
                if employee:
                    self.session.delete(employee)
            else:
                # Обновляем поля сотрудника
                if employee:
                    employee.is_on_shift = row['is_on_shift']
                    employee.name = row['name']
                    employee.position = row['position']
        self.session.commit()
        st.rerun()


Page = BrigadierPage('Производственный терминал', '🛠️')

tasks_tab, employee_tab = st.tabs(['Матрасы', 'Сотрудники'])

with tasks_tab:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("🏭 Все наряды")

    with col2:
        st.info('''На этом экране показываются данные о нарядах в режиме реального времени. Чтобы поправить любой
        наряд, включите режим редактирования. Он обладает высшим приоритетом - пока активен режим редактирования,
        изменения других рабочих не сохраняются. **Не забывайте сохранять таблицу!**''', icon="ℹ️")

    Page.all_tasks()

with employee_tab:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("👷 Сотрудники")
    with col2:
        # Должность аналогична свойству page_name на файлах страниц
        st.info('Выставляйте рабочих на смену. Они будут активны при выборе ответственного на нужном экране.  \n'
                'В поле "Роли" пропишите рабочее место сотруднику. Можно вписать несколько.', icon="ℹ️")

    st.warning('##### Доступно: заготовка, сборка, нарезка, шитьё, упаковка')
    sub_col_1, sub_col_2 = st.columns([2, 1])
    with sub_col_1:
        Page.employees_editor()
    with sub_col_2:
        with st.expander("Добавить нового сотрудника"):
            Page.add_employee()
