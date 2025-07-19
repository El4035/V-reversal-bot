
import requests
import time
from flask import Flask
import threading
from telegram import Bot
import math

# Telegram
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

# Flask сервер
app = Flask(__name__)
@app.route("/")
def home():
    return "✅ V-Reversal bot is running!"

# Настройки
MAX_PRICE = 5.0
USE_BE_READY_FILTER = False  # можно включить при желании
sent_signals = set()

# Запуск Flask в отдельном потоке
def run_flask():
    app.run(host="0.0.0.0", port=10000)

# Получение свечей
def get_klines(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url)
    return response.json()

# RSI
def calculate_rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# EMA
def calculate_ema(data, period):
    k = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for price in data[period:]:
        ema = price * k + ema * (1 - k)
    return ema

# Bollinger Bands
def calculate_bbands(closes, period=20, std_dev=2):
    ma = sum(closes[-period:]) / period
    variance = sum((c - ma) ** 2 for c in closes[-period:]) / period
    std = math.sqrt(variance)
    upper = ma + std_dev * std
    lower = ma - std_dev * std
    return upper, ma, lower

# Сигнальная логика
def analyze_symbol(symbol, interval):
    try:
        klines = get_klines(symbol, interval, 100)
        closes = [float(k[4]) for k in klines]
        lows = [float(k[3]) for k in klines]
        highs = [float(k[2]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        last_close = closes[-1]

        rsi = calculate_rsi(closes)
        ema21 = calculate_ema(closes, 21)
        upper, middle, lower = calculate_bbands(closes)

        support_level = min(lows[-10:])
        resistance_level = max(highs[-10:])
        recent_volume = volumes[-1]
        avg_volume = sum(volumes[-20:]) / 20

        # Условия BUY
        if rsi > 35: return
        if last_close > lower: return
        if last_close < ema21: return
        if recent_volume < avg_volume: return
        if last_close < support_level * 0.98: return

        stop = support_level * 0.99
        tp = resistance_level * 1.02
        rr = (tp - last_close) / (last_close - stop)
        if rr < 3: return

        if interval == "4h":
            signal_type = "be ready"
        else:
            if USE_BE_READY_FILTER:
                return
            signal_type = "BUY"

        signal_id = f"{symbol}_{interval}_{signal_type}"
        if signal_id in sent_signals:
            return
        sent_signals.add(signal_id)

        text = (
            f"📡 <b>{signal_type.upper()}</b> на <b>{interval}</b>\n"
            f"🔹 Монета: <b>{symbol}</b>\n"
            f"💰 Entry: <b>{round(last_close, 5)}</b>\n"
            f"🛑 Stop: <b>{round(stop, 5)}</b>\n"
            f"🎯 Target: <b>{round(tp, 5)}</b>\n"
            f"📈 R/R: <b>{round(rr, 2)}:1</b>\n"
            f"#Vreversal #Crypto #Signal"
        )
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

    except Exception as e:
        print(f"Ошибка: {symbol} ({interval}): {e}")

# Получение списка монет с CoinGecko
def get_top_symbols():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 200, "page": 1}
    data = requests.get(url).json()
    symbols = []

    for coin in data:
        name = coin["symbol"].upper()
        price = coin["current_price"]
        volume = coin["total_volume"]
        cap = coin["market_cap"]
        platforms = coin.get("platforms", {})
        listed_on = ",".join(platforms.keys()).lower()

        if price is None or price > MAX_PRICE: continue
        if volume < 1_000_000 or cap < 5_000_000: continue
        if any(x in name for x in ["USD", "USDT", "BUSD", "DAI", "TUSD"]): continue
        if name in ["SCAM", "PIG", "TURD"]: continue
        if not any(x in listed_on for x in ["kraken", "mexc", "bybit"]): continue

        binance_symbol = name + "USDT"
        symbols.append(binance_symbol)

    return symbols

# Основной цикл
def main_loop():
    try:
        bot.send_message(chat_id=CHAT_ID, text="🤖 Бот запущен: V‑разворот активен!")
    except:
        print("Telegram не отвечает")
    while True:
        try:
            symbols = get_top_symbols()
            for symbol in symbols:
                for interval in ["15m", "1h", "4h"]:
                    analyze_symbol(symbol, interval)
            time.sleep(180)
        except Exception as e:
            print("Ошибка в цикле:", e)
            time.sleep(60)

# Запуск
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    main_loop()
