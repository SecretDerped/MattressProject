import json
import logging
from os import getenv

import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Определение констант для этапов разговора
(STEP_1, STEP_2, STEP_3, STEP_4, STEP_5,
 STEP_6, STEP_7, STEP_8, STEP_9, STEP_10, END) = range(11)


def is_float(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


class SBISobot:
    def __init__(self, login: str = '', password: str = ''):
        self.login = login
        self.password = password
        self.serv_token = None
        self.serv_sid = None
        self.base_url = 'https://online.sbis.ru'
        self.headers = {'Host': 'online.sbis.ru',
                        'Content-Type': 'application/json-rpc; charset=utf-8',
                        'Accept': 'application/json-rpc'}
        self.QUESTIONS = {
            STEP_1: 'Как называется магазин?',
            STEP_2: 'Введите артикул, ткань и размер.',
            STEP_3: 'Какая дата доставки?',
            STEP_4: 'Какой адрес доставки?',
            STEP_5: 'Введите контактные данные.',
            STEP_6: 'Какая цена?',
            STEP_7: 'Какая предоплата?',
            STEP_8: 'Сколько нужно получить?'
        }
        self.RESPONSE_KEYS = {
            STEP_1: 'Название магазина',
            STEP_2: 'Артикул',
            STEP_3: 'Дата доставки',
            STEP_4: 'Адрес доставки',
            STEP_5: 'Контакт',
            STEP_6: 'Цена',
            STEP_7: 'Предоплата',
            STEP_8: 'Сколько нужно получить'
        }
        self.token = getenv('TG_TOKEN')

    def auth(self):
        payload = {
            "jsonrpc": "2.0",
            "method": 'СБИС.Аутентифицировать',
            "params": {"Логин": self.login, "Пароль": self.password},
            "protocol": 2,
            "id": 0
        }
        res = requests.post(f'{self.base_url}/auth/service/', headers=self.headers, data=json.dumps(payload))
        sid = json.loads(res.text)['result']

        with open(f"{self.login}_sbis_token.txt", "w+") as file:
            file.write(sid)

        return sid

    def serv_auth(self):
        json = {"app_client_id": "1431941504152192",
                
                "app_secret": "TTLJISTWTTJKIMTITQMTM2TP",
                "secret_key": "qwTLov0WOF8mgL3h8zRpcbITQxGBdY763n2tTrPYhRLviLy12agCCbyxPuuBak3IDfScRd1yX4IJJphJy1eO56L0vmCz5MIVQEMQEJXpS1QlpqlMI15Gbx"}
        url = 'https://online.sbis.ru/oauth/service/'
        response = requests.post(url, json=json)
        response.encoding = 'utf-8'
        response = response.json()
        self.serv_sid = response['sid']
        self.serv_token = response['token']

    def get_sid(self):
        try:
            with open(f"{self.login}_sbis_token.txt", "r") as file:
                sid = file.read()
                return sid
        except FileNotFoundError:
            try:
                return self.auth()
            except Exception:
                logging.critical(f"Не удалось авторизоваться в СБИС.", exc_info=True)

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

        match res.status_code:
            case 200:
                return json.loads(res.text)['result']
            case 401:
                logging.info('Требуется обновление токена.')
                self.headers['X-SBISSessionID'] = self.auth()
                res = requests.post(f'{self.base_url}/service/', headers=self.headers, data=json.dumps(payload))
                return json.loads(res.text)['result']
            case 500:
                raise AttributeError(f'{method}: Check debug logs.')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(self.QUESTIONS[STEP_1])
        return STEP_1

    # Единая функция для обработки ответов и задавания следующего вопроса
    async def collect_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text
        current_step = context.user_data.get('next_step', STEP_1)
        # Проверка на необходимость ввода числа
        if current_step in [STEP_6, STEP_7, STEP_8] and not is_float(text):
            await update.message.reply_text('Нужно ввести число.')
            return current_step  # Оставляем пользователя на том же шаге

        # Сохранение ответа пользователя
        context.user_data[self.RESPONSE_KEYS[current_step]] = text

        # Переход к следующему вопросу или завершение
        next_step = current_step + 1
        if next_step > STEP_8:
            await self.summarize(update, context)
            return ConversationHandler.END
        else:
            await update.message.reply_text(self.QUESTIONS[next_step])
            context.user_data['next_step'] = next_step
            return next_step

    # Функция для завершения разговора и вывода собранной информации
    async def summarize(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        summary = '\n '.join(
            [f"{key}: {value}" for key, value in context.user_data.items() if key in self.RESPONSE_KEYS.values()])
        params = {"Документ": {"Регламент": {"Идентификатор": "40749c15-7c3a-4c31-a258-f36185562c1a"},
                               "Сумма": context.user_data['Цена'],
                               "Тип": "Наряд",
                               "Контрагент": {
                                   "СвЮЛ": {
                                       "ИНН": "9718084490",
                                       "КПП": "771801001"
                                   }}}}
        self.main_query('СБИС.ЗаписатьДокумент', params)
        await update.message.reply_text(f"НОВАЯ ЗАЯВКА:\n{summary}", reply_markup=ReplyKeyboardRemove())

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text('Разговор завершён.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def main(self) -> None:
        application = Application.builder().token(self.token).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={state: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_info)] for state in
                    range(STEP_1, END)},
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

        application.add_handler(conv_handler)
        application.run_polling()


if __name__ == '__main__':
    bot = SBISobot('leartest', 'Leartest2007!')
    bot.main()
