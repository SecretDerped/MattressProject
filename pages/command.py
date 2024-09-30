import pandas as pd
import streamlit as st
from sqlalchemy.orm import joinedload

from utils.models import Order, MattressRequest, Employee
from utils.app_core import Page
from utils.tools import clear_cash, cashing, get_cash, barcode_link


class BrigadierPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)

        self.TASK_STATE = 'task_dataframe'
        self.EMPLOYEE_STATE = 'employee_dataframe'
        self.SHOW_DONE_STATE = 'show_done'

        self.EMPLOYEE_ACTIVE_MODE = 'employee_active_mode'

    def show_and_hide_button(self, table_state, show_state, model, edited_df=None, order_id=None):
        # Кнопка для отображения/скрытия таблицы с изменением текста
        if show_state not in st.session_state:
            st.session_state[show_state] = False

        if not st.session_state.get(show_state, False):
            button_text = '**Перейти в режим редактирования**'
        else:
            button_text = ":red[**Сохранить и вернуть режим просмотра**]"

        if st.button(button_text, key=f'{order_id}_mode_button'):
            # Очистить данные, если таблица скрывается
            if st.session_state.get(show_state, False) and edited_df is not None:
                self.save_changes_to_db(edited_df, model)
            clear_cash(table_state)
            st.session_state[show_state] = not st.session_state[show_state]
            st.rerun()

    def get_orders_with_mattress_requests(self):
        # Возвращает все заказы в порядке id. Если нужно сортировать в порядке убывания, используй Order.id.desc()
        return (self.session.query(Order)
                .options(joinedload(Order.mattress_requests))
                .order_by(Order.id.desc())
                .limit(50)
                .all())

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

            if has_active_requests or st.session_state[self.SHOW_DONE_STATE]:
                # В active_mode хранится название для переменной session_state,
                # в которой булево значение "Показывать/Не показывать таблицу".
                # Тут происходит инициализация переменной. По умолчанию show_table = False
                active_mode = f"{order.id}_active_mode"
                # Аналогично и для...
                full_mode = f"{order.id}_full_mode"
                if full_mode not in st.session_state:
                    st.session_state[full_mode] = False

                with st.expander(f'Заказ №{order.id} - {order.organization or order.contact or "- -"}', expanded=True):
                    state = self.TASK_STATE + str(order.id)
                    if st.session_state.get(active_mode, False):
                        st.error('##### Режим редактирования. Изменения других не сохраняются.', icon="🚧")
                        editor = self.tasks_editor(order)
                        self.show_and_hide_button(state, active_mode, MattressRequest, edited_df=editor, order_id=order.id)
                    else:
                        self.show_and_hide_button(state, active_mode, MattressRequest, order_id=order.id)
                        self.tasks_table(order)

    def tasks_table(self, order):
        """Показывает нередактируемую таблицу данных без индексов."""

        columns = self.tasks_columns_config
        data = []
        order_full_mode = f"{order.id}_full_mode"

        # Так сделано, чтобы настройка была только тут, чтобы
        # нельзя было менять таблицу во время режима редактирования
        full_mode_checkbox = st.checkbox('Показывать завершённые наряды', key=f"{order_full_mode}_checkbox")
        if full_mode_checkbox:
            st.session_state[order_full_mode] = True
        else:
            st.session_state[order_full_mode] = False

        for mattress_request in order.mattress_requests:
            if st.session_state[order_full_mode] or not (
                    mattress_request.components_is_done and
                    mattress_request.fabric_is_done and
                    mattress_request.gluing_is_done and
                    mattress_request.sewing_is_done and
                    mattress_request.packing_is_done
            ):
                row = {
                    'high_priority': mattress_request.high_priority,
                    'deadline': mattress_request.deadline,
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
        """База данных в этом проекте - PostgreSQL. Сначала идёт запрос в базу, а потом записи превращаются в датафрейм
        для отображения таблицы. Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
        а кэш пишется в session_state. Каждое изменение таблицы провоцируют on_change методы, а потом обновление
        всей страницы. Поэтому система такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
        Как только какое-то поле было изменено, то изменения записываются в кэш,
        потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями сохраняется в базу."""
        state = self.TASK_STATE + str(order.id)
        columns = self.tasks_columns_config

        try:
            # Если функция редактирования не открывалась, значит нет кэша.
            # Грузим данные из базы и копируем в кэш.
            if state in st.session_state:
                # Если функция была открыта, значит после изменения на странице остался кэш,
                # то есть загружаем данные из кэша.
                df = get_cash(state)
            else:
                data = []
                for mattress_request in order.mattress_requests:
                    row = {
                        'id': mattress_request.id,
                        'high_priority': mattress_request.high_priority,
                        'deadline': mattress_request.deadline,
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
                df.set_index('id', inplace=True)  # Устанавливаем 'id' как индекс
                cashing(df, state)

            file_full_mode = f"{order.id}_full_mode"
            # Стейт галочки "Показать все наряды". Декларирована вне объекта там, внизу
            if st.session_state.get(file_full_mode, False):
                filtered_df = df
            else:
                filtered_df = df[(df['components_is_done'] == False) |
                                 (df['fabric_is_done'] == False) |
                                 (df['gluing_is_done'] == False) |
                                 (df['sewing_is_done'] == False) |
                                 (df['packing_is_done'] == False)]

            editor = st.data_editor(
                data=filtered_df,
                column_config=columns,
                column_order=(column for column in columns.keys()),
                hide_index=True,
                num_rows="fixed",
                key=f"{state}_editor",
            )

            return editor

        except RuntimeError:
            st.rerun()

    def get_employees(self):
        # Возвращает все заказы в порядке id. Если нужно сортировать в порядке убывания, используй Order.id.desc()
        return self.session.query(Employee).all()

    def add_employee(self):
        with st.form(key='add_employee'):
            # Заголовок формы
            st.markdown("#### Добавить нового сотрудника")

            # Поля для ввода данных сотрудника
            name = st.text_input("Имя")
            position = st.text_input("Роли", placeholder="Перечислите через запятую")

            # Кнопка для добавления сотрудника
            if st.form_submit_button("Добавить сотрудника"):
                if name and position:  # Проверка, что обязательные поля заполнены
                    new_employee = Employee(
                        is_on_shift=False,
                        name=name,
                        position=position,
                        barcode=None,
                    )
                    self.session.add(new_employee)  # Добавление нового сотрудника в сессию
                    self.session.commit()  # Сохранение изменений в базе данных
                    st.success("Сотрудник успешно добавлен!")
                else:
                    st.error("Пожалуйста, заполните все обязательные поля.")

    def employees_editor(self, dynamic_mode: bool = False):
        employees = self.get_employees()
        # Если кэша нет, загружаем туда данные
        state = self.EMPLOYEE_STATE
        # Если функция была открыта, значит после изменения на странице остался кэш,
        # то есть загружаем данные из кэша.
        if state not in st.session_state:
            data = []
            if not employees:
                return st.subheader('В базе данных нет сотрудников. Добавьте новых.')
            for employee in employees:
                row = {
                    'id': employee.id,
                    'is_on_shift': employee.is_on_shift,
                    'name': employee.name,
                    'position': employee.position,
                    'barcode': employee.barcode
                }
                data.append(row)
            df = pd.DataFrame(data)
            # Устанавливаем 'id' как индекс
            df.set_index('id', inplace=True)

            # Создаётся колонка строк, где каждая ячейка формируется на основе соответсвующего индекса в датафрейме.
            # Для того чтобы это сработало, мы берём список индексов, преобразовываем в серию для чтения, применяем
            # к каждому индексу функцию, записываем полученную строку на соответсвующую позицию и сохраняем
            # datatype столбца как string. Всё это в строчке ниже
            df['barcode'] = df.index.to_series().apply(barcode_link).astype('string')
            cashing(df, state)

        if dynamic_mode:
            columns = ("name", "position")
        else:
            columns = ("is_on_shift", "name", "position", "barcode")

        edited_df = get_cash(state)
        editor = st.data_editor(
            edited_df,
            column_config=self.employee_columns_config,
            column_order=columns,
            hide_index=True,
            num_rows='fixed',
            on_change=cashing, args=(edited_df, state),
            key=f"{state}_editor"
        )
        self.save_changes_to_db(get_cash(state), Employee)


Page = BrigadierPage('Производственный терминал', '🛠️')

tasks_tab, employee_tab = st.tabs(['Наряды', 'Сотрудники'])

with tasks_tab:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("🏭 Все наряды")

        if st.checkbox('Отобразить сделанные заявки', key=f"{Page.SHOW_DONE_STATE}_key"):
            st.session_state[Page.SHOW_DONE_STATE] = True
        else:
            st.session_state[Page.SHOW_DONE_STATE] = False

    with col2:
        st.write(' ')
        st.info('''На этом экране показываются данные о нарядах в режиме реального времени. Чтобы поправить любой
        наряд, включите режим редактирования. Он обладает высшим приоритетом - пока активен режим редактирования,
        изменения других рабочих не сохраняются. **Не забывайте сохранять таблицу!**''', icon="ℹ️")

    Page.tasks_tables()

with employee_tab:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("👷 Сотрудники")

    with col2:
        st.write(' ')
        # Должность аналогична свойству page_name на файлах страниц
        st.info('Выставляйте рабочих на смену. Они будут активны при выборе ответственного на нужном экране. В поле'
                '"Роли" пропишите рабочее место сотруднику. Можно вписать несколько.  \n'
                'Доступно: заготовка, сборка, нарезка, шитьё, упаковка',
                icon="ℹ️")

    col1, col2 = st.columns([1, 1])
    with col1:
        # Отображение таблицы в зависимости от состояния
        if st.session_state.get(Page.EMPLOYEE_ACTIVE_MODE, False):
            Page.employees_editor(True)
            Page.add_employee()
        else:
            Page.employees_editor()
        Page.show_and_hide_button(Page.EMPLOYEE_STATE, Page.EMPLOYEE_ACTIVE_MODE, Employee)

    with col2:
        pass

