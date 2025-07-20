import requests
import time
from flask import Flask
from telegram import Bot
import math

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ V-Reversal Bot is Alive!"

def get_top_200_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": False
    }
    response = requests.get(url, params=params)
    return response.json()

def get_candle_data(symbol):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol.upper() + "USDT", "interval": "1h", "limit": 100}
    response = requests.get(url, params=params)
    return response.json()

def calculate_rsi(closes, period=14):
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi_values = []

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi_values.append(rsi)

    return rsi_values[-1] if rsi_values else None

def calculate_ema(closes, period):
    k = 2 / (period + 1)
    ema = closes[0]
    for price in closes[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_bb(closes, period=20, num_std_dev=2):
    if len(closes) < period:
        return None, None, None
    sma = sum(closes[-period:]) / period
    variance = sum((price - sma) ** 2 for price in closes[-period:]) / period
    std_dev = math.sqrt(variance)
    upper_band = sma + num_std_dev * std_dev
    lower_band = sma - num_std_dev * std_dev
    return lower_band, sma, upper_band

sent_signals = {}

def analyze_coin(coin):
    try:
        if coin["symbol"].upper() in sent_signals:
            return

        if coin["current_price"] > 3:
            return

        if coin["total_volume"] < 1_000_000:
            return

        if coin["market_cap"] < 5_000_000:
            return

        blacklist = ["SCAM", "PIG", "TURD", "ASS", "POOP", "FLOKI"]
        if any(bad in coin["symbol"].upper() for bad in blacklist):
            return

        stable_keywords = ["USD", "USDT", "BUSD", "DAI", "TUSD"]
        if any(stable in coin["symbol"].upper() for stable in stable_keywords):
            return

        allowed_exchanges = ["kraken", "mexc", "bybit"]
        tickers = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin['id']}/tickers").json()["tickers"]
        markets = set(ticker["market"]["identifier"] for ticker in tickers)
        if not any(ex in markets for ex in allowed_exchanges):
            return

        candles = get_candle_data(coin["symbol"])
        closes = [float(c[4]) for c in candles]
        lows = [float(c[3]) for c in candles]
        volumes = [float(c[5]) for c in candles]

        current_rsi = calculate_rsi(closes)
        if current_rsi is None or current_rsi > 35:
            return

        ema21 = calculate_ema(closes[-21:], 21)
        ema50 = calculate_ema(closes[-50:], 50)
        if closes[-1] < ema21 or closes[-1] < ema50:
            return

        lower_bb, mid_bb, upper_bb = calculate_bb(closes)
        if closes[-1] > lower_bb:
            return

        if volumes[-1] < sum(volumes[-5:]) / 5:
            return

        if closes[-1] <= lows[-1]:
            return

        entry = closes[-1]
        low = min(lows[-20:])  # LOW используется как 0% уровень фибо
        stop = low * 0.98

        # ✅ TP-блоки на основе low → entry
        diff = entry - low
        tp1 = entry + diff * 1.272
        tp2 = entry + diff * 1.618
        tp3 = entry + diff * 2.0
        tp4 = entry + diff * 2.618

        risk = entry - stop
        reward = tp4 - entry
        rr = reward / risk

        if rr < 3:
            return

        message = (
            f"📈 <b>V-Reversal BUY Signal</b>\n"
            f"🔹 Coin: <b>{coin['symbol'].upper()}</b>\n"
            f"💰 Entry: <code>{entry:.6f}</code>\n"
            f"📉 Stop: <code>{stop:.6f}</code>\n"
            f"🎯 TP1: <code>{tp1:.6f}</code>\n"
            f"🎯 TP2: <code>{tp2:.6f}</code>\n"
            f"🎯 TP3: <code>{tp3:.6f}</code>\n"
            f"🎯 TP4: <code>{tp4:.6f}</code>\n"
            f"📊 R/R: <b>{rr:.2f}</b>:1"
        )

        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
        sent_signals[coin["symbol"].upper()] = True
        print("✅ Signal sent:", coin["symbol"].upper())

    except Exception as e:
        print(f"❌ Error analyzing {coin['symbol']}: {e}")

def main():
    try:
        bot.send_message(chat_id=CHAT_ID, text="✅ Бот V-Reversal запущен!")
    except:
        pass

    while True:
        coins = get_top_200_coins()
        for coin in coins:
            analyze_coin(coin)
        time.sleep(180)

if __name__ == "__main__":
    from threading import Thread
    Thread(target=main).start()
    app.run(host="0.0.0.0", port=8080)
