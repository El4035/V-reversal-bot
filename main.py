from flask import Flask
from telegram import Bot
import requests
import time
import threading

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)

def send_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
        print("✅ Сообщение отправлено")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")

def analyze():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "price_change_percentage": "24h"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        print("Ошибка получения данных:", e)
        return

    for coin in data:
        try:
            price = coin["current_price"]
            ath = coin["ath"]
            volume = coin["total_volume"]
            market_cap = coin["market_cap"]
            symbol = coin["symbol"].upper()
            name = coin["name"]
            id = coin["id"]
            exchanges = coin.get("platforms", {})

            if (
                price <= 5
                and ath > 0
                and price < ath * 0.25
                and volume >= 1_000_000
                and market_cap >= 5_000_000
                and not any(stable in symbol for stable in ["USD", "USDT", "BUSD", "DAI", "TUSD"])
                and symbol not in ["SCAM", "PIG", "TURD"]
            ):
                tp1 = round(price * 1.272, 4)
                tp2 = round(price * 1.618, 4)
                tp3 = round(price * 2.0, 4)
                tp4 = round(price * 2.618, 4)
                rr = round((tp4 - price) / (price * 0.1), 1)

                if tp2 >= price * 2:
                    link = f"https://www.coingecko.com/en/coins/{id}"
                    msg = (
                        f"🚀 <b>{name} ({symbol})</b>\n\n"
                        f"💰 Цена: ${price}\n"
                        f"📉 Падение от ATH: {round(100 - (price / ath * 100), 1)}%\n"
                        f"🎯 Цели:\n"
                        f"— TP1: ${tp1}\n"
                        f"— TP2: ${tp2}\n"
                        f"— TP3: ${tp3}\n"
                        f"— TP4: ${tp4}\n"
                        f"📈 Потенциал R/R ≈ {rr}:1\n\n"
                        f"🔗 <a href='{link}'>Смотреть на CoinGecko</a>"
                    )
                    send_message(msg)
        except Exception as e:
            print("Ошибка анализа монеты:", e)

def run_loop():
    while True:
        analyze()
        time.sleep(180)

@app.route('/')
def home():
    return "🤖 Бот работает!"

if __name__ == '__main__':
    send_message("✅ Бот запущен и работает!")
    thread = threading.Thread(target=run_loop)
    thread.start()
    app.run(host='0.0.0.0', port=8080)
