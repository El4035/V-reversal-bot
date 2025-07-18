import requests
import time
import threading
from flask import Flask
from telegram import Bot
import numpy as np

# === TELEGRAM ===
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

# === FLASK SERVER (Render) ===
app = Flask(__name__)

@app.route("/")
def home():
    return "I'm alive!"

# === MEMORY ===
sent_signals = {}

# === INDICATORS ===
def calculate_ema(prices, period):
    return np.convolve(prices, np.ones(period)/period, mode='valid')

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    up = deltas.clip(min=0)
    down = -deltas.clip(max=0)
    avg_gain = np.convolve(up, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(down, np.ones(period)/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-6)
    return 100 - (100 / (1 + rs))

def calculate_bb(prices, period=20, std_dev=2):
    ma = np.convolve(prices, np.ones(period)/period, mode='valid')
    std = np.std(prices[-period:])
    upper = ma[-1] + std_dev * std
    lower = ma[-1] - std_dev * std
    return upper, lower

# === SIGNAL LOGIC ===
def check_for_signals():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 200,
            "page": 1,
            "price_change_percentage": "24h"
        }
        data = requests.get(url, params=params).json()

        for coin in data:
            try:
                symbol = coin['symbol'].upper()
                price = coin['current_price']
                cap = coin['market_cap']
                vol = coin['total_volume']
                exchanges = [ex.lower() for ex in coin.get("platforms", {}).keys()]
                if price > 3 or cap < 5_000_000 or vol < 1_000_000:
                    continue
                if not any(x in exchanges for x in ['kraken', 'mexc', 'bybit']):
                    continue
                if symbol in ["USDT", "USDC", "BUSD", "DAI", "TUSD"]:
                    continue

                klines = requests.get(
                    f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1h&limit=100"
                ).json()
                closes = [float(c[4]) for c in klines]
                if len(closes) < 50:
                    continue

                ema21 = calculate_ema(closes, 21)
                ema50 = calculate_ema(closes, 50)
                rsi = calculate_rsi(closes)[-1]
                upper, lower = calculate_bb(closes)

                last = closes[-1]
                prev = closes[-2]
                volume = float(klines[-1][5])
                prev_volume = float(klines[-2][5])

                # === CONFIRMED V-REVERSAL CONDITIONS ===
                if (
                    last > ema21[-1] > ema50[-1] and
                    last > prev and
                    volume > prev_volume and
                    rsi > 35 and
                    last > lower
                ):
                    stop = round(last * 0.97, 6)
                    tp1 = round(last * 1.1, 6)
                    tp2 = round(last * 1.3, 6)
                    tp3 = round(last * 1.6, 6)
                    tp4 = round(last * 2.0, 6)
                    rr = round((tp4 - last) / (last - stop), 1)
                    if rr < 3:
                        continue
                    if sent_signals.get(symbol):
                        continue
                    message = (
                        f"✅ BUY сигнал по монете {symbol}\n"
                        f"Цена входа: ${last}\n"
                        f"Стоп: ${stop}\n"
                        f"TP1: {tp1}\nTP2: {tp2}\nTP3: {tp3}\nTP4: {tp4}\n"
                        f"R/R = {rr}:1\n"
                        f"https://www.coingecko.com/en/coins/{coin['id']}"
                    )
                    bot.send_message(chat_id=CHAT_ID, text=message)
                    sent_signals[symbol] = True
            except Exception:
                continue
    except Exception as e:
        print("❌ Ошибка анализа:", e)

# === RUN LOOP ===
def run_bot():
    while True:
        check_for_signals()
        time.sleep(180)

# === START ===
if __name__ == "__main__":
    print("🚀 Бот запущен")
    bot.send_message(chat_id=CHAT_ID, text="🤖 Бот на V-разворот запущен!")
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
