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
        f"*Entry:* ${entry:.6f}\n"
        f"*Stop:* ${stop:.6f}\n"
        f"*R/R:* {rr:.2f}\n"
        f"*TP1:* ${tp1:.6f}\n"
        f"*TP2:* ${tp2:.6f}\n"
        f"*TP3:* ${tp3:.6f}\n"
        f"*TP4:* ${tp4:.6f}"
    )
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
        print(f"✅ Сигнал отправлен: {symbol}")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def fetch_ohlcv(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
    try:
        response = requests.get(url)
        data = response.json()
        return [[float(candle[1]), float(candle[4]), float(candle[5]), float(candle[2]), float(candle[3]), float(candle[5])] for candle in data]
    except:
        return []

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        if delta > 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

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

            # Фильтры
            if (
                price <= 5 and
                ath > 0 and
                volume >= 1_000_000 and
                cap >= 5_000_000 and
                not any(stable in symbol for stable in ["USD", "USDT", "BUSD", "TUSD", "DAI"]) and
                symbol not in ["SCAM", "PIG", "TURD"]
            ):
                candles = fetch_ohlcv(symbol, interval="1h", limit=100)
                if not candles or len(candles) < 20:
                    continue

                closes = [c[4] for c in candles]
                lows = [c[3] for c in candles]
                rsi = calculate_rsi(closes)
                last_close = closes[-1]
                last_low = lows[-1]

                if rsi and rsi <= 35:
                    # Используем фибо от low до entry (low = 0)
                    low = min(lows[-20:])
                    entry = last_close
                    stop = low
                    tp1 = low + (entry - low) * 1.272
                    tp2 = low + (entry - low) * 1.618
                    tp3 = low + (entry - low) * 2.0
                    tp4 = low + (entry - low) * 2.618
                    rr = (tp4 - entry) / (entry - stop)

                    if rr >= 3:
                        send_signal(name, symbol, price, entry, stop, rr, tp1, tp2, tp3, tp4)

        except Exception as e:
            print(f"Ошибка при анализе монеты: {e}")

def loop():
    while True:
        print(f"🔄 Проверка: {datetime.datetime.now()}")
        analyze()
        time.sleep(180)

threading.Thread(target=loop).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
