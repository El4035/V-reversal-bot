import time
import requests
from telegram import Bot
from flask import Flask
from threading import Thread

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ V-Reversal бот активен!"

def send_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print(f"❌ Ошибка отправки Telegram: {e}")

def calculate_rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        (gains if delta > 0 else losses).append(abs(delta))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period or 1e-10
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(data, period):
    k = 2 / (period + 1)
    ema = data[0]
    for price in data[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_bollinger_bands(closes, period=20, std_dev=2):
    ma = sum(closes) / period
    variance = sum((c - ma) ** 2 for c in closes) / period
    std = variance ** 0.5
    return ma + std_dev * std, ma, ma - std_dev * std

def fetch_candles(symbol, interval='1h', limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url)
    return [[float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in r.json()]

def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 200,
        'page': 1
    }
    response = requests.get(url).json()
    allowed_exchanges = ["kraken", "mexc", "bybit"]
    stablecoins = ["USD", "USDT", "BUSD", "DAI", "TUSD"]
    blacklist = ["SCAM", "PIG", "TURD"]

    filtered = []
    for coin in response:
        if (
            coin["current_price"] <= 3 and
            coin["total_volume"] >= 1_000_000 and
            coin["market_cap"] and coin["market_cap"] >= 5_000_000 and
            not any(stable in coin["symbol"].upper() for stable in stablecoins) and
            coin["symbol"].upper() not in blacklist and
            any(ex in [e["name"].lower() for e in coin.get("tickers", [])] for ex in allowed_exchanges)
        ):
            filtered.append(coin)
    return filtered

def analyze_coin(coin):
    symbol = coin["symbol"].upper() + "USDT"
    try:
        candles = fetch_candles(symbol)
    except:
        return

    closes = [c[4] for c in candles]
    volumes = [c[5] for c in candles]
    lows = [c[2] for c in candles]

    if len(closes) < 21:
        return

    rsi = calculate_rsi(closes[-15:])
    ema21 = calculate_ema(closes[-21:], 21)
    ema50 = calculate_ema(closes[-50:], 50)
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes[-20:])

    last_close = closes[-1]
    prev_close = closes[-2]
    last_low = lows[-1]
    prev_low = lows[-2]
    vol = volumes[-1]

    # Условия сигнала второй волны V-разворота
    if (
        rsi < 35 and
        last_close > prev_close and
        last_low < bb_lower and
        last_close > ema21 > ema50 and
        vol > sum(volumes[-10:]) / 10  # объём выше среднего
    ):
        entry = last_close
        stop = min(prev_low, bb_lower)
        rr = round((entry - stop) / (entry * 0.01), 1)
        if rr < 3:
            return

        tp1 = round(entry * 1.1, 4)
        tp2 = round(entry * 1.272, 4)
        tp3 = round(entry * 1.618, 4)
        tp4 = round(entry * 2.0, 4)

        msg = (
            f"📈 <b>V-Reversal BUY сигнал</b>\n"
            f"Монета: <b>{coin['name']} ({symbol})</b>\n"
            f"Цена входа: ${entry:.4f}\n"
            f"Stop-Loss: ${stop:.4f}\n"
            f"TP1: ${tp1} | TP2: ${tp2}\n"
            f"TP3: ${tp3} | TP4: ${tp4}\n"
            f"R/R: {rr}:1\n"
            f"Объём: {round(vol, 0)}"
        )
        send_message(msg)

def run_bot():
    send_message("🤖 V-Reversal бот запущен и работает!")
    while True:
        try:
            coins = get_top_coins()
            for coin in coins:
                analyze_coin(coin)
        except Exception as e:
            print("Ошибка:", e)
        time.sleep(180)

Thread(target=run_bot).start()
Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 10000}).start()
