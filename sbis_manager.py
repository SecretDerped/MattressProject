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
logging.basicConfig(handlers=(file_log, console_out),

                    level=logging.INFO,
                    format='[%(asctime)s | %(levelname)s]: %(message)s',

                    encoding='utf-8')

reglament_id_list = {'implementation': "ab1e34b3-6ce0-4235-838a-26680ed0b74d",
                     'order_delivery': "2c36b133-7a8a-4f69-82a6-89409c38a373",
                     'task': "05999956-3a78-4f91-bb80-a08b7eceb954"}

IMP_FILEPATH = 'implementation.xml'
TASK_FILEPATH = 'task.html'


class SBISManager:
    def __init__(self, login: str = '', password: str = ''):
        self.login = login
        self.password = password
        self.base_url = 'https://online.sbis.ru'
        self.headers = {
            'Host': 'online.sbis.ru',
            'Content-Type': 'application/json-rpc; charset=utf-8',
            'Accept': 'application/json-rpc'
        }

    def auth(self):
        payload = {
            "jsonrpc": "2.0",
            "method": 'СБИС.Аутентифицировать',
            "params": {"Логин": self.login, "Пароль": self.password},
            "protocol": 2,
            "id": 0
        }
        res = requests.post(f'{self.base_url}/auth/service/', headers=self.headers, data=json.dumps(payload))
        logging.debug(f"СБИС.Аутентифицировать: {json.loads(res.text)}")

        try:
            sid = json.loads(res.text)['result']

            with open(f"{self.login}_sbis_token.txt", "w+") as file:
                file.write(sid)
            return sid

        except KeyError:
            logging.critical(f"Ошибка авторизации: {json.loads(res.text)['error']}")

    def get_sid(self):
        try:
            with open(f"{self.login}_sbis_token.txt", "r") as file:
                sid = file.read()
                return sid
        except FileNotFoundError:
            return self.auth()

    def main_query(self, method: str, params: dict or str):
        self.headers['X-SBISSessionID'] = self.get_sid()
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "protocol": 2,
            "id": 0
        }

        res = requests.post(f'{self.base_url}/service/', headers=self.headers, data=json.dumps(payload))

        logging.info(f'Method: {method} | Code: {res.status_code}')
        logging.debug(f'URL: {self.base_url}/service/ \n'
                      f'Headers: {self.headers}\n'
                      f'Parameters: {params}\n'
                      f'Result: {json.loads(res.text)}')
        try:
            match res.status_code:
                case 200:
                    return json.loads(res.text)['result']
                case 401:
                    logging.info('Пробуем обновить токен...')
                    self.headers['X-SBISSessionID'] = self.auth()
                    res = requests.post(f'{self.base_url}/service/', headers=self.headers, data=json.dumps(payload))
                    return json.loads(res.text)['result']
                case 500:
                    raise AttributeError(f"{method}: {json.loads(res.text)['error']}")
        except KeyError:
            logging.critical(f"Ошибка: {json.loads(res.text)['error']}")


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
        self.doc_manager = SBISManager(self.login, self.password)
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
                # print(product)
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
        with (open(IMP_FILEPATH, 'w') as file):
            today = datetime.today().strftime('%d.%m.%Y')
            delivery_date_str = order_data.get('delivery_date', None)
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
            customer_info = json.loads(order_data.get('party_data_json', '{}'))
            customer_inn = customer_info.get('data', {}).get('inn', None)
            customer_kpp = customer_info.get('data', {}).get('kpp', None)
            order_address = customer_info.get('address_data', {}).get('value', None)
            customer_name = order_data.get('party', None).replace('"', '&quot;')
            comment = order_data.get('comment', None).replace('"', '&quot;')
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
            items = json.loads(order_data.get('positionsData', '[]'))
            for item in items:
                item_name = item['article'].replace('"', '&quot;')
                quantity = int(item.get('quantity', '1'))
                total_quantity += quantity
                info = self.articles_list[item['article']]
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
                for i in range(quantity):
                    task_data = {"code": code,
                                 "item_name": item['article'],
                                 "customer_name": order_data.get('party', None),
                                 "customer_inn": customer_inn,
                                 "customer_kpp": customer_kpp,
                                 "order_contact": order_contact,
                                 "delivery_date": delivery_date,
                                 "comment": comment,
                                 "info": info}

                    self.create_task(task_data)  # Создаёт наряд на каждый матрац

            file.write(f'''
        <Всего НеттоВс="{total_quantity}" СтБезНДСВс="{full_price}" СтУчНДСВс="{full_price}"/>
      </СодФХЖ2>
    </СвДокПТПрКроме>
    <СодФХЖ3 СодОпер="Перечисленные в документе ценности переданы"/>
    <Подписант ОблПолн="2"/>
  </Документ>

</Файл>''')

        with open(IMP_FILEPATH, "rb") as file:
            encoded_string = base64.b64encode(file.read())
            base64_file = encoded_string.decode('ascii')

        params = {"Документ": {
            "Тип": "ДокОтгрИсх",
            "Вложение": [{'Файл': {'Имя': IMP_FILEPATH, 'ДвоичныеДанные': base64_file}}],
            "Регламент": {"Идентификатор": self.reg_id['implementation']},
            "Контакт": order_contact,
            "Примечание": comment,
            "Ответственный": {"Фамилия": "Харьковский",
                              "Имя": "Александр",
                              "Отчество": "Максимович"},
            "ДополнительныеПоля": {"Предоплата": prepayment,
                                   "НужноПолучить": amount_to_receive,
                                   "Контакт": order_contact}}}

        return self.doc_manager.main_query('СБИС.ЗаписатьДокумент', params)

    def create_task(self, data):
        attributes = data.get('info', None).get('attributes')
        materials = '\n'.join(f'{key}: {value}' for key, value in attributes.items())
        params = {"Документ": {
            "Тип": "СлужЗап",
            "Регламент": {"Идентификатор": self.reg_id['task']},
            "Срок": data.get("delivery_date"),
            "Примечание": f"{data.get('item_name')}. {data.get('comment')}",
            "Автор": {"Имя": "Александр",
                      "Отчество": "Максимович",
                      "Фамилия": "Харьковский"},
            "ДополнительныеПоля": {"Заказчик": data.get('customer_name'),
                                   "Позиция": f"{data.get('item_name')} ({data.get('code')})",
                                   "Материалы": materials,
                                   "Комментарий": data.get('comment')}}}

        return self.doc_manager.main_query('СБИС.ЗаписатьДокумент', params)


if __name__ == '__main__':
    LOGIN = 'ХарьковскийАМ'
    PASSWORD = 'Retread-Undusted9-Catalyst-Unseated'
    SALE_POINT_NAME = 'Кесиян Давид Арсенович, ИП'
    PRICE_LIST_NAME = 'Тестовые матрацы'
    sbis = SBISWebApp(LOGIN, PASSWORD, SALE_POINT_NAME, PRICE_LIST_NAME)
    sbis.create_task({})
