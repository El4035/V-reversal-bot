
import requests
import time
import pandas as pd
from telegram import Bot
from flask import Flask

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
bot = Bot(token=TOKEN)

app = Flask(__name__)
@app.route("/")
def home():
    return "✅ Бот работает!"

def get_symbols():
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
    symbols = []
    for coin in data:
        price = coin["current_price"]
        volume = coin["total_volume"]
        market_cap = coin["market_cap"]
        name = coin["symbol"].upper()
        if (
            price <= 5 and volume >= 1_000_000 and market_cap >= 5_000_000
            and not any(stable in name for stable in ["USD", "USDT", "BUSD", "DAI", "TUSD"])
            and name not in ["SCAM", "PIG", "TURD"]
        ):
            symbols.append(name + "USDT")
    return symbols

def get_ohlcv(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url)
        data = response.json()
        return pd.DataFrame(data)[[0,1,2,3,4,5]].rename(columns={
            0: "timestamp", 1: "open", 2: "high", 3: "low", 4: "close", 5: "volume"
        }).astype(float)
    except:
        return None

def calculate_rsi(closes, period=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_ema(series, period=21):
    return series.ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_bollinger_bands(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    return lower.iloc[-1], sma.iloc[-1], upper.iloc[-1]

def scan():
    symbols = get_symbols()
    for symbol in symbols:
        df_4h = get_ohlcv(symbol, "4h", 100)
        if df_4h is None or len(df_4h) < 21:
            continue
        closes_4h = df_4h["close"]

        rsi_4h = calculate_rsi(closes_4h)
        bb_low_4h, bb_mid_4h, bb_high_4h = calculate_bollinger_bands(closes_4h)
        ema21_4h = calculate_ema(closes_4h, 21)
        ema50_4h = calculate_ema(closes_4h, 50)

        # === ОТЛАДКА: только print, остальное не тронуто ===
        print(f"\n🔍 Монета: {symbol}")
        print(f"📊 RSI 4H: {rsi_4h:.2f}, BB low: {bb_low_4h:.4f}, Close: {closes_4h.iloc[-1]:.4f}")
        print(f"📈 EMA21: {ema21_4h:.4f}, EMA50: {ema50_4h:.4f}")

        if (
            rsi_4h > 35 or
            closes_4h.iloc[-1] > bb_low_4h or
            closes_4h.iloc[-1] < min(closes_4h[-5:]) or
            ema21_4h < ema50_4h
        ):
            print("❌ Не прошёл фильтр be ready на 4H\n")
            continue

        # BUY сигнал:
        stop = closes_4h.iloc[-1] * 0.97
        target = closes_4h.iloc[-1] * 1.15
        rr = round((target - closes_4h.iloc[-1]) / (closes_4h.iloc[-1] - stop), 1)

        message = f"✅ BUY сигнал: {symbol}\nЦена входа: {closes_4h.iloc[-1]:.4f}\nСтоп: {stop:.4f}\nЦель: {target:.4f}\nR/R = {rr}:1"
        try:
            bot.send_message(chat_id=CHAT_ID, text=message)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

def run():
    while True:
        try:
            scan()
        except Exception as e:
            print("Ошибка в работе:", e)
        time.sleep(180)

if __name__ == "__main__":
    print("🤖 Бот запущен и работает!")
    try:
        bot.send_message(chat_id=CHAT_ID, text="🤖 Бот запущен и работает!")
    except Exception as e:
        print("❌ Ошибка Telegram:", e)
    run()
