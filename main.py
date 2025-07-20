import requests
import time
from flask import Flask
from threading import Thread
from telegram import Bot

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ V-разворот бот активен!"

def fetch_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": False
    }
    return requests.get(url, params=params).json()

def is_valid_coin(coin):
    symbol = coin["symbol"].upper()
    name = coin["name"].lower()
    price = coin["current_price"]
    volume = coin["total_volume"]
    cap = coin["market_cap"]
    exchanges = [ex.lower() for ex in coin.get("platforms", {}).keys()]
    blacklist = ["PIG", "TURD", "SCAM", "ASS", "FART"]

    if any(bad in symbol for bad in blacklist): return False
    if "usd" in symbol.lower(): return False
    if price > 3 or volume < 1_000_000 or cap < 5_000_000: return False
    allowed_exchanges = ["kraken", "mexc", "bybit"]
    if not any(ex in exchanges for ex in allowed_exchanges): return False

    return True

def calculate_indicators(prices):
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(prices, columns=["time", "open", "high", "low", "close", "volume"])
    df["EMA21"] = df["close"].ewm(span=21).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["BB_MA"] = df["close"].rolling(window=20).mean()
    df["BB_STD"] = df["close"].rolling(window=20).std()
    df["BB_LOW"] = df["BB_MA"] - 2 * df["BB_STD"]
    return df

def fetch_binance_ohlc(symbol):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol.upper() + "USDT", "interval": "1h", "limit": 100}
    try:
        res = requests.get(url, params=params)
        return res.json()
    except:
        return None

def send_signal(symbol, interval, last_close, stop, tp, rr):
    text = (
        f"🤖 <b>BUY</b> на <b>{interval}</b>\n"
        f"🔷 Монета: <b>{symbol}</b>\n"
        f"💰 Entry: <b>{round(last_close, 5)}</b>\n"
        f"🛑 Stop: <b>{round(stop, 5)}</b>\n"
        f"🎯 TP: <b>{round(tp, 5)}</b>\n"
        f"📈 R/R = <b>{round(rr, 2)}:1</b>"
    )
    try:
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
    except Exception as e:
        print(f"Telegram error: {e}")

def check_coin(coin):
    symbol = coin["symbol"].upper()
    prices = fetch_binance_ohlc(symbol)
    if not prices or len(prices) < 30: return

    df = calculate_indicators(prices)
    last = df.iloc[-1]
    prev = df.iloc[-2]

    rsi_ok = last["RSI"] > prev["RSI"] and last["RSI"] <= 35
    bb_ok = last["close"] > last["BB_LOW"] and prev["close"] < prev["BB_LOW"]
    ema_ok = last["close"] > last["EMA21"] > last["EMA50"]
    volume_ok = last["volume"] > df["volume"].rolling(10).mean().iloc[-1]
    support = min(df["low"][-10:])

    if not (rsi_ok and bb_ok and ema_ok and volume_ok):
        return

    last_close = last["close"]
    stop = support * 0.99
    tp = support + (last_close - support) * 1.618
    rr = (tp - last_close) / (last_close - stop)

    if rr < 3:
        return

    send_signal(symbol, "1H", last_close, stop, tp, rr)

def run_bot():
    try:
        bot.send_message(chat_id=CHAT_ID, text="🤖 Бот запущен: V-разворот активен!")
    except: pass

    while True:
        try:
            coins = fetch_top_coins()
            for coin in coins:
                if is_valid_coin(coin):
                    check_coin(coin)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(180)

if __name__ == '__main__':
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=8080)
