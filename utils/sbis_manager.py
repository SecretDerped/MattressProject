import base64
import os
import json
import logging
import requests
from datetime import datetime

from utils.tools import load_conf

config = load_conf()
imp_filepath = config.get('sbis').get('implementation_filepath')


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
        if not os.path.exists('../cash'):
            os.makedirs('../cash')

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

            with open(f"cash/{self.login}_sbis_token.txt", "w+") as file:
                file.write(sid)
            return sid

        except KeyError:
            logging.critical(f"Ошибка авторизации: {json.loads(res.text)['error']}")

    def get_sid(self):
        try:
            with open(f"cash/{self.login}_sbis_token.txt", "r") as file:
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
        payload = {"app_client_id": config.get('sbis').get('app_client_id'),
                   "app_secret": config.get('sbis').get('app_secret'),
                   "secret_key": config.get('sbis').get('secret_key')}
        response = requests.post(f'https://online.sbis.ru/oauth/service/', json=payload)
        response.encoding = 'utf-8'
        result = json.loads(response.text)

        sid = result['sid']
        with open(f"cash/{self.login}_sbis_service_sid.txt", "w+") as file:
            file.write(sid)

        token = result['token']
        with open(f"cash/{self.login}_sbis_service_token.txt", "w+") as file:
            file.write(token)

        return sid, token

    def get_tokens(self):
        try:
            with open(f"cash/{self.login}_sbis_sid.txt", "r") as file:
                sid = file.read()
            with open(f"cash/{self.login}_sbis_token.txt", "r") as file:
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
        self.reg_id = config.get('sbis').get('regalement_id_list')
        self.sale_point_name = sale_point_name
        self.price_list_name = price_list_name
        self.nomenclatures_list = {}

    def get_sale_point_id(self):
        res = self.main_query('/point/list?', {'withPrices': 'true'})
        for point in res['salesPoints']:
            if point['name'] == self.sale_point_name:  # 'Гаспарян Роман Славикович, ИП'
                return point['id']

    def get_price_list_id(self, point_id: str):
        params = {'pointId': point_id,
                  'actualDate': '2024-03-18'}
        res = self.main_query('/nomenclature/price-list?', params)
        for price_list in res['priceLists']:
            if price_list['name'] == self.price_list_name:
                return price_list['id']

    def get_nomenclature_list(self, point_id: str, price_list_id: str, page: int):
        """
        get_nomenclature_list возвращает список из словарей:
        {
            article: str  # Артикул наименования
            attributes: [{...}]  # Массив с характеристиками товара
            balance: str  # Остаток товара с учетом открытых смен. Остаток передается по складу точки продаж
            barcodes: [{...}]  # Массив штрих-кодов
                code: str  # Штрихкод
                codetype: str  # Тип штрих-кода (EAN-13, EAN-8)
            cost: integer  # Цена товара из прайса
            description: str  # Поле «Описание» из карточки товара
            externalId: str  # Идентификатор товара в формате UUID
            hierarchicalId: integer  # Идентификатор раздела
            hierarchicalParent: integer  # Идентификатор родительского раздела
            id: integer  # Идентификатор товара
            images: list[str]  # Массив ссылок на изображение товара
            indexNumber: integer  # Порядковый номер в каталоге
            modifiers: list[{...}]  # Массив списков модификаторов
                id: integer  # Идентификатор товарной позиции
                externalId: str  # Идентификатор товара в формате UUID
                nomNumber: str  # Код товара, указанный в карточке товара
                name: str  # Название товара
                cost: int/float  # Цена модификатора
                unit: str  # Название единицы измерения
            name: str  # Название товара
            nomNumber: str  # Код товара, указанный в карточке товара
            published: boolean  # Признак публикации товарной позиции
            masters: str  # Список сотрудников, которые могут применять этот товар/услугу
            short_code: integer  # Короткий код
            unit: str  # Единица измерения
            outcome: boolean  # Признак наличия записей на следующих страницах
        }
            """
        params = {'pointId': point_id,
                  'priceListId': price_list_id,
                  'pageSize': 300,
                  'page': page}
        return self.main_query('/nomenclature/list?', params)

    def get_nomenclatures(self) -> dict:
        """Подтягивает номенклатуру из прайс-листа в разделе Бизнес - Цены
        в виде словаря с названиями позиций в качестве ключей, а в значениях - словарь свойств позиции.
        Важно: на момент июня 2024-го СБИС не даёт подтягивать номенклатуру просто так, только из
        прайс-листа. ЕСЛИ НОМЕНКЛАТУРА НЕ ВЫГРУЖАЕТСЯ, ПРОВЕРЬ ПРАЙС-ЛИСТ "Позиции для Telegram-бота" """
        point_id = self.get_sale_point_id()
        price_list_id = self.get_price_list_id(point_id)
        # ID товарной группы матрасов. Далее стоит проверка товара на
        # принадлежность этой группе. Товары из группы матрасов попадают
        # в датафрейм в качестве задания на производство
        mattress_group_id = config.get('sbis').get('mattress_group_id')
        fabrics_group_id = config.get('sbis').get('fabrics_group_id')
        springs_group_id = config.get('sbis').get('springs_group_id')

        # Это пригодится чуть ниже для пангинации
        page = 0

        # Пустой словарик, который будем заполнять данными
        # В качестве ключа к данными о позиции будет название позиции в СБИС
        nomenclatures_list = dict()

        while True:
            product_list = self.get_nomenclature_list(point_id, price_list_id, page)
            logging.debug("Nomenclature list: ")
            logging.debug(product_list)

            # Выход сразу же, если список номенклатур пустой
            if not product_list['nomenclatures']:
                break
            # Оп! Пангинация!
            page += 1
            for product in product_list['nomenclatures']:
                # Позиции без номера это каталоги. Пропускаем
                if not product['nomNumber']:
                    continue

                key_name = product['name']
                nomenclatures_list[key_name] = {'code': product.get('nomNumber', 0),
                                                'article': product.get('article', 'Неизвестен'),
                                                'price': product.get('cost', 0),
                                                'description': product.get('description_simple', ''),
                                                'attributes': product.get('attributes', {'': ''}),
                                                'images': product.get('images', None),
                                                'is_mattress': False,
                                                'is_fabric': False,
                                                'is_springs': False}

                # Вычисляем группу позиции, типа ткань, матрас, или ещё что-либо
                group = product['hierarchicalParent']
                attributes = nomenclatures_list[key_name]['attributes']

                # Если товар принадлежит к группе матрасов, пишем размер в отдельное поле
                if group == mattress_group_id:
                    nomenclatures_list[key_name]['is_mattress'] = True
                    nomenclatures_list[key_name]['size'] = attributes.get('Размер', '0')
                    nomenclatures_list[key_name]['structure'] = attributes.get('Состав', '')
                # А если к группе тканей, то ставится тип "Ткань"
                if group == fabrics_group_id:
                    nomenclatures_list[key_name]['is_fabric'] = True
                    # Раньше аттрибут типа ткани использовался для коррекции бочины
                    # Теперь поиск идёт по ключевым словам в названии ткани
                    # nomenclatures_list[key_name]['type'] = attributes.get('Тип ткани', '')
                if group == springs_group_id:
                    nomenclatures_list[key_name]['is_springs'] = True

            # Цикл прерывается, если позиций больше нет
            if not product_list['outcome']['hasMore']:
                break

        self.nomenclatures_list = nomenclatures_list
        return nomenclatures_list

    def create_implementation_xml(self, data):
        today = datetime.today().strftime('%d.%m.%Y')

        delivery_date = datetime.strptime(data.get('delivery_date', '2000-01-01'), '%Y-%m-%d').strftime('%d.%m.%Y')
        # Заменяем двойные кавычки на &quot;, иначе XML посчитает эти кавычки за конец строки и разметка сломается.
        customer_name = data.get('organization', None).replace('"', '&quot;')

        # Если поле "Компания" оставить пустым при создании заявки, счёт оформится как розница,
        # а если нет, то в счёте будет юрлицо
        customer_inn, customer_kpp, company_address = None, None, None
        wholesale = False
        if data['organization']:
            wholesale = True

        if wholesale:
            customer_info = json.loads(data.get('organization_data', {}))
            customer_inn = customer_info.get('data', {}).get('inn', None)
            customer_kpp = customer_info.get('data', {}).get('kpp', None)
            company_address = customer_info.get('address_data', {}).get('value', None)

        comment = data.get('comment', '').replace('"', '&quot;')

        xml_content = f'''<?xml version="1.0" encoding="WINDOWS-1251" ?>
<Файл ВерсФорм="5.02">

  <СвУчДокОбор>
    <СвОЭДОтпр/>
  </СвУчДокОбор>

  <Документ ВремИнфПр="9.00.00" ДатаИнфПр="{today}" КНД="1175010" НаимЭконСубСост="ИП Гаспарян Роман Славикович">
    <СвДокПТПрКроме>
      <СвДокПТПр>
        <НаимДок НаимДокОпр="Товарная накладная" ПоФактХЖ="Документ о передаче товара при торговых операциях"/>
        <ИдентДок ДатаДокПТ="{today}"/>
        <СодФХЖ1>
          <ГрузОтпр ОКПО="0151033706">
            <ИдСв>
              <СвИП ИННФЛ="230911595879" СвГосРегИП="323237500002399">
                <ФИО Имя="Роман" Отчество="Славикович" Фамилия="Гаспарян"/>
              </СвИП>
            </ИдСв>
            <Адрес>
              <АдрИнф АдрТекст="Краснодарский край, г.о. город Краснодар, г. Краснодар" КодСтр="643"/>
            </Адрес>
          </ГрузОтпр>'''
        if wholesale:
            xml_content += f''''
          <ГрузПолуч ОКПО="20524053">
            <ИдСв>
              <СвОрг>
                <СвЮЛ ИННЮЛ="{customer_inn}" '''
            if customer_kpp:
                xml_content += f'КПП="{customer_kpp}" '
            xml_content += f'''НаимОрг="{customer_name}"/>
          </СвОрг>
        </ИдСв>
        <Адрес>
          <АдрИнф АдрТекст="{company_address}" КодСтр="643"/>
        </Адрес>
      </ГрузПолуч>'''
        xml_content += f'''
          <Продавец ОКПО="0151033706">
            <ИдСв>
              <СвИП ИННФЛ="230911595879" СвГосРегИП="323237500002399">
                <ФИО Имя="Роман" Отчество="Славикович" Фамилия="Гаспарян"/>
              </СвИП>
            </ИдСв>
            <Адрес>
              <АдрИнф АдрТекст="Краснодарский край, г.о. город Краснодар, г. Краснодар" КодСтр="643"/>
            </Адрес>
          </Продавец>'''
        if wholesale:
            xml_content += f'''
      <Покупатель ОКПО="20524053">
        <ИдСв>
          <СвОрг>
            <СвЮЛ ИННЮЛ="{customer_inn}" КПП="{customer_kpp}" НаимОрг="{customer_name}"/>
          </СвОрг>
        </ИдСв>
        <Адрес>
          <АдрИнф АдрТекст="{company_address}" КодСтр="643"/>
        </Адрес>
        <Контакт Тлф="8 (861) 204-05-06" ЭлПочта="dir@le-ar.ru"/>
        <БанкРекв НомерСчета="40702810512550035771">
          <СвБанк БИК="044525360" КорСчет="30101810445250000360" НаимБанк="Филиал &quot;Корпоративный&quot; ПАО &quot;Совкомбанк&quot; МОСКВА"/>
        </БанкРекв>
      </Покупатель>'''
        else:
            xml_content += f'''
          <Покупатель>
            <ИдСв/>
          </Покупатель>'''
        xml_content += f'''
          <Основание НаимОсн="-"/>
          <ИнфПолФХЖ1>
            <ТекстИнф Значен="{comment}" Идентиф="Примечание"/>
            <ТекстИнф Значен="{comment}" Идентиф="ИнфПередТабл"/>
            <ТекстИнф Значен="{delivery_date}" Идентиф="Срок"/>
            <ТекстИнф Значен="23:59:59" Идентиф="СрокВремя"/>
            <ТекстИнф Значен="Основной склад" Идентиф="СкладНаименование"/>
            <ТекстИнф Значен="ИП Гаспарян Роман Славикович" Идентиф="НаимПост"/>
            <ТекстИнф Значен="ИП Гаспарян Роман Славикович" Идентиф="НаимГрузОтпр"/>
          </ИнфПолФХЖ1>
        </СодФХЖ1>
      </СвДокПТПр>
      <СодФХЖ2>'''

        item_num = 1
        total_quantity = 0
        total_price = 0
        positions = data.get('mattresses', '[]')
        for position in positions:
            position_price = position['price']
            item_name = position['name'].replace('"', '&quot;')
            item_quantity = int(position.get('quantity', '1'))
            total_quantity += item_quantity
            item_price = position_price / item_quantity

            info = self.nomenclatures_list[position['name']]
            code = info.get("code")

            total_price += position_price
            #  НаимЕдИзм="шт"
            xml_content += f'''
        <СвТов КодТов="{code}" НаимТов="{item_name}" НалСт="без НДС" НеттоПередано="{item_quantity}" НомТов="{item_num}" ОКЕИ_Тов="796" СтБезНДС="{position_price}" СтУчНДС="{position_price}" Цена="{item_price}">
          <ИнфПолФХЖ2 Значен="{code}" Идентиф="КодПоставщика"/>
          <ИнфПолФХЖ2 Значен="{item_name}" Идентиф="НазваниеПоставщика"/>
          <ИнфПолФХЖ2 Значен="&quot;Type&quot;:&quot;Товар&quot;" Идентиф="ПоляНоменклатуры"/>
          <ИнфПолФХЖ2 Значен="41-01" Идентиф="СчетУчета"/>
        </СвТов>'''
            item_num += 1

        positions = data.get('additionalItems', '[]')
        for position in positions:
            position_price = float(position['price'])
            item_name = position['name'].replace('"', '&quot;')
            item_quantity = int(position.get('quantity', '1'))
            total_quantity += item_quantity
            item_price = position_price / item_quantity

            info = self.nomenclatures_list[position['name']]
            code = info.get("code")

            total_price += position_price
            #  НаимЕдИзм="шт"
            xml_content += f'''
                <СвТов КодТов="{code}" НаимТов="{item_name}" НалСт="без НДС" НеттоПередано="{item_quantity}" НомТов="{item_num}" ОКЕИ_Тов="796" СтБезНДС="{position_price}" СтУчНДС="{position_price}" Цена="{item_price}">
                  <ИнфПолФХЖ2 Значен="{code}" Идентиф="КодПоставщика"/>
                  <ИнфПолФХЖ2 Значен="{item_name}" Идентиф="НазваниеПоставщика"/>
                  <ИнфПолФХЖ2 Значен="&quot;Type&quot;:&quot;Товар&quot;" Идентиф="ПоляНоменклатуры"/>
                  <ИнфПолФХЖ2 Значен="41-01" Идентиф="СчетУчета"/>
                </СвТов>'''
            item_num += 1

        xml_content += f'''
        <Всего НеттоВс="{total_quantity}" СтБезНДСВс="{total_price}" СтУчНДСВс="{total_price}"/>
      </СодФХЖ2>
    </СвДокПТПрКроме>
    <СодФХЖ3 СодОпер="Перечисленные в документе ценности переданы"/>
    <Подписант ОблПолн="2">
      <ИП СвГосРегИП="323237500002399">
        <ФИО/>
      </ИП>
    </Подписант>
  </Документ>

</Файл>
'''
        with open(imp_filepath, 'w') as file:
            return file.write(xml_content)

    def write_implementation(self, order_data: dict):
        logging.info(f"Order data:\n{order_data}")

        # Такая конструкция вернёт пустой словарь, вместо None, если данных нет.
        customer_info = json.loads(order_data.get('organization_data', {}) or '{}')
        logging.debug(customer_info)

        total_price = 0
        mattresses = order_data['mattresses']
        for position in mattresses:
            total_price += float(position['price'])

        additional_items = order_data['additionalItems']
        for position in additional_items:
            total_price += float(position['price'])

        prepayment = order_data['prepayment']
        amount_to_receive = total_price - prepayment

        self.create_implementation_xml(order_data)

        with open(imp_filepath, "rb") as file:
            encoded_string = base64.b64encode(file.read())
            base64_file = encoded_string.decode('ascii')

        regulation = self.reg_id['direct_sell'] if customer_info == {} else self.reg_id['wholesale']
        order_contact = order_data.get('contact', None)
        comment = order_data.get('comment', '').replace('"', '&quot;')
        order_address = customer_info.get('address_data', {}).get('value', None)

        params = {"Документ": {
            "Тип": "ДокОтгрИсх",
            "Вложение": [{'Файл': {'Имя': imp_filepath,
                                   'ДвоичныеДанные': base64_file}}],
            "Регламент": {"Идентификатор": regulation},
            "Контакт": order_contact,
            "Примечание": comment,
            "Ответственный": {"Фамилия": "Харьковский",
                              "Имя": "Александр",
                              "Отчество": "Максимович"},
            "ДополнительныеПоля": {"Предоплата": round(prepayment),
                                   "НужноПолучить": round(amount_to_receive),
                                   "Контакт": order_contact,
                                   "Адрес": order_address}}}

        return self.doc_manager.main_query('СБИС.ЗаписатьДокумент', params)
