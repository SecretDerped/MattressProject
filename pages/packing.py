import os
import time

from openpyxl.reader.excel import load_workbook

from utils.app_core import ManufacturePage
from utils.tools import config, save_to_file, time_now, print_file, get_date_str
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
                f"**Топ:** {row['base_fabric']}  \n"
                f"**Бок:** {row['side_fabric']}  \n"
                f"**ПБ:** {row['springs']}  \n")

    def packing_tasks(self, file):
        data = super().load_tasks(file)
        # Фильтруем наряды. Показываются те, что не пошиты,
        # но на которые нарезали ткань и собрали основу.
        # Не меняй "==" на "is" по стандарту PEP 8, иначе фильтр не будет работать.
        return data[(data['packing_is_done'] == False) &
                    (data['sewing_is_done'] == True)]

    def talon_button(self, file, row, index):
        document = f'{self.page_name}_talon_{index}.xlsx'
        # Кнопка для печати талона

        if st.button(label=f":blue[**{self.talon_button_text}**]", key=f"{file}_{document}"):
            template_path = 'static/guarantee.xlsx'
            wb = load_workbook(template_path)
            ws = wb.active

            # Заполнение шаблона
            ws['B4'] = "Матрас АРТ.№ " + row['article'] + '  |  ПБ: ' + row['springs']

            ws['B6'] = row['size']

            ws['B8'] = row['deadline'].strftime('%d.%m.%Y')

            ws['B16'] = f"{row['organization']}  {row['address']}" if row['address'] else 'Краснодар, ул. Демуса 6А'

            document_path = fr'cash\{document}'
            wb.save(document_path)
            print_file(document_path, self.default_printer_name)
            st.toast("Сейчас распечатается талон...", icon='🖨️')
            time.sleep(1)
            try:
                os.remove(document_path)
            except Exception:
                time.sleep(0.5)

    def label_button(self, file, row, index):
        article = row['article']
        if st.button(label=f":orange[**{self.label_button_text}**]", key=f"{file}_{article}_{index}"):
            try:
                file_path = fr"static\labels\{article}.pdf"
                print_file(file_path, self.label_printer_name)
                st.toast("Печать этикетки...", icon='🖨️')
            except FileNotFoundError:
                st.toast("Ошибка печати. Шаблон для этикетки не найден.", icon='❗')
                #print_file("static\labels\800.pdf")
            except Exception as e:
                st.toast(f"Ошибка печати: {e}")

    def _form_box_text(self, row):
        # Текст контейнера красится в красный, когда у наряда приоритет
        text_color = 'red' if row['high_priority'] else 'gray'

        box_text = f':{text_color}[{self.inner_box_text(row)}'

        if row['comment']:
            box_text += f"**Комментарий**: {row['comment']}  "

        box_text += ']'
        return box_text

    def show_tasks_tiles(self, data, file, stage_to_done: str, num_columns: int = 3) -> bool:
        """Принимает отфильтрованные данные. Выводит заявки в виде плиточек на страницу.
        Отфильтрованные данные выводятся, а потом, при нажатии "Готово" на заявке, по
        индексу изменения соотносятся с главным хранилищем и записываются"""
        page = self.page_name
        main_data = super().load_tasks(file)

        if len(data) == 0:
            return st.header('Все заявки выполнены! Хорошая работа 🏖️')

        row_container = st.columns(num_columns)
        count = 0
        for index, row in data.iterrows():
            if count % num_columns == 0:
                row_container = st.columns(num_columns)

            box = row_container[count % num_columns].container(border=True)

            with box:
                photo = row['photo']
                if photo:
                    st.image(photo, caption='Фото', width=80)

                st.markdown(self._form_box_text(row))
                button_row_1, button_row_2, button_row_3 = st.columns([1, 1, 1])
                if page in st.session_state and st.session_state[page]:
                    employee = st.session_state[page]
                    with button_row_1:
                        if st.button(f":green[**{self.done_button_text}**]", key=f'{file}_{page}_done_{index}'):
                            history_note = f'({time_now()}) {page} [ {employee} ] -> {self.done_button_text}; \n'
                            main_data.at[index, stage_to_done] = True
                            main_data.at[index, 'history'] += history_note
                            save_to_file(main_data, file)
                            st.rerun()
                    with button_row_2:
                        self.talon_button(file, row, index)
                    with button_row_3:
                        self.label_button(file, row, index)
            count += 1
        return True

    @st.experimental_fragment(run_every="1s")
    def tiles_row(self):
        for file in self.task_cash.iterdir():
            # Папки пропускаем
            if not file.is_file():
                continue

            # Завершённые таблицы не показываем
            data = self.packing_tasks(file)
            if data.empty:
                continue

            row = data.iloc[0]
            date = get_date_str(row['deadline'])
            delivery_type = row['delivery_type']
            client = row['organization'] or row['contact']
            address = f"{row.get('address', '')}"
            region = f"{row.get('region', '')}"
            expander_text = f"{date}" if delivery_type == "Самовывоз" else f"{date} | {address}"
            if region and delivery_type != "Самовывоз":
                expander_text += f" | {region}"
            packing_title = f"#### {delivery_type}, {client}"
            st.markdown(packing_title)
            with st.expander(expander_text):
                self.show_tasks_tiles(data, file, 'packing_is_done', 4)
                st.divider()


Page = PackingPage("Упаковка", "📦")
Page.tiles_row()
