import json
import time
import httpx
import logging
import subprocess
from os import getenv
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from sbis_manager import SBISWebApp
load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, encoding='utf-8')
logger = logging.getLogger(__name__)

app = Flask(__name__)
sbis = SBISWebApp(getenv('sbis.login'), getenv('sbis.password'))
articles = sbis.get_articles()


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', articles=articles)


@app.route('/api/articles', methods=['GET'])
def get_articles():
    return jsonify(list(articles))


@app.route('/create_order', methods=['POST'])
def create_order():
    chat_id = request.args.get('chat_id')
    order_data = dict({
        'party': request.form['party'],
        'party_data': request.form['party_data'],
        'articles': request.form['positionsData'],
        'delivery_date': request.form['delivery_date'],
        'delivery_address': request.form['delivery_address'],
        'address_data': request.form['address_data'],
        'contact': request.form['contact'],
        'price': request.form['price'],
        'prepayment': request.form['prepayment']
    })
    order_data['amount_to_receive'] = float(order_data.get('price', 0)) - float(order_data.get('prepayment', 0))

    order_message = (f"""Новая заявка:\n
Артикул: {order_data['articles']}
Дата доставки: {order_data['delivery_date']}
Адрес: {order_data['delivery_address']}
Магазин: {order_data['party']}
Цена: {order_data['price']}
Предоплата: {order_data['prepayment']}
Нужно получить: {order_data['amount_to_receive']}""")
    send_telegram_message(order_message, chat_id)

    return create_sbis_order(order_data)


def create_sbis_order(order_data):
    print('\nЗаказ готооов')
    return "Заказ отправлен"


def send_telegram_message(text, chat_id):
    bot_token = getenv('TG_TOKEN')
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    response = httpx.post(url, data=data)
    print(response.text)
    return response.json()


def start_ngrok():
    process = subprocess.Popen(['ngrok.exe', 'http', '5000'])
    url = None

    while url is None:
        try:
            response = subprocess.check_output(['curl', '-s', 'http://localhost:4040/api/tunnels'])
            data = json.loads(response.decode('utf-8'))
            url = data['tunnels'][0]['public_url']
        except:
            time.sleep(1)
    logging.info(f' * Site is available on ngrok {url}')
    return process, url


def run_flask():
    app.run()


if __name__ == '__main__':
    ngrok_process, ngrok_url = start_ngrok()
    run_flask()

    ngrok_process.wait()
