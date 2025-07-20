import requests
import time
import math
from datetime import datetime
from flask import Flask
from telegram import Bot

# --- Telegram настройки ---
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

# --- Flask сервер ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ V-бот активен и работает!"

# --- Глобальные переменные ---
sent_signals = {}

# --- Функции расчёта индикаторов ---
def calculate_rsi(closes, period=14):
    deltas = np.diff(closes)
    ups = deltas.clip(min=0)
    downs = -deltas.clip(max=0)

    avg_gain = np.convolve(ups, np.ones(period), 'valid') / period
    avg_loss = np.convolve(downs, np.ones(period), 'valid') / period

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return np.concatenate([np.full(period, np.nan), rsi])

def calculate_ema(prices, period):
    return np.convolve(prices, np.ones(period)/period, mode='valid')

def calculate_bb(closes, period=20, mult=2):
    sma = np.convolve(closes, np.ones(period)/period, mode='valid')
    std = np.array([np.std(closes[i-period:i]) for i in range(period, len(closes)+1)])
    upper = sma + mult * std
    lower = sma - mult * std
    return sma, upper, lower

# --- Проверка монеты ---
def analyze_symbol(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    data = requests.get(url).json()

    if not data or 'code' in data:
        return

    closes = [float(k[4]) for k in data]
    lows = [float(k[3]) for k in data]
    highs = [float(k[2]) for k in data]
    volumes = [float(k[5]) for k in data]

    if len(closes) < 50:
        return

    close = closes[-1]
    rsi = calculate_rsi(np.array(closes))[-1]
    bb_sma, bb_upper, bb_lower = calculate_bb(np.array(closes))
    lower_bb = bb_lower[-1]
    ema21 = calculate_ema(closes, 21)[-1]
    ema50 = calculate_ema(closes, 50)[-1]
    volume = volumes[-1]
    prev_volume = volumes[-2]

    # Условия сигнала BUY (вторая волна)
    if (
        rsi <= 35 and
        close < lower_bb and
        close > ema21 and
        close > ema50 and
        volume > prev_volume and
        volume > 100000
    ):
        entry = close
        stop = min(lows[-5:])
        if stop == 0 or entry <= stop:
            return
        rr = (entry - stop)
        tp1 = round(entry + rr * 1.272, 6)
        tp2 = round(entry + rr * 1.618, 6)
        tp3 = round(entry + rr * 2.0, 6)
        tp4 = round(entry + rr * 2.618, 6)
        ratio = round((tp4 - entry) / (entry - stop), 1)

        if ratio < 3:
            return

        text = f"""
🟢 <b>BUY сигнал по {symbol}</b>
Цена входа: <b>{entry:.6f}</b>
Stop Loss: <b>{stop:.6f}</b>
—
TP1: {tp1}
TP2: {tp2}
TP3: {tp3}
TP4: {tp4}
R/R = {ratio}:1
⏱ Таймфрейм: {interval}
        """
        key = f"{symbol}-{interval}"
        if key not in sent_signals:
            try:
                bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')
                sent_signals[key] = True
            except Exception as e:
                print("Ошибка Telegram:", e)

# --- Основной цикл ---
def main():
    while True:
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 200,
                "page": 1,
                "sparkline": "false"
            }
            coins = requests.get(url, params=params).json()

            allowed_exchanges = ["kraken", "mexc", "bybit"]

            for coin in coins:
                symbol = coin.get("symbol", "").upper()
                price = coin.get("current_price", 0)
                volume = coin.get("total_volume", 0)
                market_cap = coin.get("market_cap", 0)
                tickers = coin.get("tickers", [])

                if (
                    any(x in symbol for x in ["USD", "USDT", "BUSD", "TUSD", "DAI"]) or
                    price > 5 or
                    volume < 1_000_000 or
                    market_cap < 5_000_000 or
                    not any(t["market"]["identifier"] in allowed_exchanges for t in tickers)
                ):
                    continue

                binance_symbol = symbol + "USDT"
                for interval in ["15m", "1h", "4h"]:
                    analyze_symbol(binance_symbol, interval)

        except Exception as e:
            print("Ошибка в main:", e)

        time.sleep(180)

if __name__ == "__main__":
    try:
        bot.send_message(chat_id=CHAT_ID, text="🤖 Бот V-разворота запущен и работает!")
    except Exception as e:
        print("Ошибка при запуске Telegram:", e)

    import threading
    threading.Thread(target=main).start()
    app.run(host='0.0.0.0', port=8080)

