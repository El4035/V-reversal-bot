# main.py (финальная версия, 154 строки)
import requests
from flask import Flask
from telegram import Bot
import time
import threading
import datetime
import math

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)

SENT_IDS = set()

def send_signal(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        print("✅ Сигнал отправлен")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": "false"
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
        "vs_currency": "usd",
        "days": "4",
        "interval": "hourly"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        prices = data["prices"]
        volumes = data["total_volumes"]
        return prices, volumes
    except Exception as e:
        print(f"Ошибка при получении OHLCV: {e}")
        return [], []

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = prices[i][1] - prices[i - 1][1]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0][1]
    for price in prices[1:]:
        ema = price[1] * k + ema * (1 - k)
    return ema

def calculate_bb(prices, period=20):
    if len(prices) < period:
        return None, None

    closes = [p[1] for p in prices[-period:]]
    mean = sum(closes) / period
    variance = sum((c - mean) ** 2 for c in closes) / period
    std = math.sqrt(variance)
    lower = mean - 2 * std
    upper = mean + 2 * std
    return lower, upper

def analyze_coin(coin):
    coin_id = coin["id"]
    symbol = coin["symbol"].upper()
    name = coin["name"]
    current_price = coin["current_price"]
    volume = coin["total_volume"]
    market_cap = coin["market_cap"]

    if current_price > 3 or volume < 1_000_000 or market_cap < 5_000_000:
        return

    if any(x in symbol for x in ["USD", "USDT", "BUSD", "DAI", "TUSD"]):
        return

    blacklist = ["SCAM", "PIG", "TURD"]
    if symbol in blacklist:
        return

    allowed_exchanges = ["kraken", "mexc", "bybit"]
    tickers_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers"
    tickers = requests.get(tickers_url).json().get("tickers", [])
    if not any(t["market"]["identifier"] in allowed_exchanges for t in tickers):
        return

    prices, volumes = get_ohlcv(coin_id)
    if not prices or not volumes:
        return

    recent_price = prices[-1][1]
    rsi = calculate_rsi(prices[-15:])
    ema21 = calculate_ema(prices[-21:], 21)
    ema50 = calculate_ema(prices[-50:], 50)
    bb_low, bb_high = calculate_bb(prices)

    if not all([rsi, ema21, ema50, bb_low]):
        return

    if rsi > 35 or recent_price > bb_low:
        return

    if not (recent_price > ema21 > ema50):
        return

    recent_volume = volumes[-1][1]
    previous_volume = volumes[-2][1]
    if recent_volume < previous_volume * 1.5:
        return

    support = min(p[1] for p in prices[-10:])
    entry = recent_price
    stop = support
    rr = round((entry - stop) / (entry * 0.03), 1)

    if rr < 3:
        return

    tp1 = round(entry * 1.1, 4)
    tp2 = round(entry * 1.2, 4)
    tp3 = round(entry * 1.5, 4)
    tp4 = round(entry * 2.0, 4)

    key = f"{symbol}_{round(entry, 4)}"
    if key in SENT_IDS:
        return

    SENT_IDS.add(key)
    message = (
        f"🟢 <b>BUY сигнал (V‑разворот)</b>\n\n"
        f"<b>{name} ({symbol})</b>\n"
        f"Цена: ${entry:.4f}\n"
        f"Stop: ${stop:.4f}\n"
        f"TP1: ${tp1}\n"
        f"TP2: ${tp2}\n"
        f"TP3: ${tp3}\n"
        f"TP4: ${tp4}\n"
        f"R/R: {rr}:1\n\n"
        f"https://www.coingecko.com/en/coins/{coin_id}"
    )
    send_signal(message)

def run_bot():
    send_signal("🤖 Бот V‑разворота запущен!")
    while True:
        try:
            coins = get_top_coins()
            for coin in coins:
                analyze_coin(coin)
        except Exception as e:
            print(f"Ошибка при сканировании монет: {e}")
        time.sleep(180)

@app.route('/')
def home():
    return "✅ I'm alive!"

if __name__ == '__main__':
    t = threading.Thread(target=run_bot)
    t.start()
    app.run(host='0.0.0.0', port=10000)
