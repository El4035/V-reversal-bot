from flask import Flask
from telegram import Bot
import requests
import time
import threading

# Telegram настройки
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

# Flask-сервер для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ V-reversal бот работает!"

# Функция отправки сигнала
def send_signal(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        print("✅ Сигнал отправлен в Telegram")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

# Основная логика анализа (упрощённая версия сигнала V-разворота)
def analyze_v_reversal():
    try:
        # Пример запроса свечей с Binance (замени на нужный тикер и интервал)
        symbol = "WIFUSDT"
        interval = "1h"
        limit = 100
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url)
        data = response.json()

        closes = [float(candle[4]) for candle in data]  # закрытия
        lows = [float(candle[3]) for candle in data]    # минимумы
        volumes = [float(candle[5]) for candle in data]

        if len(closes) < 30:
            return

        last_close = closes[-1]
        prev_low = lows[-3]
        last_low = lows[-1]
        last_volume = volumes[-1]
        avg_volume = sum(volumes[-20:]) / 20

        # Простая логика разворота: двойное дно, повышенный объём
        if last_low > prev_low and last_volume > 1.2 * avg_volume:
            rr_ratio = 3.2
            stop = round(last_close * 0.97, 4)
            tp = round(last_close * 1.15, 4)

            message = f"🟢 BUY сигнал (V-образный разворот)\n" \
                      f"Монета: {symbol}\n" \
                      f"Вход: {last_close}\n" \
                      f"Стоп: {stop}\n" \
                      f"Цель: {tp}\n" \
                      f"R/R: {rr_ratio}:1"

            send_signal(message)

    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")

# Автозапуск логики каждые 3 минуты
def auto_loop():
    while True:
        analyze_v_reversal()
        time.sleep(180)

# Запуск
if __name__ == '__main__':
    threading.Thread(target=auto_loop).start()
    app.run(host='0.0.0.0', port=10000)
