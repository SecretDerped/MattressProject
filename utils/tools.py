import re

import pandas
import tomli


def load_conf(path: str = "app_config.toml"):
    with open(path, "rb") as f:
        return tomli.load(f)


config = load_conf()
cash_filepath = config.get('site').get('cash_filepath')


def save_to_file(data: pandas.DataFrame, filepath: str):
    data.to_pickle(filepath)


def read_file(filepath: str) -> pandas.DataFrame:
    return pandas.read_pickle(filepath)


def get_cash_rows_without(column_to_hide: str = '', ):
    data = read_file(cash_filepath)
    if column_to_hide != '':
        tasks_todo = data[data[column_to_hide] == False]
    else:
        tasks_todo = data
    sorted_tasks = tasks_todo.sort_values(by=['high_priority', 'deadline', 'delivery_type', 'comment'],
                                          ascending=[False, True, True, False])
    return sorted_tasks


def append_to_dataframe(data: dict, filepath: str):
    """
    Принимает словарь task_data. Берёт оттуда значения без ключей
    и формирует запись в конце указанного датафрейма.
    """
    df = read_file(filepath)
    row = []
    for k in data.values():
        row.append(k)
    print(row)
    df.loc[len(df.index)] = row
    save_to_file(df, filepath)


def get_size_int(string):
    """
    Принимает строку с размером матраса типа "180х200".
    Ищет первые два или три числа, разделенных любым символом.
    Если не находит число, ставит 0.
    Возвращает словарь с размерами:
    {'length': 180,
    'width': 200,
    'height': 0}
    """

    pattern = r'(\d+)(?:\D+(\d+))?(?:\D+(\d+))?'

    match = re.search(pattern, string)
    if not match:
        return {'length': 0, 'width': 0, 'height': 0}

    length = int(match.group(1))
    width = int(match.group(2)) if match.group(2) else 0
    height = int(match.group(3)) if match.group(3) else 0
    return {'length': length, 'width': width, 'height': height}


def side_eval(size, fabric_type: str = None) -> str:
    """
    Вычисляет сколько нужно отрезать боковины, используя размер из функции get_size_int.
   Формула для вычисления размера боковины: (Длина * 2 + Ширина * 2) + корректировка
   В зависимости от типа ткани корректировка прописывается в app_config.toml,
   в разделе [fabric_corrections]
   """

    try:
        result = (size.get('length', 0) * 2 + size.get('width', 0) * 2)
        corrections = config.get('fabric_corrections', {'Текстиль': 0})

        match corrections.get(fabric_type, 0):
            case value:
                result += value

        return str(result)

    except Exception:
        return "Ошибка в вычислении размера"


def get_date_str(dataframe_row: pandas.Series) -> str:
    """
    Принимает дату из датафрейма и преобразует в строку: 08 мая, среда
    """
    date = pandas.to_datetime(dataframe_row).strftime('%d.%m.%A')
    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    day, month, weekday = date.split('.')
    return f'{day} {months[int(month) - 1]}, {weekday}'


# TODO: актуализировать сообщение в телеграм
def create_message_str(data):
    positions_data = data['positionsData']
    positions_str = "\n".join([f"{item['article']} - {item['quantity']} шт." for item in positions_data])
    order_message = (f"""НОВАЯ ЗАЯВКА

Позиции:
{positions_str}

Дата доставки:
{data['delivery_date']}

Адрес:
{data['delivery_address']}

Магазин:
{data['party']}

Цена: {data['price']}
Предоплата: {data['prepayment']}
Нужно получить: {data['amount_to_receive']}""")
    if data['comment'] != '':
        order_message += f"\n\nКомментарий: {data['comment']}"
        return order_message


if __name__ == "__main__":
    # Пример использования
    input_string_1 = "Размеры: 10x20 см"
    input_string_2 = "20 10"
    dimensions_1 = get_size_int(input_string_1)
    dimensions_2 = get_size_int(input_string_2)
    print(dimensions_1)  # Вывод: {'length': 10, 'width': 20, 'height': None}
    print(dimensions_2)  # Вывод: {'length': 10, 'width': 20, 'height': 30}
