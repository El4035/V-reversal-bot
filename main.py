import requests
import time
import pandas as pd
from flask import Flask
from telegram import Bot

# Telegram настройки
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

# Flask-сервер для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "V-reversal bot is running"

# Память сигналов, чтобы не дублировались
sent_signals = set()

# Получить свечи с Binance
def get_klines(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["low"] = df["low"].astype(float)
    df["high"] = df["high"].astype(float)
    df["open"] = df["open"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

# Индикаторы
def calculate_indicators(df):
    df["EMA21"] = df["close"].ewm(span=21).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()
    df["RSI"] = compute_rsi(df["close"], 14)
    df["BB_MID"] = df["close"].rolling(window=20).mean()
    df["BB_STD"] = df["close"].rolling(window=20).std()
    df["BB_LOW"] = df["BB_MID"] - 2 * df["BB_STD"]
    return df

# RSI вручную
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Проверка второй волны
def check_second_wave(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    vol_increased = latest["volume"] > df["volume"].rolling(10).mean().iloc[-1] * 1.5
    candle = latest["close"] > latest["open"]
    bb_break = prev["close"] < prev["BB_LOW"] and latest["close"] > latest["BB_LOW"]
    ema_cross = latest["close"] > latest["EMA21"] > latest["EMA50"]
    rsi_conver = latest["RSI"] > prev["RSI"]

    return all([vol_increased, candle, bb_break, ema_cross, rsi_conver])

# Основная логика
def scan_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": False
    }
    response = requests.get(url)
    coins = response.json()

    for coin in coins:
        symbol = coin["symbol"].upper()
        if "USD" in symbol or coin["current_price"] > 3:
            continue
        if coin["market_cap"] < 5_000_000 or coin["total_volume"] < 1_000_000:
            continue

        if not any(ex in coin["platforms"] for ex in ["kraken", "mexc", "bybit"]):
            continue

        try:
            binance_symbol = symbol + "USDT"
            df = get_klines(binance_symbol)
            df = calculate_indicators(df)

            if check_second_wave(df):
                entry = df["close"].iloc[-1]
                stop = df["low"].rolling(5).min().iloc[-1]
                rr = (entry - stop) * 3 + entry

                msg_id = f"{symbol}_{round(entry, 4)}"
                if msg_id in sent_signals:
                    continue
                sent_signals.add(msg_id)

                text = f"""
🟢 BUY signal for {symbol}
Entry: {entry:.4f}
Stop: {stop:.4f}
TP1: {(entry * 1.272):.4f}
TP2: {(entry * 1.618):.4f}
TP3: {(entry * 2.0):.4f}
TP4: {(entry * 2.618):.4f}
R/R ≈ 3:1
"""
                bot.send_message(chat_id=CHAT_ID, text=text.strip())
        except Exception as e:
            print(f"❌ Error for {symbol}: {e}")

# Запуск
print("Bot zapushchen i rabotaet!")

scan_coins()

