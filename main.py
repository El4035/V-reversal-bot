import requests
import time
import math
from datetime import datetime
import telebot

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = "944484522"
bot = telebot.TeleBot(TOKEN)

def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": False
    }
    response = requests.get(url, params=params)
    data = response.json()
    coins = []
    for coin in data:
        if (
            coin["current_price"] <= 5 and
            coin["total_volume"] >= 1_000_000 and
            coin["market_cap"] >= 5_000_000 and
            coin["symbol"].upper() not in ["SCAM", "PIG", "TURD"] and
            all(stable not in coin["symbol"].upper() for stable in ["USD", "USDT", "BUSD", "DAI", "TUSD"])
        ):
            coins.append(coin)
    return coins

def get_binance_ohlcv(symbol):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol.upper() + "USDT", "interval": "1h", "limit": 100}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None
    data = response.json()
    ohlcv = []
    for item in data:
        ohlcv.append({
            "time": item[0],
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5])
        })
    return ohlcv

def calculate_rsi(closes, period=14):
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains = [max(delta, 0) for delta in deltas]
    losses = [-min(delta, 0) for delta in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calculate_ema(data, period=21):
    k = 2 / (period + 1)
    ema = data[0]
    for price in data[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_bb(closes, period=20):
    ma = sum(closes[-period:]) / period
    std = (sum((c - ma) ** 2 for c in closes[-period:]) / period) ** 0.5
    upper = ma + (2 * std)
    lower = ma - (2 * std)
    return lower, ma, upper

def analyze_coin(coin):
    symbol = coin["symbol"].upper()
    ohlcv = get_binance_ohlcv(symbol)
    if not ohlcv or len(ohlcv) < 22:
        return

    closes = [c["close"] for c in ohlcv]
    lows = [c["low"] for c in ohlcv]
    rsi = calculate_rsi(closes)
    ema21 = calculate_ema(closes[-21:])
    ema50 = calculate_ema(closes[-50:]) if len(closes) >= 50 else ema21
    lower_bb, _, _ = calculate_bb(closes)

    current_price = closes[-1]
    volume = ohlcv[-1]["volume"]
    low_price = min(lows[-5:])
    entry = round(current_price, 4)
    stop = round(low_price, 4)

    if (
        current_price > ema21 > ema50 and
        rsi < 35 and
        current_price < lower_bb and
        volume > 0
    ):
        # --- БЛОК РАСЧЁТА УРОВНЕЙ ФИБОНАЧЧИ И TP1–TP4 ---
        diff = entry - stop
        tp1 = round(entry + diff * 1.272, 4)
        tp2 = round(entry + diff * 1.618, 4)
        tp3 = round(entry + diff * 2.0, 4)
        tp4 = round(entry + diff * 2.618, 4)

        rr_ratio = round((tp4 - entry) / (entry - stop), 1)

        if rr_ratio >= 3:
            message = (
                f"📈 BUY сигнал по {symbol}/USDT\n\n"
                f"Цена входа: {entry}$\n"
                f"Стоп: {stop}$\n"
                f"TP1: {tp1}$\n"
                f"TP2: {tp2}$\n"
                f"TP3: {tp3}$\n"
                f"TP4: {tp4}$\n\n"
                f"R/R = {rr_ratio}:1"
            )
            try:
                bot.send_message(CHAT_ID, message)
                print(f"✅ Отправлен сигнал по {symbol}")
            except Exception as e:
                print(f"❌ Ошибка Telegram: {e}")

def main():
    try:
        coins = get_top_coins()
        for coin in coins:
            analyze_coin(coin)
    except Exception as e:
        print("Ошибка:", e)

if __name__ == "__main__":
    bot.send_message(CHAT_ID, "✅ Бот запущен и работает!")
    while True:
        main()
        time.sleep(180)
