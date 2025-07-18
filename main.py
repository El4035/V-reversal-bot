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

def get_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 200, "page": 1}
    return requests.get(url, params=params).json()

def analyze_coin(coin):
    try:
        if coin["symbol"].upper() in ["SCAM", "PIG", "TURD"]:
            return None
        if any(stable in coin["symbol"].upper() for stable in ["USD", "USDT", "BUSD", "DAI", "TUSD"]):
            return None
        if coin["current_price"] > 3:
            return None
        if coin["total_volume"] < 1_000_000 or coin["market_cap"] < 5_000_000:
            return None
        if not any(e in coin["platforms"] for e in ["kraken", "mexc", "bybit"]):
            return None

        ath = coin.get("ath", 0)
        price = coin["current_price"]
        if ath == 0 or price == 0:
            return None

        drop = round((price - ath) / ath * 100, 2)
        tp2 = round(price * 1.618, 4)
        tp4 = round(price * 2.618, 4)

        if drop <= -80 and tp2 >= price * 2:
            signal_id = coin["id"]
            if signal_id in sent_signals:
                return None
            sent_signals.add(signal_id)

            msg = f"📉 *V-Разворот: {coin['name']}*\n\n"
            msg += f"💰 Цена: ${price}\n"
            msg += f"📉 Падение от ATH: {drop}%\n\n"
            msg += f"🎯 Цели:\n• TP1 = ${round(price*1.272, 4)}\n• TP2 = ${tp2}\n• TP3 = ${round(price*2.0, 4)}\n• TP4 = ${tp4}"
            if tp4 >= price * 3:
                msg += "\n\n🚀 *High Potential!*"
            msg += f"\n\n🔗 https://www.coingecko.com/en/coins/{coin['id']}"

            send_telegram(msg)
            with open("signals_log.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([coin["id"], coin["symbol"], price, drop, tp2, tp4])
    except:
        pass

def run_bot():
    while True:
        coins = get_coins()
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
    send_telegram("🤖 V-Reversal бот запущен!")
    run_bot()
