import streamlit as st

from utils.app_core import Page
from utils.tools import clear_cash, read_file, cashing, \
    get_cash, save_to_file, barcode_link


class BrigadierPage(Page):
    def __init__(self, page_name, icon):
        super().__init__(page_name, icon)
        self.EMPLOYEE_STATE = 'employee_dataframe'
        self.TASK_STATE = 'task_dataframe'
        self.SHOW_TABLE = 'show_table'

    def show_employees_editor(self):
        # Создаёт таблицу из настроек колонн, если её нет
        if self.EMPLOYEE_STATE not in st.session_state:
            dataframe = read_file(self.employees_cash)
            # Создаётся колонка строк, где каждая ячейка формируется на основе соответсвующего индекса в датафрейме.
            # Для того чтобы это сработало, мы берём список индексов, преобразовываем в серию для чтения, применяем
            # к каждому индексу функцию, записываем полученную строку на соответсвующую позицию и сохраняем
            # datatype столбца как string. Всё это в строчке ниже
            dataframe['barcode'] = dataframe.index.to_series().apply(barcode_link).astype('string')

            cashing(dataframe, self.EMPLOYEE_STATE)

        edited_df = get_cash(self.EMPLOYEE_STATE)
        editor = st.data_editor(
            edited_df,
            column_config=self.employee_columns_config,
            hide_index=True,
            num_rows="dynamic",
            on_change=cashing, args=(edited_df, self.EMPLOYEE_STATE),
        )
        save_to_file(editor, self.employees_cash)

    def show_tasks_editor(self):
        """База данных в этом проекте представляет собой файл pkl с датафреймом библиотеки pandas.
        Кэш выступает промежуточным состоянием таблицы. Таблица стремится подгрузится из кэша,
        а кэш делается из session_state - текущего состояния таблицы. Каждое изменение таблицы
        провоцируют on_change методы, а потом обновление всей страницы. Поэтому система
        такая: если кэша нет - подгружается таблица из базы, она же копируется в кэш.
        Как только какое-то поле было изменено, то изменения записываются в кэш,
        потом страница обновляется, подгружая данные из кэша, и после новая таблица с изменениями
        сохраняется в базу."""
        if self.TASK_STATE not in st.session_state:
            dataframe = read_file(self.task_cash)
            # Со страницы создания заявки возвращаются только строки, поэтому тут
            # некоторые столбцы преобразуются в типы, читаемые для pandas.
            dataframe['deadline'].astype("datetime64[ns]")
            dataframe['created'].astype("datetime64[ns]")
            cashing(dataframe, self.TASK_STATE)

        edited_df = get_cash(self.TASK_STATE)
        editor = st.data_editor(
            edited_df,
            column_config=self.tasks_columns_config,
            hide_index=True,
            num_rows="fixed",
            on_change=cashing, args=(edited_df, self.TASK_STATE),
            height=420
        )
        save_to_file(editor, self.task_cash)

    @st.experimental_fragment(run_every="1s")
    def show_tasks_table(self):
        """Показывает нередактируемую таблицу данных без индексов."""
        st.dataframe(data=read_file(self.task_cash), column_config=self.tasks_columns_config, hide_index=True)


################################################ Page ####################################################


Page = BrigadierPage('Производственный терминал', '🛠️')

tasks_tab, employee_tab = st.tabs(['Наряды', 'Сотрудники'])

with tasks_tab:
    # В SHOW_TABLE хранится название для переменной session_state,
    # в которой булево значение "Показывать/Не показывать таблицу".
    # Тут происходит инициализация переменной. По умолчанию show_table = False
    if Page.SHOW_TABLE not in st.session_state:
        st.session_state[Page.SHOW_TABLE] = False

    col1, col2 = st.columns([1, 2])

    with col1:
        st.title("🏭 Все наряды")
        # Кнопка для отображения/скрытия таблицы с изменением текста
        button_text = '**Перейти в режим редактирования**' if not st.session_state[
            Page.SHOW_TABLE] else ":red[**Сохранить и вернуть режим просмотра**]"
        if st.button(button_text):
            # Очистить данные, если таблица скрывается
            clear_cash(Page.TASK_STATE)
            st.session_state[Page.SHOW_TABLE] = not st.session_state[Page.SHOW_TABLE]
            st.rerun()

    with col2:
        st.write(' ')
        st.info('''Чтобы поправить любой наряд, включите режим редактирования.
        Он обладает высшим приоритетом - пока активен режим редактирования,
        изменения других рабочих не сохраняются. **Не забывайте сохранять таблицу!**''', icon="ℹ️")

    # Отображение таблицы в зависимости от состояния
    if st.session_state[Page.SHOW_TABLE]:
        Page.show_tasks_editor()
    if not st.session_state[Page.SHOW_TABLE]:
        Page.show_tasks_table()

# TODO: совместный табель - история смен сотрудников
with employee_tab:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.title("👷 Сотрудники")
        st.button("Записать сотрудников")
    with col2:
        st.write(' ')
        st.info('Выставляйте рабочих на смену. Они будут активны при выборе ответственного на нужном экране. В поле'
                '"Роли" пропишите рабочее место сотруднику. Можно вписать несколько.  \n'
                'Доступно: сборка основы, нарезка ткани, швейный стол, упаковка',
                icon="ℹ️")

    col1, col2 = st.columns([2, 1])
    with col1:
        Page.show_employees_editor()
    with col2:
        pass