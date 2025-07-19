import requests
import time
import csv
import os
import math
from datetime import datetime
from flask import Flask
from telegram import Bot

app = Flask(__name__)
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = "944484522"
bot = Bot(token=TOKEN)

sent_signals = set()

def calculate_tp_levels(entry, stop):
    tp1 = round(entry + (entry - stop) * 1.272, 4)
    tp2 = round(entry + (entry - stop) * 1.618, 4)
    tp3 = round(entry + (entry - stop) * 2.0, 4)
    tp4 = round(entry + (entry - stop) * 2.618, 4)
    return tp1, tp2, tp3, tp4

def fetch_ohlcv(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    response = requests.get(url)
    data = response.json()
    return [float(candle[4]) for candle in data]  # closing prices

def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url)
    return float(response.json()["price"])

while True:
    try:
        symbols = ["WIFUSDT", "BONKUSDT", "DOGEUSDT"]
        for symbol in symbols:
            closes = fetch_ohlcv(symbol)
            if len(closes) < 10:
                continue

            price = get_price(symbol)
            minimum = min(closes[-6:])
            if closes[-1] > closes[-2]:
                stop = round(minimum, 4)
                if (price - stop) / price > 0.05:
                    continue

                tps = calculate_tp_levels(price, stop)
                rr = round((tps[3] - price) / (price - stop), 2)
                if rr < 3:
                    continue

                signal_id = f"{symbol}-{stop}"
                if signal_id in sent_signals:
                    continue
                sent_signals.add(signal_id)

                msg = f"✅ BUY SIGNAL\n\n🔹 Symbol: {symbol}\n🔹 Entry: {price}\n🔹 Stop: {stop}\n🔹 TP1: {tps[0]}\n🔹 TP2: {tps[1]}\n🔹 TP3: {tps[2]}\n🔹 TP4: {tps[3]}\n🔹 R/R: {rr}:1"
                bot.send_message(chat_id=CHAT_ID, text=msg)

                with open("signals_log.csv", "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([datetime.now(), symbol, price, stop, *tps, rr])

        time.sleep(180)

    except Exception as e:
        print("Error:", e)

@app.route("/")
def home():
    return "I'm alive!"

if __name__ == "__main__":
    bot.send_message(chat_id=CHAT_ID, text="🤖 Бот V-разворот запущен!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


