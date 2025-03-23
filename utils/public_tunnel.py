import logging
import subprocess
import threading
import time

import niquests


def start_localtunnel(port, subdomain):
    """
    Запускает localtunnel для указанного порта и поддомена.
    Возвращает процесс и публичный URL.
    """
    # Формируем команду. Если указать поддомен, то попытка использовать его будет,
    # но если он занят, localtunnel выдаст случайный URL.
    cmd = [r"C:\Users\Celes\AppData\Roaming\npm\lt.cmd", "--port", str(port), "--subdomain", subdomain]
    logging.info(f"Запуск localtunnel для порта {port} с поддоменом {subdomain}: {' '.join(cmd)}")

    # Запускаем процесс localtunnel
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    url = None
    # Ожидаем появления URL в stdout (обычно localtunnel пишет URL в первой строке)
    start_time = time.time()
    timeout = 20  # секунд
    while True:
        line = process.stdout.readline()
        if line:
            logging.info(f"localtunnel ({subdomain}): {line.strip()}")
            # Обычно строка содержит URL, например "your url is: https://fastapi.loca.lt"
            if "your url is:" in line.lower():
                parts = line.strip().split()
                for part in parts:
                    if part.startswith("http"):
                        url = part
                        break
                if url:
                    break
        if time.time() - start_time > timeout:
            logging.error(f"Таймаут ожидания URL для localtunnel на порту {port}")
            break
        time.sleep(0.2)

    if not url:
        logging.error(f"Не удалось получить публичный URL для localtunnel на порту {port}")
    return process, url


def start_localtunnels():
    tunnels = {}
    processes = {}

    def run_tunnel(name, port):
        proc, url = start_localtunnel(port, name)
        processes[name] = proc
        tunnels[name] = url

    threads = []
    for name, port in [("fastapi", 5000), ("streamlit", 8501)]:
        t = threading.Thread(target=run_tunnel, args=(name, port))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    logging.info(f"Полученные публичные URL: {tunnels}")

    return processes, tunnels


def get_tunnel_password():
    url = 'https://loca.lt/mytunnelpassword'
    page = niquests.get(url)
    if page is None:
        raise Exception("Не удалось получить пароль туннеля.")
    return page.text
