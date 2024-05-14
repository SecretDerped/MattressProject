import json
import re
from datetime import datetime

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


def append_to_dataframe(data: dict, filepath: str):
    """
    Принимает словарь task_data. Берёт оттуда значения без ключей
    и формирует запись в конце указанного датафрейма.
    """
    df = read_file(filepath)
    row = []
    for k in data.values():
        row.append(k)
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


def create_implementation_xml(nomenclature_list, data, filepath):
    today = datetime.today().strftime('%d.%m.%Y')
    delivery_date_str = data.get('delivery_date', None)
    delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
    customer_info = json.loads(data.get('party_data_json', '{}'))
    customer_inn = customer_info.get('data', {}).get('inn', None)
    customer_kpp = customer_info.get('data', {}).get('kpp', None)
    order_address = customer_info.get('address_data', {}).get('value', None)
    customer_name = data.get('party', None).replace('"', '&quot;')
    comment = data.get('comment', None).replace('"', '&quot;')
    order_contact = data.get('contact', None)
    full_price = round(float(data.get('price', None)), 2)
    prepayment = round(float(data.get('prepayment', None)), 2)
    amount_to_receive = round(float(data.get('amount_to_receive', None)), 2)
    items = data.get('positionsData', '[]')

    with (open(filepath, 'w') as file):
        file.write(f'''<?xml version="1.0" encoding="WINDOWS-1251" ?>
                    <Файл ВерсФорм="5.02">

                    <СвУчДокОбор>
                    <СвОЭДОтпр/>
                    </СвУчДокОбор>

                    <Документ ВремИнфПр="9.00.00" ДатаИнфПр="{today}" КНД="1175010" НаимЭконСубСост="ИП Кесиян Давид Арсенович">
                    <СвДокПТПрКроме>
                    <СвДокПТПр>
                    <НаимДок НаимДокОпр="Товарная накладная" ПоФактХЖ="Документ о передаче товара при торговых операциях"/>
                    <ИдентДок ДатаДокПТ="{today}"/>
                    <СодФХЖ1>
                      <ГрузОтпр ОКПО="0120807602">
                        <ИдСв>
                          <СвИП ИННФЛ="231003981502" СвГосРегИП="317237500347162">
                            <ФИО Имя="Давид" Отчество="Арсенович" Фамилия="Кесиян"/>
                          </СвИП>
                        </ИдСв>
                        <Адрес>
                          <АдрРФ Город="г. Краснодар" Дом="27" Индекс="350042" КодРегион="23" Улица="ул. Клиническая"/>
                        </Адрес>
                        <Контакт ЭлПочта="it@le-ar.ru"/>
                        <БанкРекв НомерСчета="40802810270010040929">
                          <СвБанк БИК="044525092" КорСчет="30101810645250000092" НаимБанк="Московский Филиал АО КБ &quot;Модульбанк&quot; МОСКВА"/>
                        </БанкРекв>
                      </ГрузОтпр>
                      <ГрузПолуч ОКПО="20524053">
                        <ИдСв>
                          <СвОрг>
                            <СвЮЛ ИННЮЛ="{customer_inn}" КПП="{customer_kpp}" НаимОрг="{customer_name}"/>
                          </СвОрг>
                        </ИдСв>
                        <Адрес>
                          <АдрИнф АдрТекст="{order_address}" КодСтр="643"/>
                        </Адрес>
                        </ГрузПолуч>
                      <Продавец ОКПО="0120807602">
                        <ИдСв>
                          <СвИП ИННФЛ="231003981502" СвГосРегИП="317237500347162">
                            <ФИО Имя="Давид" Отчество="Арсенович" Фамилия="Кесиян"/>
                          </СвИП>
                        </ИдСв>
                        <Адрес>
                          <АдрРФ Город="г. Краснодар" Дом="27" Индекс="350042" КодРегион="23" Улица="ул. Клиническая"/>
                        </Адрес>
                        <Контакт ЭлПочта="it@le-ar.ru"/>
                        <БанкРекв НомерСчета="40802810270010040929">
                          <СвБанк БИК="044525092" КорСчет="30101810645250000092" НаимБанк="Московский Филиал АО КБ &quot;Модульбанк&quot; МОСКВА"/>
                        </БанкРекв>
                      </Продавец>
                      <Покупатель ОКПО="20524053">
                        <ИдСв>
                          <СвОрг>
                            <СвЮЛ ИННЮЛ="{customer_inn}" КПП="{customer_kpp}" НаимОрг="{customer_name}"/>
                          </СвОрг>
                        </ИдСв>
                        <Адрес>
                          <АдрИнф АдрТекст="{order_address}" КодСтр="643"/>
                        </Адрес>
                        <Контакт Тлф="8 (861) 204-05-06" ЭлПочта="dir@le-ar.ru"/>
                        <БанкРекв НомерСчета="40702810512550035771">
                          <СвБанк БИК="044525360" КорСчет="30101810445250000360" НаимБанк="Филиал &quot;Корпоративный&quot; ПАО &quot;Совкомбанк&quot; МОСКВА"/>
                        </БанкРекв>
                      </Покупатель>
                      <Основание НаимОсн="-"/>
                      <ИнфПолФХЖ1>
                        <ТекстИнф Значен="{comment}" Идентиф="Примечание"/>
                        <ТекстИнф Значен="{comment}" Идентиф="ИнфПередТабл"/>
                        <ТекстИнф Значен="{delivery_date}" Идентиф="Срок"/>
                        <ТекстИнф Значен="23:59:59" Идентиф="СрокВремя"/>
                        <ТекстИнф Значен="Основной склад" Идентиф="СкладНаименование"/>
                        <ТекстИнф Значен="ИП Кесиян Давид Арсенович" Идентиф="НаимПост"/>
                        <ТекстИнф Значен="ИП Кесиян Давид Арсенович" Идентиф="НаимГрузОтпр"/>
                      </ИнфПолФХЖ1>
                    </СодФХЖ1>
                  </СвДокПТПр>
                  <СодФХЖ2>''')
        item_num = 1
        total_quantity = 0

        for item in items:
            item_name = item['article'].replace('"', '&quot;')
            quantity = int(item.get('quantity', '1'))
            total_quantity += quantity
            info = nomenclature_list[item['article']]
            code = info.get("code")
            price = info.get('price')
            file.write(f'''
                        <СвТов КодТов="{code}" НаимТов="{item_name}" НаимЕдИзм="шт" НалСт="без НДС" НеттоПередано="{quantity}" НомТов="{item_num}" ОКЕИ_Тов="796" СтБезНДС="{price}" СтУчНДС="{price}" Цена="{price}">
                          <ИнфПолФХЖ2 Значен="{code}" Идентиф="КодПоставщика"/>
                          <ИнфПолФХЖ2 Значен="{item_name}" Идентиф="НазваниеПоставщика"/>
                          <ИнфПолФХЖ2 Значен="&quot;Type&quot;:&quot;Товар&quot;" Идентиф="ПоляНоменклатуры"/>
                          <ИнфПолФХЖ2 Значен="41-01" Идентиф="СчетУчета"/>
                        </СвТов>''')
            item_num += 1

        file.write(f'''
            <Всего НеттоВс="{total_quantity}" СтБезНДСВс="{full_price}" СтУчНДСВс="{full_price}"/>
          </СодФХЖ2>
        </СвДокПТПрКроме>
        <СодФХЖ3 СодОпер="Перечисленные в документе ценности переданы"/>
        <Подписант ОблПолн="2"/>
      </Документ>

    </Файл>''')


if __name__ == "__main__":
    # Пример использования
    input_string_1 = "Размеры: 10x20 см"
    input_string_2 = "20 10"
    dimensions_1 = get_size_int(input_string_1)
    dimensions_2 = get_size_int(input_string_2)
    print(dimensions_1)  # Вывод: {'length': 10, 'width': 20, 'height': None}
    print(dimensions_2)  # Вывод: {'length': 10, 'width': 20, 'height': 30}
