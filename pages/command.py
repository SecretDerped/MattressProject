import pandas as pd
import streamlit as st
from sqlalchemy import select
from streamlit import session_state as state

from utils.models import MattressRequest, Employee, EmployeeTask
from utils.app_core import Page
from utils.tools import barcode_link


class BrigadierPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)

        self.TASK_STATE = 'task_dataframe'

        self.SHOW_ALL_TASKS = 'MattressRequest_full_mode'
        if self.SHOW_ALL_TASKS not in state:
            state[self.SHOW_ALL_TASKS] = False

        self.REDACT_TASKS = 'MattressRequest_redact_mode'
        if self.REDACT_TASKS not in state:
            state[self.REDACT_TASKS] = False

    def mattress_editor(self, dataframe):
        return st.data_editor(data=dataframe,
                              column_config=self.tasks_columns_config,
                              column_order=(column for column in self.tasks_columns_config.keys()),
                              hide_index=False,
                              key=self.TASK_STATE,
                              height=650)

    def mattress_viewer(self, dataframe):
        st.dataframe(data=dataframe,
                     column_config=self.tasks_columns_config,
                     column_order=(column for column in self.tasks_columns_config.keys()),
                     hide_index=False,
                     key=self.TASK_STATE,
                     height=650)

    @st.fragment(run_every=1)
    def all_tasks(self):
        half_col_1, half_col_2 = st.columns([1, 1])
        with half_col_1:
            if state.get(self.REDACT_TASKS, False):
                st.error('##### Режим редактирования. Изменения других не сохраняются.', icon="🚧")
            else:
                st.info('##### Режим просмотра. Для изменения нажмите кнопку редактирования внизу.', icon="🔎")

        with half_col_2:
            full_mode_checkbox = st.checkbox('### Показывать завершённые наряды', key=f"{self.SHOW_ALL_TASKS}_checkbox")
            state[self.SHOW_ALL_TASKS] = True if full_mode_checkbox else False

        df = self.get_sorted_tasks()

        if not state[self.SHOW_ALL_TASKS]:
            conditions = {
                'components_is_done': False,
                'fabric_is_done': False,
                'gluing_is_done': False,
                'sewing_is_done': False,
                'packing_is_done': False
            }
            df = self.filter_incomplete_tasks(df, conditions)

        if state.get(self.REDACT_TASKS, False):
            edited_df = self.mattress_editor(df)
            self.edit_mode_button(MattressRequest, edited_df)
        else:
            self.mattress_viewer(df)
            self.edit_mode_button(MattressRequest)

    def edit_mode_button(self, model, edited_dataframe=None):
        redact_mode = self.REDACT_TASKS
        if state.get(redact_mode, False):
            button_text = ":red[**Сохранить и вернуть режим просмотра**]"
        else:
            button_text = '**Перейти в режим редактирования**'

        if not st.button(button_text, key=f'{model}_mode_button'):
            return

        if state.get(redact_mode, False) and edited_dataframe is not None:
            self.save_mattress_df_to_db(edited_dataframe, model)
        state[redact_mode] = not state[redact_mode]

        # Очистить данные, если таблица скрывается
        task_state = self.TASK_STATE
        if task_state in st.session_state:
            del st.session_state[task_state]

        st.rerun()

    @staticmethod
    def get_df_from_employees(employees):
        # Подготавливаем данные для отображения
        data = []
        for employee in employees:
            row = {'id': employee.id,
                   'is_on_shift': employee.is_on_shift,
                   'name': employee.name,
                   'position': employee.position,
                   'barcode': barcode_link(employee.id),
                   'Удалить': False}  # Инициализируем флаг удаления как False
            data.append(row)

        dataframe = pd.DataFrame(data)
        if 'id' in dataframe.columns:
            dataframe.set_index('id', inplace=True)

        return dataframe

    def employees_editor(self):
        # Получаем сотрудников из базы данных
        employees = self.session.query(Employee).all()

        df = self.get_df_from_employees(employees)

        # Отображаем таблицу редактирования
        edited_df = st.data_editor(
            data=df,
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
            if employee:
                if row['Удалить']:
                    result = self.session.execute(select(EmployeeTask).where(EmployeeTask.employee_id == index))
                    employee_task = result.scalar_one_or_none()
                    self.session.delete(employee_task)
                    self.session.delete(employee)
                else:
                    employee.is_on_shift = row['is_on_shift']
                    employee.name = row['name']
                    employee.position = row['position']

        self.session.commit()
        st.rerun()

    def add_employee(self):
        with st.form(key='add_employee'):
            name = st.text_input("Имя")
            position = st.text_input("Роли", placeholder="Перечислите через запятую")

            if st.form_submit_button("Внести"):
                if not name or not position:
                    st.error("Пожалуйста, заполните оба поля.")
                else:
                    new_employee = Employee(is_on_shift=False,
                                            name=name,
                                            position=position,
                                            barcode=None)
                    self.session.add(new_employee)
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
