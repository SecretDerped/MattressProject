import os
import time

from openpyxl.reader.excel import load_workbook

from utils.app_core import ManufacturePage
from utils.tools import get_date_str, config, save_to_file, time_now, print_file
import streamlit as st


class PackingPage(ManufacturePage):
    def __init__(self, name, icon):
        super().__init__(name, icon)
        self.talon_button_text = 'Талон'
        self.label_button_text = 'Этикетка'
        self.default_printer_name = config.get('site').get('hardware').get('default_printer')
        self.label_printer_name = config.get('site').get('hardware').get('label_printer')

    @staticmethod
    def inner_box_text(row):
        return (f"**Артикул:** {row['article']}  \n"
                f"**Размер**: {row['size']}  \n"
                f"**Тип доставки:** {row['delivery_type']}  \n"
                f"**Адрес:** {row['address']}  \n"
                f"**Клиент:** {row.get('client')}  \n"
                f"**Срок:** {get_date_str(row.get('deadline'))}  \n")

    def packing_tasks(self):
        data = super().load_tasks()
        # Фильтруем наряды. Показываются те, что не пошиты,
        # но на которые нарезали ткань и собрали основу.
        # Не меняй "==" на "is" по стандарту PEP 8, иначе фильтр не будет работать.
        return data[(data['packing_is_done'] == False) &
                    (data['sewing_is_done'] == True)]

    def talon_button(self, row, index):
        file_name = f'{self.page_name}_talon_{index}.xlsx'
        # Кнопка для печати талона

        if st.button(label=f":blue[**{self.talon_button_text}**]", key=file_name):
            template_path = 'static/guarantee.xlsx'
            wb = load_workbook(template_path)
            ws = wb.active

            # Заполнение шаблона
            ws['B4'] = "Матрас АРТ.№ " + row['article'] + '  |  ПБ: ' + row['springs']

            ws['B6'] = row['size']

            ws['B8'] = row['deadline'].strftime('%d.%m.%Y')

            ws['B16'] = f"{row['client']}  {row['address']}" if row['address'] else 'Краснодар, ул. Демуса 6А'

            file_path = fr'cash\{file_name}'
            wb.save(file_path)
            print_file(file_path, self.default_printer_name)
            st.toast("Сейчас распечатается талон...", icon='🖨️')
            time.sleep(1)
            try:
                os.remove(file_path)
            except Exception:
                time.sleep(0.5)

    def label_button(self, row, index):
        article = row['article']
        if st.button(label=f":orange[**{self.label_button_text}**]", key=f"{article}_{index}"):
            try:
                file_path = fr"static\labels\{article}.pdf"
                print_file(file_path, self.label_printer_name)
            except Exception:
                print_file("static\labels\800.pdf")

    def _form_box_text(self, row):
        # Текст контейнера красится в красный, когда у наряда приоритет
        text_color = 'red' if row['high_priority'] else 'gray'

        box_text = f':{text_color}[{self.inner_box_text(row)}'

        if row['comment']:
            box_text += f"**Комментарий**: {row['comment']}  "

        box_text += ']'
        return box_text

    def show_tasks_tiles(self, data, stage_to_done: str, num_columns: int = 3) -> bool:
        """Принимает отфильтрованные данные. Выводит заявки в виде плиточек на страницу.
        Отфильтрованные данные выводятся, а потом, при нажатии "Готово" на заявке, по
        индексу изменения соотносятся с главным хранилищем и записываются"""
        main_data = super().load_tasks()
        page = self.page_name

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
                    st.markdown(self._form_box_text(row))
                with col3:
                    if page in st.session_state and st.session_state[page]:
                        employee = st.session_state[page]

                        if st.button(f":green[**{self.done_button_text}**]", key=f'{page}_done_{index}'):
                            history_note = f'({time_now()}) {page} [ {employee} ] -> {self.done_button_text}; \n'
                            main_data.at[index, stage_to_done] = True
                            main_data.at[index, 'history'] += history_note
                            save_to_file(main_data, self.task_cash)
                            st.rerun()

                        self.talon_button(row, index)
                        self.label_button(row, index)
            count += 1
        return True

    @st.experimental_fragment(run_every="1s")
    def packing_tiles(self):
        self.show_tasks_tiles(self.packing_tasks(), 'packing_is_done', 3)


Page = PackingPage("Упаковка", "📦")
Page.packing_tiles()
