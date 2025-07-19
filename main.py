
import requests
import time
import datetime
from flask import Flask
import threading
import math
import os

# Telegram
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = "944484522"

# Flask-сервер для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "V-Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# Параметры
VS_CURRENCY = "usd"
EXCHANGES = ["kraken", "mexc", "bybit"]
MIN_VOLUME = 1_000_000
MIN_CAP = 5_000_000
MAX_PRICE = 3.0
DROP_THRESHOLD = 75  # от ATH
MIN_RR = 3.0

signal_history = set()

def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": VS_CURRENCY,
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": False
    }
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Ошибка при получении списка монет: {e}")
        return []

def get_ohlcv(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": VS_CURRENCY,
        "days": "1",
        "interval": "hourly"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        if len(prices) >= 20 and len(volumes) >= 20:
            return prices[-20:], volumes[-20:]
        return [], []
    except:
        return [], []

def calculate_rsi(prices):
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i][1] - prices[i-1][1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))
    avg_gain = sum(gains) / len(gains)
    avg_loss = sum(losses) / len(losses) + 1e-6
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def check_coin(coin):
    try:
        if coin["current_price"] > MAX_PRICE: return
        if coin["total_volume"] < MIN_VOLUME: return
        if coin["market_cap"] < MIN_CAP: return
        if not any(ex in coin["platforms"].values() for ex in EXCHANGES): return
        ath = coin.get("ath", 0)
        if ath == 0: return
        drop = ((ath - coin["current_price"]) / ath) * 100
        if drop < DROP_THRESHOLD: return

        prices, volumes = get_ohlcv(coin["id"])
        if not prices or not volumes: return

        rsi = calculate_rsi(prices)
        if rsi > 35: return

        # Проверка второй волны (подтверждённый разворот)
        close_now = prices[-1][1]
        close_prev = prices[-2][1]
        if close_now < close_prev: return

        vol_now = volumes[-1][1]
        avg_vol = sum([v[1] for v in volumes[:-1]]) / len(volumes[:-1])
        if vol_now < avg_vol * 1.5: return

        if prices[-1][1] < prices[-2][1] or rsi < 20: return

        entry = round(prices[-1][1], 6)
        stop = round(entry * 0.97, 6)
        tp1 = round(entry * 1.272, 6)
        tp2 = round(entry * 1.618, 6)
        tp3 = round(entry * 2.0, 6)
        tp4 = round(entry * 2.618, 6)
        rr = round((tp4 - entry) / (entry - stop), 1)
        if rr < MIN_RR: return

        key = f"{coin['symbol']}_{entry}"
        if key in signal_history: return
        signal_history.add(key)

        msg = (
            f"📈 <b>BUY сигнал (V-разворот)</b>\n\n"
            f"🪙 <b>{coin['name'].upper()}</b> ({coin['symbol'].upper()})\n"
            f"💰 Цена входа: <b>${entry}</b>\n"
            f"🛑 Стоп: <b>${stop}</b>\n"
            f"🎯 TP1: ${tp1}\n🎯 TP2: ${tp2}\n🎯 TP3: ${tp3}\n🎯 TP4: ${tp4}\n"
            f"⚖️ R/R: <b>{rr}:1</b>\n"
            f"📊 Объём: ${coin['total_volume']:,}\n"
            f"📉 Падение от ATH: {round(drop)}%\n"
            f"📅 Время: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"🌐 https://www.coingecko.com/en/coins/{coin['id']}"
        )
        send_telegram(msg)
        log_signal(coin["symbol"], entry, stop, tp4, rr)
    except Exception as e:
        print(f"Ошибка при проверке монеты {coin['id']}: {e}")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)

def log_signal(symbol, entry, stop, tp4, rr):
    try:
        with open("signals_log.csv", "a") as f:
            f.write(f"{datetime.datetime.utcnow()},{symbol},{entry},{stop},{tp4},{rr}\n")
    except:
        pass

def main_loop():
    while True:
        coins = get_top_coins()
        for coin in coins:
            check_coin(coin)
        time.sleep(180)

# Запуск
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    send_telegram("🤖 Бот V-РАЗВОРОТ запущен!")
    main_loop()

