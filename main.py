import requests
import time
from datetime import datetime
from flask import Flask
from telegram import Bot

# --- Telegram настройки ---
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

# --- Flask сервер ---
app = Flask(__name__)
@app.route("/")
def home():
    return "V-Reversal bot is alive!"

# --- Конфигурация ---
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
BINANCE_URL = "https://api.binance.com/api/v3/klines"
VS_CURRENCY = "usd"
ALLOWED_EXCHANGES = ["mexc", "bybit", "kraken"]
MAX_PRICE = 5.0
MIN_VOLUME = 1_000_000
MIN_MARKET_CAP = 5_000_000
MIN_DROP_FROM_ATH = 0.75
INTERVALS = {"15m": "15m", "1h": "1h", "4h": "4h"}

sent_signals = set()

# --- Индикаторы ---
def calculate_rsi(closes, period=14):
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    seed = deltas[:period]
    up = sum(x for x in seed if x > 0) / period
    down = -sum(x for x in seed if x < 0) / period
    rs = up / down if down != 0 else 0
    rsi = [100 - 100 / (1 + rs)]
    for delta in deltas[period:]:
        upval = max(delta, 0)
        downval = -min(delta, 0)
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi.append(100 - 100 / (1 + rs))
    return rsi[-1] if rsi else 0

def calculate_ema(data, period):
    k = 2 / (period + 1)
    ema = data[0]
    for price in data[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_bb(closes, period=20):
    if len(closes) < period:
        return None, None, None
    sma = sum(closes[-period:]) / period
    std = (sum((x - sma) ** 2 for x in closes[-period:]) / period) ** 0.5
    return sma - 2 * std, sma, sma + 2 * std

# --- Получение списка монет ---
def fetch_eligible_coins():
    params = {
        "vs_currency": VS_CURRENCY,
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": "false"
    }
    coins = requests.get(COINGECKO_URL, params=params).json()
    result = []
    for coin in coins:
        if (
            coin.get("current_price") and coin["current_price"] <= MAX_PRICE and
            coin.get("total_volume") and coin["total_volume"] >= MIN_VOLUME and
            coin.get("market_cap") and coin["market_cap"] >= MIN_MARKET_CAP and
            coin.get("ath") and coin["ath"] > 0 and
            coin["current_price"] / coin["ath"] <= 1 - MIN_DROP_FROM_ATH and
            coin.get("platforms") and any(ex in coin["platforms"] for ex in ALLOWED_EXCHANGES) and
            "usd" not in coin["symbol"].lower()
        ):
            result.append(coin["symbol"].upper() + "USDT")
    return result

# --- Анализ одной монеты ---
def analyze_symbol(symbol, interval):
    params = {"symbol": symbol.lower(), "interval": interval, "limit": 100}
    try:
        response = requests.get(BINANCE_URL, params={"symbol": symbol, "interval": interval, "limit":100})
        data = response.json()
        if not isinstance(data, list) or len(data) < 50:
            return
        closes = [float(c[4]) for c in data]
        lows = [float(c[3]) for c in data]
        volumes = [float(c[5]) for c in data]
        last_close = closes[-1]
        last_low = lows[-1]
        support = min(lows[-10:])
        rsi = calculate_rsi(closes)
        ema21 = calculate_ema(closes[-21:], 21)
        ema50 = calculate_ema(closes[-50:], 50)
        bb_low, _, _ = calculate_bb(closes)

        # Условия входа
        if (
            rsi <= 35 and
            last_close < bb_low and
            last_close > ema21 > ema50 and
            volumes[-1] > sum(volumes[-6:-1]) / 5 and
            last_low <= support * 1.01
        ):
            stop = support * 0.99
            tp = support + (last_close - support) * 1.618  # заменили расчёт TP
            rr = (tp - last_close) / (last_close - stop)
            if rr < 3:
                return
            signal_id = f"{symbol}_{interval}"
            if signal_id in sent_signals:
                return
            sent_signals.add(signal_id)
            text = (
                f"📡 <b>BUY</b> на <b>{interval}</b>\n"
                f"🔹 Монета: <b>{symbol}</b>\n"
                f"💰 Entry: <b>{round(last_close, 5)}</b>\n"
                f"🛑 Stop: <b>{round(stop, 5)}</b>\n"
                f"🎯 TP: <b>{round(tp, 5)}</b>\n"
                f"📈 R/R: <b>{round(rr, 2)}:1</b>\n"
                f"#Vreversal #Crypto"
            )
            bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')
    except Exception as e:
        print(f"❌ Ошибка по {symbol}: {e}")

# --- Главный цикл ---
def run_bot():
    try:
        coins = fetch_eligible_coins()
        for interval in INTERVALS.values():
            for symbol in coins:
                analyze_symbol(symbol, interval)
    except Exception as e:
        print("❌ Ошибка запуска:", e)

# --- Telegram старт ---
try:
    bot.send_message(chat_id=CHAT_ID, text="✅ V-Reversal бот запущен!")
except:
    pass

# --- Автообновление ---
if __name__ == "__main__":
    while True:
        run_bot()
        time.sleep(180)
