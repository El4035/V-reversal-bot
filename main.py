
import requests
import time
import threading
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask
from telegram import Bot

# ==== Telegram ====
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

# ==== Flask-сервер для Render ====
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"

# ==== История сигналов ====
sent_signals = set()

# ==== Получение топ-200 монет с CoinGecko ====
def get_top_200_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": False
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        return response.json()
    except:
        return []

# ==== Получение свечей с Binance ====
def get_klines(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'trades', 'taker_base_vol',
            'taker_quote_vol', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['low'] = df['low'].astype(float)
        df['high'] = df['high'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except:
        return pd.DataFrame()

# ==== Индикаторы ====
def calculate_indicators(df):
    df['EMA21'] = df['close'].ewm(span=21).mean()
    df['EMA50'] = df['close'].ewm(span=50).mean()
    df['BB_MA'] = df['close'].rolling(window=20).mean()
    df['BB_STD'] = df['close'].rolling(window=20).std()
    df['BB_lower'] = df['BB_MA'] - 2 * df['BB_STD']
    df['RSI'] = compute_rsi(df['close'])
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ==== Фильтр разворота ====
def check_v_reversal(df):
    if df.empty or len(df) < 30:
        return False, None

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Условия V-разворота (вторая волна)
    cond1 = latest['RSI'] > prev['RSI'] and prev['RSI'] < 35
    cond2 = latest['close'] > latest['EMA21'] and latest['close'] > prev['close']
    cond3 = latest['close'] > latest['BB_lower']
    cond4 = latest['volume'] > df['volume'].rolling(window=20).mean().iloc[-1]
    cond5 = latest['low'] >= df['low'].rolling(window=5).min().iloc[-1]  # отскок от поддержки

    if cond1 and cond2 and cond3 and cond4 and cond5:
        entry = round(latest['close'], 6)
        stop = round(df['low'].rolling(window=5).min().iloc[-1], 6)
        rr = round((entry - stop) / (stop * 0.01), 1)  # упрощённо
        tp4 = round(entry + (entry - stop) * 2.618, 6)
        return True, {"entry": entry, "stop": stop, "tp4": tp4, "rr": rr}
    return False, None

# ==== Главная функция ====
def scan_coins():
    coins = get_top_200_coins()
    for coin in coins:
        try:
            symbol = coin['symbol'].upper()
            if "USD" in symbol or "USDT" in symbol or coin['current_price'] > 3:
                continue
            if coin['total_volume'] < 1_000_000 or coin['market_cap'] < 5_000_000:
                continue
            if coin['id'] in sent_signals:
                continue

            binance_symbol = symbol + "USDT"
            df = get_klines(binance_symbol, interval="1h", limit=100)
            df = calculate_indicators(df)

            ok, data = check_v_reversal(df)
            if ok:
                msg = f"📈 *V-разворот найден!*\n\n" \
                      f"🪙 Монета: `{symbol}`\n" \
                      f"💰 Entry: `{data['entry']}`\n" \
                      f"🛑 Stop: `{data['stop']}`\n" \
                      f"🎯 TP4: `{data['tp4']}`\n" \
                      f"📊 R/R: `{data['rr']}:1`\n\n" \
                      f"[🔗 Открыть на CoinGecko](https://www.coingecko.com/en/coins/{coin['id']})"
                bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                sent_signals.add(coin['id'])
                print(f"✅ Сигнал по {symbol}")
        except Exception as e:
            print(f"Ошибка для {coin['id']}: {e}")

# ==== Потоки ====
def run_flask():
    app.run(host="0.0.0.0", port=10000)

def run_loop():
    while True:
        scan_coins()
        time.sleep(180)

# ==== Запуск ====
if __name__ == "__main__":
    try:
        bot.send_message(chat_id=CHAT_ID, text="🤖 Бот на V‑разворот запущен!")
        print("✅ Telegram-бот запущен")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_loop).start()
