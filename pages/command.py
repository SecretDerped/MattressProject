import streamlit as st

from utils.app_core import Page
from utils.tools import clear_cash, read_file, cashing, \
    get_cash, save_to_file, barcode_link


def show_and_hide_button(table_state, show_state):
    # Кнопка для отображения/скрытия таблицы с изменением текста
    if not st.session_state[show_state]:
        button_text = '**Перейти в режим редактирования**'
    else:
        button_text = ":red[**Сохранить и вернуть режим просмотра**]"

    if st.button(button_text, key=f'{table_state}_mode_button'):
        # Очистить данные, если таблица скрывается
        clear_cash(table_state)
        st.session_state[show_state] = not st.session_state[show_state]
        st.rerun()


class BrigadierPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)

        self.TASK_STATE = 'task_dataframe'
        self.EMPLOYEE_STATE = 'employee_dataframe'

        self.TASK_ACTIVE_MODE = 'task_active_mode'
        self.TASK_FULL_MODE = 'task_full_mode'
        self.EMPLOYEE_ACTIVE_MODE = 'employee_active_mode'

        # В TASK_ACTIVE_MODE хранится название для переменной session_state,
        # в которой булево значение "Показывать/Не показывать таблицу".
        # Тут происходит инициализация переменной. По умолчанию show_table = False
        if self.TASK_ACTIVE_MODE not in st.session_state:
            st.session_state[self.TASK_ACTIVE_MODE] = False
            # Аналогично и для...
        if self.TASK_FULL_MODE not in st.session_state:
            st.session_state[self.TASK_FULL_MODE] = False

        if self.EMPLOYEE_ACTIVE_MODE not in st.session_state:
            st.session_state[self.EMPLOYEE_ACTIVE_MODE] = False

    @st.experimental_fragment(run_every="1s")
    def tasks_table(self):
        """Показывает нередактируемую таблицу данных без индексов."""
        columns = self.tasks_columns_config
        data = read_file(self.task_cash)

        # Так сделано, чтобы настройка была только тут, чтобы
        # нельзя было менять таблицу во время режима редактирования
        if st.checkbox('Показывать завершённые наряды'):
            st.session_state[Page.TASK_FULL_MODE] = True
        else:
            st.session_state[Page.TASK_FULL_MODE] = False

        if not st.session_state[self.TASK_FULL_MODE]:
            data = data[(data['fabric_is_done'] == False) |
                        (data['gluing_is_done'] == False) |
                        (data['sewing_is_done'] == False) |
                        (data['packing_is_done'] == False)]

        st.dataframe(data=data,
                     column_config=columns,
                     column_order=(column for column in columns.keys()),
                     hide_index=True)

    def tasks_editor(self):
        """База данных в этом проекте представляет собой файл pkl с датафреймом библиотеки pandas.
        Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
        а кэш пишется в session_state текущего состояния таблицы. Каждое изменение таблицы
        провоцируют on_change методы, а потом обновление всей страницы. Поэтому система
        такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
        Как только какое-то поле было изменено, то изменения записываются в кэш,
        потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями
        сохраняется в базу."""
        state = self.TASK_STATE
        columns = self.tasks_columns_config

        try:
            # Если функция редактирования не открывалась, значит нет кэша.
            # Грузим данные из базы и копируем в кэш.
            if state not in st.session_state:
                data = read_file(self.task_cash)
                cashing(data, state)
            # Если функция была открыта, значит после изменения на странице остался кэш,
            # то есть загружаем данные из кэша.
            else:
                data = get_cash(state)

            # Стейт галочки "Показать все наряды". Декларирована вне объекта там, внизу
            if st.session_state[self.TASK_FULL_MODE]:
                filtered_df = data
            else:
                filtered_df = data[(data['fabric_is_done'] == False) |
                                   (data['gluing_is_done'] == False) |
                                   (data['sewing_is_done'] == False) |
                                   (data['packing_is_done'] == False)]

            editor = st.data_editor(
                data=filtered_df,
                column_config=columns,
                column_order=(column for column in columns.keys()),  # Порядок получается такой же, как в конфиге колонн
                hide_index=True,
                num_rows="fixed",
                on_change=self.update_cache_and_save, args=(data, filtered_df, state),
                key=f"{state}_editor",
                height=420
            )

        except RuntimeError:
            st.rerun()

    def update_cache_and_save(self, cached_df, edited_df, state):
        """Обновляет кэш и сохраняет изменения в базу данных."""
        for index, row in edited_df.iterrows():
            cached_df.loc[index] = row
        cashing(cached_df, state)
        save_to_file(cached_df, self.task_cash)

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

        show_and_hide_button(Page.TASK_STATE, Page.TASK_ACTIVE_MODE)

    with col2:
        st.write(' ')

        # Отображение подсказки в зависимости от состояния
        if st.session_state[Page.TASK_ACTIVE_MODE]:
            st.error('''##### Внимание, включён режим редактирования.  
            \nПока он активен, изменения других рабочих не сохраняются!''', icon="🚧")
        else:
            st.info('''На этом экране показываются данные о нарядах в режиме реального времени. Чтобы поправить любой
            наряд, включите режим редактирования. Он обладает высшим приоритетом - пока активен режим редактирования,
            изменения других рабочих не сохраняются. **Не забывайте сохранять таблицу!**''', icon="ℹ️")

    # Отображение таблицы в зависимости от состояния
    if st.session_state[Page.TASK_ACTIVE_MODE]:
        Page.tasks_editor()
    else:
        Page.tasks_table()

with employee_tab:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("👷 Сотрудники")
        show_and_hide_button(Page.EMPLOYEE_STATE, Page.EMPLOYEE_ACTIVE_MODE)

    with col2:
        st.info('Выставляйте рабочих на смену. Они будут активны при выборе ответственного на нужном экране. В поле'
                '"Роли" пропишите рабочее место сотруднику. Можно вписать несколько.  \n'
                'Доступно: сборка основы, нарезка ткани, швейный стол, упаковка',
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
