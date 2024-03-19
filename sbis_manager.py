import base64
from datetime import datetime
import json
import requests
import logging
from os import getenv
from dotenv import load_dotenv

load_dotenv()

console_out = logging.StreamHandler()
file_log = logging.FileHandler(f"application.log", mode="w")
logging.basicConfig(handlers=(file_log, console_out), level=logging.DEBUG,
                    format='[%(asctime)s | %(levelname)s]: %(message)s',
                    encoding='utf-8')

reglament_id_list = {'implementation': "ab1e34b3-6ce0-4235-838a-26680ed0b74d",
                     'order_delivery': "2c36b133-7a8a-4f69-82a6-89409c38a373",
                     'order_craft': "40749c15-7c3a-4c31-a258-f36185562c1a"}

XML_FILEPATH = 'implementation.xml'
DOCX_FILEPATH = 'order.docx'


class SABYAccessDenied(Exception):
    pass


class SBISApiManager:
    def __init__(self, login: str = '', password: str = ''):
        self.login = login
        self.password = password
        self.base_url = 'https://api.sbis.ru/retail'
        self.headers = {'X-SBISAccessToken': ''}

    def service_auth(self):
        payload = {"app_client_id": getenv('sbis.app_client_id'),
                   "app_secret": getenv('sbis.app_secret'),
                   "secret_key": getenv('sbis.secret_key')}
        response = requests.post(f'https://online.sbis.ru/oauth/service/', json=payload)
        response.encoding = 'utf-8'
        result = json.loads(response.text)

        sid = result['sid']
        with open(f"{self.login}_sbis_service_sid.txt", "w+") as file:
            file.write(sid)

        token = result['token']
        with open(f"{self.login}_sbis__service_token.txt", "w+") as file:
            file.write(token)

        return sid, token

    def get_tokens(self):
        try:
            with open(f"{self.login}_sbis_sid.txt", "r") as file:
                sid = file.read()
            with open(f"{self.login}_sbis_token.txt", "r") as file:
                token = file.read()
            return sid, token
        except FileNotFoundError:
            try:
                return self.service_auth()
            except Exception:
                logging.critical(f"Не удалось авторизоваться в СБИС.", exc_info=True)

    def main_query(self, method: str, params: dict or str):
        sid, token = self.get_tokens()
        self.headers['X-SBISAccessToken'] = token

        url = f'{self.base_url}{method}'
        res = requests.get(url, headers=self.headers, params=params)

        logging.info(f'Method: {method} | Code: {res.status_code}')
        logging.debug(f'URL: {url}\n'
                      f'Headers: {self.headers}\n'
                      f'Parameters: {params}\n'
                      f'Result: {json.loads(res.text)}')

        match res.status_code:
            case 200:
                return json.loads(res.text)
            case 401:
                logging.info('Требуется обновление токена.')
                sid, token = self.service_auth()
                self.headers['X-SBISAccessToken'] = token
                res = requests.get(f'{self.base_url}' + method, headers=self.headers, params=params)
                return json.loads(res.text)
            case 500:
                raise AttributeError(f'{method}: Check debug logs.')


class SBISWebApp(SBISApiManager):
    def __init__(self, login: str, password: str, sale_point_name: str, price_list_name: str):
        super().__init__(login, password)
        self.reg_id = reglament_id_list
        self.sale_point_name = sale_point_name
        self.price_list_name = price_list_name
        self.articles_list = self.get_articles()

    def get_sale_point_id(self):
        res = self.main_query('/point/list?', {'withPrices': 'true'})
        for point in res['salesPoints']:
            if point['name'] == self.sale_point_name:  # 'Гаспарян Роман Славикович, ИП':
                return point['id']

    def get_price_list_id(self, point_id: str):
        params = {'pointId': point_id,
                  'actualDate': '2024-03-18'}
        res = self.main_query('/nomenclature/price-list?', params)
        for list in res['priceLists']:
            if list['name'] == self.price_list_name:
                return list['id']

    def get_nomenclature_list(self, point_id: str, price_list_id: str):
        params = {'pointId': point_id,
                  'priceListId': price_list_id}
        return self.main_query('/nomenclature/list?', params)

    def get_articles(self):
        articles_list = dict()
        point_id = self.get_sale_point_id()
        price_list_id = self.get_price_list_id(point_id)
        product_list = self.get_nomenclature_list(point_id, price_list_id)
        for product in product_list['nomenclatures']:
            if product['nomNumber']:
                name = product['name']
                code = product['nomNumber']
                description = product['description_simple']
                attributes = product['attributes']
                price = product['cost']

                articles_list[name] = {'code': code,
                                       'price': price,
                                       'description': description,
                                       'attributes': attributes}
        self.articles_list = articles_list
        return articles_list

    def write_implementation(self, order_data: dict):
        base64_file = ''
        with (open(XML_FILEPATH, 'w') as file):
            today = datetime.today().strftime('%d.%m.%Y')
            delivery_date_str = order_data.get('delivery_date', None)
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
            customer_info = json.loads(order_data.get('party_data_json', '{}'))
            customer_inn = customer_info.get('data', {}).get('inn', None)
            customer_kpp = customer_info.get('data', {}).get('kpp', None)
            order_address = customer_info.get('address_data', {}).get('value', None)
            customer_name = order_data.get('party', None)
            comment = order_data.get('comment', None)
            order_contact = order_data.get('contact', None)
            full_price = round(float(order_data.get('price', None)), 2)
            prepayment = round(float(order_data.get('prepayment', None)), 2)
            amount_to_receive = round(float(order_data.get('amount_to_receive', None)), 2)

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
                        <СвЮЛ ИННЮЛ="{customer_inn}" КПП="{customer_kpp}", НаимОрг="{customer_name}"/>
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
                        <СвЮЛ ИННЮЛ="2311230064" КПП="231001001" НаимОрг="{customer_name}"/>
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
            items = order_data.get('positionsData')
            if type(items) is dict:
                items = [items]
            for item_name in items:
                info = self.articles_list[item_name]
                code = info.get("code")
                attributes = info.get('attributes')
                quantity = int(item_name.get('quantity', '1'))
                total_quantity += quantity
                file.write(f'''
                    <СвТов КодТов="{code}" НаимТов="{item_name}" НаимЕдИзм="шт" НалСт="без НДС" НеттоПередано="{quantity}" НомТов="{item_num}" ОКЕИ_Тов="796" СтБезНДС="{full_price}" СтУчНДС="{full_price}" Цена="{full_price}">
                      <ИнфПолФХЖ2 Значен="{code}" Идентиф="КодПоставщика"/>
                      <ИнфПолФХЖ2 Значен="{item_name}" Идентиф="НазваниеПоставщика"/>
                      <ИнфПолФХЖ2 Значен="{attributes}" Идентиф="ХарактНоменклатуры"/>
                      <ИнфПолФХЖ2 Значен="41-01" Идентиф="СчетУчета"/>
                    </СвТов>''')
                item_num += 1

            file.write(f'''
                    <Всего НеттоВс="{total_quantity}" СтБезНДСВс="{full_price}" СтУчНДСВс="{full_price}"/>
                  </СодФХЖ2>
                </СвДокПТПрКроме>
                <СодФХЖ3 СодОпер="Перечисленные в документе ценности переданы"/>
                </Документ>
                
                </Файл>''')

        with open(XML_FILEPATH, "rb") as file:
            encoded_string = base64.b64encode(file.read())
            base64_file = encoded_string.decode('ascii')

        params = {"Документ": {
            "Тип": "ДокОтгрИсх",
            "Вложение": [{'Файл': {'Имя': XML_FILEPATH, 'ДвоичныеДанные': base64_file}}],
            "Регламент": {"Идентификатор": self.reg_id['implementation']},
            "Примечание": f'Нужно получить: {amount_to_receive} у {order_contact}',
            "Ответственный": 'Харьковский Александр Максимович'}}

        return self.main_query('СБИС.ЗаписатьДокумент', params)

    def write_order(self):
        with open(DOCX_FILEPATH, "rb") as file:
            encoded_string = base64.b64encode(file.read())
            base64_file = encoded_string.decode('ascii')

        params = {"Документ": {
            "Тип": "Наряд",
            "Вложение": [{'Файл': {'Имя': DOCX_FILEPATH, 'ДвоичныеДанные': base64_file}}],
            "Регламент": {"Идентификатор": self.reg_id['order_craft']},
            "Примечание": 'ТЕСТ НАРЯДА НА МАТРАЦ',
            "Ответственный": 'Харьковский Александр Максимович'}}

        return self.main_query('СБИС.ЗаписатьДокумент', params)


if __name__ == '__main__':
    LOGIN = 'ХарьковскийАМ'
    PASSWORD = 'rx7SiNZtAb'
    SALE_POINT_NAME = 'Кесиян Давид Арсенович, ИП'
    PRICE_LIST_NAME = 'Тестовые матрацы'
    sbis = SBISWebApp(LOGIN, PASSWORD, PRICE_LIST_NAME, SALE_POINT_NAME)
