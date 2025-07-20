import time
import threading
import requests
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
    return "✅ Бот V-разворот работает!"

# --- Память сигналов ---
sent_buy = set()

# --- RSI ---
def calculate_rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period or 1e-6
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- EMA ---
def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return ema

# --- BB Low ---
def calculate_bb_low(prices, period=20, std_mult=2):
    sma = sum(prices[-period:]) / period
    std = (sum((p - sma) ** 2 for p in prices[-period:]) / period) ** 0.5
    return sma - std_mult * std

# --- Проверка дивергенции ---
def has_rsi_divergence(closes, rsi_now):
    return closes[-1] < closes[-2] < closes[-3] and rsi_now > calculate_rsi(closes[:-1])

# --- Анализ таймфреймов ---
def check_timeframes(symbol, listed):
    for interval in ["15m", "1h", "4h"]:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit=100"
            r = requests.get(url)
            if r.status_code != 200:
                continue
            candles = r.json()
            closes = [float(c[4]) for c in candles]
            lows = [float(c[3]) for c in candles]
            volumes = [float(c[5]) for c in candles]

            last_close = closes[-1]
            last_low = lows[-1]
            last_volume = volumes[-1]
            prev_volume = volumes[-2]
            rsi_now = calculate_rsi(closes)
            ema21 = calculate_ema(closes[-21:], 21)
            ema50 = calculate_ema(closes[-50:], 50)
            bb_low = calculate_bb_low(closes)
            support = min(lows[-20:])
            rr = (last_close - support) / max((last_close * 0.01), 0.00001)

            if (
                rsi_now <= 35 and last_low <= bb_low
                and ema21 > ema50 and last_close > ema21
                and last_volume > prev_volume * 1.5
                and has_rsi_divergence(closes, rsi_now)
                and rr >= 3
            ):
                diff = last_close - support
                tp1 = round(last_close + diff * 1.272, 4)
                tp2 = round(last_close + diff * 1.618, 4)
                tp3 = round(last_close + diff * 2.0, 4)
                tp4 = round(last_close + diff * 2.618, 4)

                signal_id = f"{symbol}_{interval}_BUY"
                if signal_id not in sent_buy:
                    sent_buy.add(signal_id)
                    msg = f"""📈 <b>V-РАЗВОРОТ BUY</b> — <b>{interval}</b>
<b>{symbol}</b> — ${last_close:.4f}

<b>📍 Поддержка:</b> ${support:.4f}
<b>📍 Стоп:</b> ${support:.4f}
<b>🎯 Цели:</b>
• TP1: ${tp1}
• TP2: ${tp2}
• TP3: ${tp3}
• TP4: ${tp4}

<b>R/R:</b> {round(rr, 2)}:1
Биржи: {', '.join([x.capitalize() for x in listed if x in ['kraken', 'mexc', 'bybit']])}
"""
                    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
        except Exception as e:
            print(f"⚠️ Ошибка в {symbol} [{interval}]: {e}")

# --- Главная функция анализа монет ---
def analyze_market():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 200,
            "page": 1,
            "sparkline": False
        }
        coins = requests.get(url, params=params).json()

        for coin in coins:
            try:
                symbol = coin["symbol"].upper()
                price = coin["current_price"]
                vol = coin["total_volume"]
                cap = coin["market_cap"]
                listed = [e.lower() for e in coin["platforms"].keys()]

                if (
                    price <= 5 and vol >= 1_000_000 and cap >= 5_000_000
                    and not any(x in symbol.lower() for x in ["usd", "usdt", "busd", "tusd", "dai"])
                    and symbol not in ["SCAM", "PIG", "TURD"]
                    and any(x in listed for x in ["kraken", "mexc", "bybit"])
                ):
                    check_timeframes(symbol, listed)
            except Exception as e:
                print(f"⚠️ Ошибка монеты {coin['id']}: {e}")
    except Exception as e:
        print("❌ Ошибка CoinGecko:", e)

# --- Автообновление ---
def run_bot():
    while True:
        analyze_market()
        time.sleep(180)

# --- Запуск ---
if __name__ == '__main__':
    try:
        bot.send_message(chat_id=CHAT_ID, text="🤖 Бот на V-разворот ЗАПУЩЕН!")
        print("✅ Стартовое сообщение Telegram отправлено.")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=8080)
