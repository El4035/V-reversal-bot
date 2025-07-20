
import time
import requests
from datetime import datetime
from flask import Flask
from telegram import Bot

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ V-Reversal Bot is alive!"

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

def filter_coin(coin):
    name = coin["name"]
    symbol = coin["symbol"].upper()
    price = coin["current_price"]
    cap = coin["market_cap"]
    volume = coin["total_volume"]
    exchanges = [ex["name"].lower() for ex in coin.get("tickers", [])]

    if "usd" in symbol or "usdt" in symbol or "busd" in symbol or "dai" in symbol:
        return False
    if price > 5 or volume < 1_000_000 or cap < 5_000_000:
        return False
    allowed_exchanges = ["kraken", "mexc", "bybit"]
    if not any(ex in ex_name for ex_name in exchanges for ex in allowed_exchanges):
        return False
    return True

def calculate_targets(entry, stop):
    diff = entry - stop
    tp1 = round(entry + diff * 1.272, 6)
    tp2 = round(entry + diff * 1.618, 6)
    tp3 = round(entry + diff * 2.0, 6)
    tp4 = round(entry + diff * 2.618, 6)
    return tp1, tp2, tp3, tp4

def calculate_rr(entry, stop, tp4):
    risk = entry - stop
    reward = tp4 - entry
    if risk <= 0:
        return 0
    return round(reward / risk, 2)

def check_signal(coin):
    try:
        id = coin["id"]
        name = coin["name"]
        symbol = coin["symbol"].upper()
        price = coin["current_price"]
        ath = coin["ath"]

        if ath == 0 or price == 0:
            return None

        drop = round((ath - price) / ath * 100, 2)
        if drop < 75:
            return None

        # Simplified second-wave signal confirmation (example)
        entry = price
        stop = round(price * 0.97, 6)  # fixed 3% stop
        tp1, tp2, tp3, tp4 = calculate_targets(entry, stop)
        rr = calculate_rr(entry, stop, tp4)
        if rr < 3:
            return None

        message = f"📈 *V-Разворот BUY сигнал!*\n\n" \
                  f"Монета: *{name}*  \n" \
                  f"Цена входа: ${entry}  \n" \
                  f"Stop-Loss: ${stop}  \n" \
                  f"TP1: ${tp1}  \n" \
                  f"TP2: ${tp2}  \n" \
                  f"TP3: ${tp3}  \n" \
                  f"TP4: ${tp4}  \n\n" \
                  f"R/R = *{rr}:1*\n\n" \
                  f"🔗 https://www.coingecko.com/en/coins/{id}"
        return message

    except Exception as e:
        print(f"Ошибка в check_signal: {e}")
        return None

def scan():
    coins = get_coins()
    for coin in coins:
        if not filter_coin(coin):
            continue
        signal = check_signal(coin)
        if signal:
            try:
                bot.send_message(chat_id=CHAT_ID, text=signal, parse_mode="Markdown")
                print(f"✅ Сигнал отправлен: {coin['name']}")
            except Exception as e:
                print(f"❌ Ошибка при отправке Telegram: {e}")

def run_loop():
    while True:
        print(f"⏰ Проверка: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        scan()
        time.sleep(180)

if __name__ == "__main__":
    try:
        bot.send_message(chat_id=CHAT_ID, text="✅ Бот запущен и работает!")
        print("🚀 Старт: бот запущен")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")
    import threading
    threading.Thread(target=run_loop).start()
    app.run(host="0.0.0.0", port=8080)

