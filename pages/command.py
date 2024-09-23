import streamlit as st

from utils.app_core import Page
from utils.tools import clear_cash, read_file, cashing, \
    get_cash, save_to_file, barcode_link


def show_and_hide_button(table_state, show_state, edited_df=None, original_df=None, file_path=None):
    # Кнопка для отображения/скрытия таблицы с изменением текста
    if not st.session_state[show_state]:
        button_text = '**Перейти в режим редактирования**'
    else:
        button_text = ":red[**Сохранить и вернуть режим просмотра**]"

    if st.button(button_text, key=f'{file_path}_mode_button'):
        # Очистить данные, если таблица скрывается
        if st.session_state[show_state]:
            if edited_df is not None and original_df is not None:
                for index, row in edited_df.iterrows():
                    original_df.loc[index] = row
                save_to_file(original_df, file_path)
        clear_cash(table_state)
        st.session_state[show_state] = not st.session_state[show_state]
        st.rerun()


class BrigadierPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)

        self.TASK_STATE = 'task_dataframe'
        self.EMPLOYEE_STATE = 'employee_dataframe'
        self.SHOW_DONE_STATE = 'show_done'

        self.EMPLOYEE_ACTIVE_MODE = 'employee_active_mode'

        if self.EMPLOYEE_ACTIVE_MODE not in st.session_state:
            st.session_state[self.EMPLOYEE_ACTIVE_MODE] = False

        if self.SHOW_DONE_STATE not in st.session_state:
            st.session_state[self.SHOW_DONE_STATE] = False

    @st.experimental_fragment(run_every="1s")
    def tasks_table(self, file):
        """Показывает нередактируемую таблицу данных без индексов."""
        columns = self.tasks_columns_config
        data = read_file(file)
        # В file_full_mode хранится состояние "Показать все наряды",
        file_full_mode = f"{file}_full_mode"

        # Так сделано, чтобы настройка была только тут, чтобы
        # нельзя было менять таблицу во время режима редактирования
        if st.checkbox('Показывать завершённые наряды', key=f"{file_full_mode}_full_mode_checkbox"):
            st.session_state[file_full_mode] = True
        else:
            st.session_state[file_full_mode] = False

        if not st.session_state[file_full_mode]:
            data = data[(data['components_is_done'] == False) |
                        (data['fabric_is_done'] == False) |
                        (data['gluing_is_done'] == False) |
                        (data['sewing_is_done'] == False) |
                        (data['packing_is_done'] == False)]

        st.dataframe(data=data,
                     column_config=columns,
                     column_order=(column for column in columns.keys()),
                     hide_index=True)

    def tasks_editor(self, file):
        """База данных в этом проекте представляет собой файл pkl с датафреймом библиотеки pandas.
        Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
        а кэш пишется в session_state текущего состояния таблицы. Каждое изменение таблицы
        провоцируют on_change методы, а потом обновление всей страницы. Поэтому система
        такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
        Как только какое-то поле было изменено, то изменения записываются в кэш,
        потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями
        сохраняется в базу."""
        state = self.TASK_STATE + str(file)
        columns = self.tasks_columns_config

        try:
            # Если функция редактирования не открывалась, значит нет кэша.
            # Грузим данные из базы и копируем в кэш.
            if state not in st.session_state:
                data = read_file(file)
                cashing(data, state)
            # Если функция была открыта, значит после изменения на странице остался кэш,
            # то есть загружаем данные из кэша.
            else:
                data = get_cash(state)

            # Стейт галочки "Показать все наряды". Декларирована вне объекта там, внизу
            if st.session_state[f"{file}_full_mode"]:
                filtered_df = data
            else:
                filtered_df = data[(data['components_is_done'] == False) |
                                   (data['fabric_is_done'] == False) |
                                   (data['gluing_is_done'] == False) |
                                   (data['sewing_is_done'] == False) |
                                   (data['packing_is_done'] == False)]

            editor = st.data_editor(
                data=filtered_df,
                column_config=columns,
                column_order=(column for column in columns.keys()),  # Порядок получается такой же, как в конфиге колонн
                hide_index=True,
                num_rows="fixed",
                key=f"{file}_{state}_editor",
            )

            return editor, data

        except RuntimeError:
            st.rerun()

    def tasks_tables(self):
        for file in self.task_cash.iterdir():
            if not file.is_file():
                continue

            data = read_file(file)
            # Флаг для показа/скрытия таблицы
            has_active_records = not data[
                (data['components_is_done'] == False) |
                (data['fabric_is_done'] == False) |
                (data['gluing_is_done'] == False) |
                (data['sewing_is_done'] == False) |
                (data['packing_is_done'] == False)
                ].empty

            if has_active_records or st.session_state[self.SHOW_DONE_STATE] is True:
                # В active_mode хранится название для переменной session_state,
                # в которой булево значение "Показывать/Не показывать таблицу".
                # Тут происходит инициализация переменной. По умолчанию show_table = False
                active_mode = f"{file}_active_mode"
                if active_mode not in st.session_state:
                    st.session_state[active_mode] = False
                # Аналогично и для...
                full_mode = f"{file}_full_mode"
                if full_mode not in st.session_state:
                    st.session_state[full_mode] = False

                with st.expander(f'{file.name}'):
                    if st.session_state[active_mode]:
                        st.error('''##### Режим редактирования. Изменения других не сохраняются.''', icon="🚧")
                        editor, original_data = self.tasks_editor(file)
                        show_and_hide_button(self.TASK_STATE, active_mode, editor, original_data, file)
                    else:
                        show_and_hide_button(self.TASK_STATE, active_mode, file_path=file)
                        self.tasks_table(file)

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
        show_and_hide_button(Page.EMPLOYEE_STATE, Page.EMPLOYEE_ACTIVE_MODE)

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
        if st.session_state[Page.EMPLOYEE_ACTIVE_MODE]:
            Page.employees_editor(True)
        else:
            Page.employees_editor()

    with col2:
        pass
