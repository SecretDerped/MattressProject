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

SALE_POINT_NAME = 'Кесиян Давид Арсенович, ИП'
PRICE_LIST_NAME = 'Тестовые матрацы'


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
    def __init__(self, login: str, password: str):
        super().__init__(login, password)
        self.reg_id = reglament_id_list

    def get_sale_point(self, point_name: str = SALE_POINT_NAME):
        res = self.main_query('/point/list?', {'withPrices': 'true'})
        for point in res['salesPoints']:
            if point['name'] == point_name:  # 'Гаспарян Роман Славикович, ИП':
                return point['id']

    def get_price_list(self, point_id: str, list_name: str = PRICE_LIST_NAME):
        params = {'pointId': point_id,
                  'actualDate': '2024-03-14'} # TODO: Сделать гит, воткнуть даты
        res = self.main_query('/nomenclature/price-list?', params)
        for list in res['priceLists']:
            if list['name'] == list_name:
                return list['id']

    def get_nomenclature_list(self, point_id: str, price_list_id: str):
        params = {'pointId': point_id,
                  'priceListId': price_list_id}
        return self.main_query('/nomenclature/list?', params)

    def get_articles(self):
        articles_list = dict()
        point_id = self.get_sale_point(SALE_POINT_NAME)
        price_list_id = self.get_price_list(point_id, PRICE_LIST_NAME)
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
        return articles_list



'''    def write_implementation(self):
        base64_file = ''
        params = {"Документ": {
            "Тип": "ДокОтгрИсх",
            "Вложение": [{'Файл': {'Имя': XML_FILEPATH, 'ДвоичныеДанные': base64_file}}],
            "Регламент": {"Идентификатор": self.reg_id['implementation']},
            "Примечание": 'APITEST',
            "Ответственный": 'Харьковский Александр Максимович'}}

        return self.main_query('СБИС.ЗаписатьДокумент', params)'''


if __name__ == '__main__':
    sbis = SBISWebApp('ХарьковскийАМ', 'rx7SiNZtAb')
    for key, val in sbis.get_articles().items():
        print(key, val)
