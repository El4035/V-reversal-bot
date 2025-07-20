
import requests
import time
import datetime
from telegram import Bot
from flask import Flask
import threading

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Бот работает!"

def send_signal(name, symbol, price, entry, stop, rr, tp1, tp2, tp3, tp4):
    message = (
        f"🟢 *V-разворот (BUY)*\n"
        f"*Монета:* {name} ({symbol})\n"
        f"*Цена:* ${price}\n"
        f"*Entry:* ${entry}\n"
        f"*Stop:* ${stop}\n"
        f"*R/R:* {rr:.2f}\n"
        f"*TP1:* ${tp1}\n"
        f"*TP2:* ${tp2}\n"
        f"*TP3:* ${tp3}\n"
        f"*TP4:* ${tp4}"
    )
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
        print(f"✅ Сигнал отправлен: {symbol}")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def analyze():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        print(f"Ошибка API CoinGecko: {e}")
        return

    for coin in data:
        try:
            price = coin["current_price"]
            ath = coin["ath"]
            volume = coin["total_volume"]
            cap = coin["market_cap"]
            name = coin["name"]
            symbol = coin["symbol"].upper()
            markets = [m["name"] for m in coin.get("platforms", {}).values()]

            # Фильтры
            if (
                price <= 5 and
                ath > 0 and
                volume >= 1_000_000 and
                cap >= 5_000_000 and
                not any(stable in symbol for stable in ["USD", "USDT", "BUSD", "TUSD", "DAI"]) and
                symbol not in ["SCAM", "PIG", "TURD"] and
                any(m in ["Kraken", "MEXC", "Bybit"] for m in coin.get("tickers", []))
            ):
                drop = (price - ath) / ath
                if drop <= -0.8:
                    # Фибо от лоу до Entry
                    low = price - (price * 0.25)  # Имитация лоу на 25% ниже
                    entry = price
                    tp1 = low + (entry - low) * 1.272
                    tp2 = low + (entry - low) * 1.618
                    tp3 = low + (entry - low) * 2.0
                    tp4 = low + (entry - low) * 2.618
                    stop = low
                    rr = (tp4 - entry) / (entry - stop)

                    if rr >= 3:
                        send_signal(name, symbol, price, entry, stop, rr, tp1, tp2, tp3, tp4)

        except Exception as e:
            print(f"Ошибка при анализе монеты: {e}")

def loop():
    while True:
        print(f"🔍 Проверка {datetime.datetime.now()}")
        analyze()
        time.sleep(180)  # каждые 3 минуты

threading.Thread(target=loop).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
