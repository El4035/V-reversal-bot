
import requests
import time
import math
from telegram import Bot
from flask import Flask
import threading

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

# ✅ Тестовое сообщение — УДАЛИ после проверки
bot.send_message(chat_id=CHAT_ID, text="✅ Тестовое сообщение: бот работает!")

app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"

def get_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": "false"
    }
    response = requests.get(url, params=params)
    return response.json()

def check_signal():
    coins = get_coins()
    for coin in coins:
        try:
            symbol = coin["symbol"].upper()
            price = coin["current_price"]
            ath = coin["ath"]
            vol = coin["total_volume"]
            cap = coin["market_cap"]
            markets = coin.get("platforms", {})

            if (
                price <= 3 and
                ath > 0 and
                vol >= 1_000_000 and
                cap >= 5_000_000 and
                "kraken" in coin["name"].lower() or
                "mexc" in coin["name"].lower() or
                "bybit" in coin["name"].lower()
            ):
                drop = (ath - price) / ath
                if drop >= 0.75:
                    tp1 = round(price * 1.272, 6)
                    tp2 = round(price * 1.618, 6)
                    tp3 = round(price * 2.0, 6)
                    tp4 = round(price * 2.618, 6)
                    rr = round((tp2 - price) / (price * 0.05), 1)

                    tags = []
                    if drop >= 0.95:
                        tags.append("🚨 ULTRA DROP")
                    if tp4 >= price * 3:
                        tags.append("🚀 HIGH POTENTIAL")

                    msg = f"""🟢 <b>BUY SIGNAL</b> — {symbol}
💰 Цена: ${price}
📉 Падение от ATH: {round(drop*100)}%
🎯 Цели:
• TP1: ${tp1}
• TP2: ${tp2}
• TP3: ${tp3}
• TP4: ${tp4}
⚖️ R/R ≈ {rr}:1
📊 Объём: ${vol:,.0f}
🏷️ {' | '.join(tags) if tags else '—'}"""

                    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="HTML")
        except Exception as e:
            print(f"❌ Ошибка при обработке {coin.get('id', '')}: {e}")

def run_loop():
    while True:
        check_signal()
        time.sleep(180)

if __name__ == "__main__":
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start()
    run_loop()
