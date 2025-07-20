import requests
import time
from telegram import Bot
from flask import Flask
import threading
from datetime import datetime

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)

# 1. Получение списка монет с CoinGecko
def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": "false"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return []

# 2. Проверка условий сигнала V-разворота (упрощено)
def check_signal(coin):
    price = coin['current_price']
    ath = coin['ath']
    volume = coin['total_volume']
    cap = coin['market_cap']
    name = coin['name']
    symbol = coin['symbol'].upper()
    id = coin['id']
    exchanges = ["kraken", "mexc", "bybit"]

    if (
        price <= 3 and
        price > 0 and
        volume >= 1_000_000 and
        cap >= 5_000_000 and
        "usd" not in symbol.lower() and
        not any(bad in symbol.lower() for bad in ["scam", "pig", "turd"]) and
        (ath - price) / ath >= 0.75
    ):
        # 3. Получение списка бирж
        markets_url = f"https://api.coingecko.com/api/v3/coins/{id}/tickers"
        res = requests.get(markets_url)
        if res.status_code == 200:
            data = res.json()
            listed_exchanges = set()
            for item in data["tickers"]:
                ex = item["market"]["identifier"]
                if ex in exchanges:
                    listed_exchanges.add(ex)
            if listed_exchanges:
                return {
                    "name": name,
                    "symbol": symbol,
                    "price": price,
                    "ath": ath,
                    "drop": round((ath - price) / ath * 100, 1),
                    "exchanges": listed_exchanges
                }
    return None

# 4. Расчёт целей и отправка в Telegram
def send_signal(coin):
    name = coin["name"]
    symbol = coin["symbol"]
    price = coin["price"]

    # === Обновлённый блок ФИБО и TP ===
    tp1 = round(price * 1.272, 4)
    tp2 = round(price * 1.618, 4)
    tp3 = round(price * 2.0, 4)
    tp4 = round(price * 2.618, 4)
    rr_ratio = round((tp4 - price) / (price * 0.03), 1)
    # === Конец обновления ===

    msg = f"""🟢 <b>BUY Signal (V‑Reversal)</b>

🔹 <b>{name} ({symbol})</b>
💰 Price: ${price}
📉 Drop from ATH: {coin["drop"]}%
📈 Targets:
▫️TP1: ${tp1}
▫️TP2: ${tp2}
▫️TP3: ${tp3}
▫️TP4: ${tp4}
🎯 R/R ≈ {rr_ratio}:1

📊 Exchanges: {', '.join(coin['exchanges'])}
🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"""

    try:
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
    except Exception as e:
        print(f"Telegram error: {e}")

# 5. Основной цикл
sent_ids = set()

def run_bot():
    while True:
        coins = get_top_coins()
        for coin in coins:
            if coin["id"] in sent_ids:
                continue
            data = check_signal(coin)
            if data:
                send_signal(data)
                sent_ids.add(coin["id"])
        time.sleep(180)

# 6. Flask keep-alive
@app.route('/')
def home():
    return "✅ Bot is running!"

def start_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    print("🤖 Бот запущен!")
    try:
        bot.send_message(chat_id=CHAT_ID, text="🤖 Бот запущен!")
    except Exception as e:
        print(f"Telegram error: {e}")
    threading.Thread(target=start_flask).start()
    run_bot()
