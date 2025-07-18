
✅ Финальный main.py для V-Разворот бота (с расчётом RSI, EMA, BB и подтверждением второй волны)

import requests import time import math import numpy as np from flask import Flask from telegram import Bot from datetime import datetime

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y" CHAT_ID = 944484522 bot = Bot(token=TOKEN) app = Flask(name)

SYMBOL = "WIFUSDT" INTERVAL = "1h" LIMIT = 100 API_URL = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit={LIMIT}"

sent_buy_signals = set()

📊 Расчёт EMA

def calculate_ema(values, period): ema = [] k = 2 / (period + 1) for i in range(len(values)): if i < period: ema.append(np.mean(values[:i+1])) else: ema.append(values[i] * k + ema[i - 1] * (1 - k)) return ema

📉 Расчёт RSI

def calculate_rsi(closes, period=14): gains, losses = [], [] for i in range(1, len(closes)): delta = closes[i] - closes[i - 1] gains.append(max(delta, 0)) losses.append(abs(min(delta, 0))) avg_gain = np.mean(gains[:period]) avg_loss = np.mean(losses[:period]) rsis = [] for i in range(period, len(gains)): avg_gain = (avg_gain * (period - 1) + gains[i]) / period avg_loss = (avg_loss * (period - 1) + losses[i]) / period rs = avg_gain / avg_loss if avg_loss != 0 else 0 rsis.append(100 - (100 / (1 + rs))) return rsis

📉 Расчёт нижней полосы BB

def calculate_bb_lower(closes, period=20): bb_lower = [] for i in range(period, len(closes)): mean = np.mean(closes[i - period:i]) std = np.std(closes[i - period:i]) bb_lower.append(mean - 2 * std) return bb_lower

✅ Основная проверка BUY сигнала (вторая волна)

def is_confirmed_buy(candles): closes = [float(c[4]) for c in candles] lows = [float(c[3]) for c in candles] volumes = [float(c[5]) for c in candles]

if len(closes) < 60:
    return False, None

ema21 = calculate_ema(closes, 21)
ema50 = calculate_ema(closes, 50)
rsi = calculate_rsi(closes, 14)
bb_lower = calculate_bb_lower(closes, 20)

last_close = closes[-1]
last_low = lows[-1]
last_volume = volumes[-1]
avg_volume = np.mean(volumes[-20:])

# Условия:
if last_volume < avg_volume * 1.2:
    return False, None  # Нет всплеска объёма
if last_close < ema21[-1] or last_close < ema50[-1]:
    return False, None  # Цена не выше EMA21/50
if last_low > bb_lower[-1]:
    return False, None  # Нет касания нижней BB
if rsi[-1] < rsi[-2]:
    return False, None  # RSI не растёт

entry = last_close
stop = min(lows[-5:]) * 0.995
rr = (entry * 2.618 - entry) / (entry - stop)

if rr < 3:
    return False, None

tp1 = round(entry * 1.272, 5)
tp2 = round(entry * 1.618, 5)
tp3 = round(entry * 2.0, 5)
tp4 = round(entry * 2.618, 5)

return True, {
    "entry": entry,
    "stop": round(stop, 5),
    "tp1": tp1,
    "tp2": tp2,
    "tp3": tp3,
    "tp4": tp4,
    "rr": round(rr, 2)
}

🔁 Основной цикл проверки

@app.route('/') def home(): return "✅ V-Reversal bot is alive"

def check_signal(): try: candles = requests.get(API_URL).json() if not candles or len(candles) < 60: return is_buy, data = is_confirmed_buy(candles) if is_buy: signal_id = f"{SYMBOL}_{data['entry']}" if signal_id in sent_buy_signals: return sent_buy_signals.add(signal_id) message = ( f"✅ BUY сигнал по {SYMBOL}\n" f"Цена входа: {data['entry']}\n" f"Stop: {data['stop']}\n" f"TP1: {data['tp1']}\n" f"TP2: {data['tp2']}\n" f"TP3: {data['tp3']}\n" f"TP4: {data['tp4']}\n" f"R/R: {data['rr']}:1" ) bot.send_message(chat_id=CHAT_ID, text=message) except Exception as e: print(f"❌ Ошибка: {e}")

🚀 Запуск

if name == 'main': print("🤖 Бот запущен!") bot.send_message(chat_id=CHAT_ID, text="🤖 Бот на V-разворот запущен!") while True: check_signal() time.sleep(180) app.run(host='0.0.0.0', port=8080)

