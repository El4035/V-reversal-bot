
import requests
import time
import csv
from flask import Flask
from threading import Thread

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

app = Flask(__name__)
sent_signals = set()

def send_telegram(message):
    try:
        requests.post(TG_URL, data={"chat_id": CHAT_ID, "text": message})
    except:
        pass

def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 200, "page": 1}
    return requests.get(url, params=params).json()

def analyze_coin(coin):
    try:
        symbol = coin["symbol"].upper()
        name = coin["name"]
        price = coin["current_price"]
        volume = coin["total_volume"]
        cap = coin["market_cap"]
        ath = coin.get("ath", 0)
        platforms = coin.get("platforms", {})

        if symbol in ["SCAM", "PIG", "TURD"]:
            return
        if any(stable in symbol for stable in ["USD", "USDT", "BUSD", "DAI", "TUSD"]):
            return
        if price > 3 or price == 0:
            return
        if volume < 1_000_000 or cap < 5_000_000 or ath == 0:
            return
        if not any(ex in platforms for ex in ["kraken", "mexc", "bybit"]):
            return

        drop = round((price - ath) / ath * 100, 2)
        if drop > -80:
            return

        signal_id = coin["id"]
        if signal_id in sent_signals:
            return

        tp1 = round(price * 1.272, 4)
        tp2 = round(price * 1.618, 4)
        tp3 = round(price * 2.0, 4)
        tp4 = round(price * 2.618, 4)
        stop = round(price * 0.97, 4)
        rr = round((tp4 - price) / (price - stop), 1)

        if rr < 3:
            return

        sent_signals.add(signal_id)

        msg = f"📈 BUY сигнал: *{name}*

"
        msg += f"💚 Entry: ${price}
"
        msg += f"❌ Stop: ${stop}
"
        msg += f"🎯 TP1: ${tp1}
"
        msg += f"🎯 TP2: ${tp2}
"
        msg += f"🎯 TP3: ${tp3}
"
        msg += f"🎯 TP4: ${tp4}
"
        msg += f"📊 Объём 24ч: ${int(volume):,}
"
        msg += f"📉 Падение от ATH: {drop}%
"
        msg += f"✅ R/R: {rr}:1
"
        msg += f"\n🔗 https://www.coingecko.com/en/coins/{signal_id}"

        send_telegram(msg)

        with open("signals_log.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([signal_id, symbol, price, stop, tp4, rr])

    except:
        pass

def run_bot():
    while True:
        coins = get_top_coins()
        for coin in coins:
            analyze_coin(coin)
        time.sleep(180)

@app.route('/')
def home():
    return "✅ V-Reversal bot is running!"

def start_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    Thread(target=start_flask).start()
    send_telegram("🤖 Бот V-разворота запущен!")
    run_bot()
