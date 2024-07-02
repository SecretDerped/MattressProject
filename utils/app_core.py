import pandas
import streamlit as st

from utils.tools import config, employee_choose, read_file, side_eval, get_date_str, is_reserved, get_reserver, \
    set_reserver, set_reserved, save_to_file, time_now


class Page:
    def __init__(self, name, icon):
        self.name = name
        self.icon = icon

        self.cash = config.get('site').get('cash_filepath')

        self.reserve_button_text = 'Взять'
        self.done_button_text = 'Готово'

        st.set_page_config(page_title=self.name,
                           page_icon=self.icon,
                           layout="wide")
        self.header()

    def header(self):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f'{self.icon} {self.name}')
        with col2:
            employee_choose(self.name)


class ManufacturePage(Page):
    def __init__(self, name, icon):
        super().__init__(name, icon)

    def load_tasks(self):
        data = read_file(self.cash)
        return data.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                ascending=[False, True, True, False])

    @staticmethod
    def inner_box_text(row):
        """Метод, выдающий текст внутри бокса. Для каждой страницы с плитками заявок можно переопределять этот метод."""
        return (f"**Артикул:** {row.get('article')}  \n"
                f"**Ткань**: {row.get('base_fabric')}  \n"
                f"**Тип доставки**: {row.get('delivery_type')}  \n"
                f"**Адрес:** {row.get('address')}  \n"
                f"**Клиент:** {row.get('client')}  \n"
                f"**Верх/Низ**: {row.get('base_fabric')}  \n"
                f"**Бочина**: {row.get('side_fabric')}  \n"
                f"**Состав:** {row.get('attributes')}  \n"
                f"**Размер:** {row.get('size')} ({side_eval(row.get('size'), row.get('side_fabric'))}  \n"
                f"**Срок**: {get_date_str(row.get('deadline'))}  \n")

    def _form_box_text(self, index, row):
        # Текст контейнера красится в красный, когда у наряда приоритет
        text_color = 'red' if row['high_priority'] else 'gray'
        box_text = ''

        # Проверка на бронирование
        if is_reserved(self.name, index):
            reserver = get_reserver(self.name, index)
            box_text += f":orange[**Взято - {reserver}**]  \n"
        box_text += f':{text_color}[{self.inner_box_text(row)}'
        if row['comment']:
            box_text += f"**Комментарий**: {row['comment']}  "

        box_text += ']'
        return box_text

    @st.experimental_fragment(run_every="1s")
    def show_tasks_tiles(self, data: pandas.DataFrame, stage_to_done: str, num_columns: int = 3) -> bool:

        if len(data) == 0:
            return st.header('Все заявки выполнены! Хорошая работа 🏖️')

        row_container = st.columns(num_columns)
        count = 0
        for index, row in data.iterrows():

            if count % num_columns == 0:
                row_container = st.columns(num_columns)

            box = row_container[count % num_columns].container(height=250, border=True)

            with box:
                photo = row['photo']
                if photo:
                    col1, col2, buff, col3 = st.columns([12, 3, 1, 6])
                    col2.image(photo, caption='Фото', width=80)
                else:
                    col1, col3 = st.columns([3, 1])

                with col1:
                    st.markdown(self._form_box_text(index, row))
                with col3:
                    st.title('')
                    st.subheader('')
                    if self.name in st.session_state and st.session_state[self.name]:
                        if is_reserved(self.name, index):
                            if st.button(f":green[**{self.done_button_text}**]", key=f'{self.name}_done_{index}'):
                                data.at[index, stage_to_done] = True
                                employee = st.session_state[self.name]
                                history_note = f'({time_now()}) {self.name} [ {employee} ] -> {self.done_button_text}; \n'
                                data.at[index, 'history'] += history_note
                                save_to_file(data, self.cash)
                                st.rerun()
                        else:
                            if st.button(f":blue[**{self.reserve_button_text}**]",
                                         key=f'{self.name}_reserve_{index}'):
                                employee = st.session_state[self.name]
                                history_note = f'({time_now()}) {self.name} [ {employee} ] -> {self.reserve_button_text}; \n'
                                data.at[index, 'history'] += history_note
                                set_reserver(self.name, index, employee)
                                set_reserved(self.name, index, True)
                                save_to_file(data, self.cash)
                                st.rerun()
            count += 1
        return True
