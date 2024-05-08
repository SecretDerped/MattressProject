import re

import pandas
import tomli


def load_conf(path: str = "app_config.toml"):
    with open(path, "rb") as f:
        return tomli.load(f)


config = load_conf()


def save_to_file(data: pandas.DataFrame, filepath: str):
    data.to_pickle(filepath)


def read_file(filepath: str) -> pandas.DataFrame:
    return pandas.read_pickle(filepath)


def get_size_int(string):
    # Шаблон регулярного выражения для поиска двух или трех чисел, разделенных любым символом
    pattern = r'(\d+)(?:\D+(\d+))?(?:\D+(\d+))?'

    # Поиск соответствий в строке
    match = re.search(pattern, string)

    if not match:
        return None

    # Извлечение чисел из соответствия
    length = int(match.group(1))
    width = int(match.group(2)) if match.group(2) else None
    height = int(match.group(3)) if match.group(3) else None
    return {'length': length, 'width': width, 'height': height}


def side_eval(size, fabric_type: str = None) -> str:
    try:
        result = (size.get('length', 0) * 2 + size.get('width', 0) * 2)
        corrections = config.get('fabric_corrections', {'Жаккард': -10, 'Трикотаж': -5})
        # TODO: поменять значения

        match corrections.get(fabric_type, 0):
            case value:
                result += value

        return str(result)

    except Exception:
        return "Ошибка в размере"


if __name__ == "__main__":
    # Пример использования
    input_string_1 = "Размеры: 10x20 см"
    input_string_2 = "20 10"
    dimensions_1 = get_size_int(input_string_1)
    dimensions_2 = get_size_int(input_string_2)
    print(dimensions_1)  # Вывод: {'length': 10, 'width': 20, 'height': None}
    print(dimensions_2)  # Вывод: {'length': 10, 'width': 20, 'height': 30}
