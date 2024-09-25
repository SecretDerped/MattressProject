import pandas as pd
import streamlit as st
from sqlalchemy.orm import joinedload

from utils.models import Order, MattressRequest
from utils.db_connector import session
from utils.app_core import Page
from utils.tools import clear_cash, read_file, cashing, \
    get_cash, save_to_file, barcode_link


def get_orders_with_mattress_requests(session):
    # Возвращает все заказы в порядке id. Если нужно сортировать в порядке убывания, используй Order.id.desc()
    return session.query(Order).options(joinedload(Order.mattress_requests)).order_by(Order.id.desc()).limit(20).all()


class BrigadierPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)

        self.session = session()
        self.TASK_STATE = 'task_dataframe'
        self.EMPLOYEE_STATE = 'employee_dataframe'
        self.SHOW_DONE_STATE = 'show_done'

        self.EMPLOYEE_ACTIVE_MODE = 'employee_active_mode'

    def save_changes_to_db(self, edited_df):
        for index, row in edited_df.iterrows():
            mattress_request = self.session.get(MattressRequest, index)  # Используем session.get()
            if mattress_request:
                for column in self.tasks_columns_config.keys():
                    setattr(mattress_request, column, row[column])
        self.session.commit()

    def show_and_hide_button(self, table_state, show_state, edited_df=None, original_df=None, order_id=None):
        # Кнопка для отображения/скрытия таблицы с изменением текста
        if show_state not in st.session_state:
            st.session_state[show_state] = False

        if not st.session_state.get(show_state, False):
            button_text = '**Перейти в режим редактирования**'
        else:
            button_text = ":red[**Сохранить и вернуть режим просмотра**]"

        if st.button(button_text, key=f'{order_id}_mode_button'):
            # Очистить данные, если таблица скрывается
            if st.session_state.get(show_state, False):
                if edited_df is not None and original_df is not None:
                    self.save_changes_to_db(edited_df)
            clear_cash(table_state)
            st.session_state[show_state] = not st.session_state[show_state]
            st.rerun()

    def tasks_table(self, order):
        """Показывает нередактируемую таблицу данных без индексов."""

        columns = self.tasks_columns_config
        data = []
        file_full_mode = f"{order.id}_full_mode"

        # Так сделано, чтобы настройка была только тут, чтобы
        # нельзя было менять таблицу во время режима редактирования
        full_mode_checkbox = st.checkbox('Показывать завершённые наряды', key=f"{file_full_mode}_full_mode_checkbox")
        if full_mode_checkbox:
            st.session_state[file_full_mode] = True
        else:
            st.session_state[file_full_mode] = False

        for mattress_request in order.mattress_requests:
            if st.session_state[file_full_mode] or not (
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
            pass

    def tasks_editor(self, order):
        """База данных в этом проекте представляет собой файл pkl с датафреймом библиотеки pandas.
        Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
        а кэш пишется в session_state текущего состояния таблицы. Каждое изменение таблицы
        провоцируют on_change методы, а потом обновление всей страницы. Поэтому система
        такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
        Как только какое-то поле было изменено, то изменения записываются в кэш,
        потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями
        сохраняется в базу."""
        state = self.TASK_STATE + str(order.id)
        columns = self.tasks_columns_config

        try:
            # Если функция редактирования не открывалась, значит нет кэша.
            # Грузим данные из базы и копируем в кэш.
            if state not in st.session_state:
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
            # Если функция была открыта, значит после изменения на странице остался кэш,
            # то есть загружаем данные из кэша.
            else:
                df = get_cash(state)

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

            return editor, df

        except RuntimeError:
            st.rerun()

    def tasks_tables(self):
        orders = get_orders_with_mattress_requests(self.session)
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

                with st.expander(f'Заказ №{order.id} - {order.organization or order.contact or "- -"}'):
                    state = self.TASK_STATE + str(order.id)
                    if st.session_state.get(active_mode, False):
                        st.error('##### Режим редактирования. Изменения других не сохраняются.', icon="🚧")
                        editor, original_data = self.tasks_editor(order)
                        self.show_and_hide_button(state, active_mode, editor, original_data, order.id)
                    else:
                        self.show_and_hide_button(state, active_mode, order_id=order.id)
                        self.tasks_table(order)

    def employees_editor(self, dynamic_mode: bool = False):
        # Если кэша нет, загружаем туда данные
        state = self.EMPLOYEE_STATE
        if state not in st.session_state:
            dataframe = read_file(self.employees_cash)

            # Создаётся колонка строк, где каждая ячейка формируется на основе соответсвующего индекса в датафрейме.
            # Для того чтобы это сработало, мы берём список индексов, преобразовываем в серию для чтения, применяем
            # к каждому индексу функцию, записываем полученную строку на соответсвующую позицию и сохраняем
            # datatype столбца как string. Всё это в строчке ниже
            dataframe['barcode'] = dataframe.index.to_series().apply(barcode_link).astype('string')

            cashing(dataframe, state)

        if dynamic_mode:
            mode = 'dynamic'
            columns = ("name", "position")
        else:
            mode = 'fixed'
            columns = ("is_on_shift", "name", "position", "barcode")

        edited_df = get_cash(state)
        editor = st.data_editor(
            edited_df,
            column_config=self.employee_columns_config,
            column_order=columns,
            hide_index=True,
            num_rows=mode,
            on_change=cashing, args=(edited_df, state),
            key=f"{state}_{mode}_editor"
        )
        save_to_file(editor, self.employees_cash)


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
        Page.show_and_hide_button(Page.EMPLOYEE_STATE, Page.EMPLOYEE_ACTIVE_MODE)

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
        else:
            Page.employees_editor()

    with col2:
        pass

