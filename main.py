import requests import time import csv import os import math from datetime import datetime from flask import Flask from telegram import Bot

TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y" CHAT_ID = "944484522" bot = Bot(token=TOKEN)

app = Flask(name)

sent_signals = set()

def fetch_top_200(): url = "https://api.coingecko.com/api/v3/coins/markets" params = { "vs_currency": "usd", "order": "market_cap_desc", "per_page": 200, "page": 1, "price_change_percentage": "24h" } return requests.get(url, params=params).json()

def get_ohlcv(symbol): try: url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1h&limit=100" response = requests.get(url) data = response.json() closes = [float(candle[4]) for candle in data] lows = [float(candle[3]) for candle in data] highs = [float(candle[2]) for candle in data] volumes = [float(candle[5]) for candle in data] return closes, lows, highs, volumes except: return [], [], [], []

def calculate_rsi(closes, period=14): if len(closes) < period: return 100 deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)] gains = [delta if delta > 0 else 0 for delta in deltas[-period:]] losses = [-delta if delta < 0 else 0 for delta in deltas[-period:]] avg_gain = sum(gains) / period avg_loss = sum(losses) / period if sum(losses) != 0 else 1e-10 rs = avg_gain / avg_loss return 100 - (100 / (1 + rs))

def calculate_ema(data, period): if len(data) < period: return data[-1] k = 2 / (period + 1) ema = data[0] for price in data[1:]: ema = price * k + ema * (1 - k) return ema

def calculate_bollinger_bands(closes, period=20): if len(closes) < period: return 0, 0 sma = sum(closes[-period:]) / period std = math.sqrt(sum((c - sma) ** 2 for c in closes[-period:]) / period) return sma - 2 * std, sma + 2 * std

def calculate_tp_levels(entry, stop): diff = entry - stop return [round(entry + diff * fib, 5) for fib in [1.272, 1.618, 2.0, 2.618]]

def analyze(): coins = fetch_top_200() for coin in coins: try: symbol = coin['symbol'].upper() if any(x in symbol for x in ["USD", "USDT", "BUSD", "DAI", "TUSD"]): continue if coin['current_price'] > 3 or coin['market_cap'] < 5_000_000 or coin['total_volume'] < 1_000_000: continue tickers = [m['market']['name'] for m in requests.get(f"https://api.coingecko.com/api/v3/coins/{coin['id']}").json()['tickers']] if not any(ex in tickers for ex in ["MEXC", "Kraken", "Bybit"]): continue

price = coin['current_price']
        ath = coin['ath']
        drop = (ath - price) / ath
        if drop < 0.75:
            continue

        closes, lows, highs, volumes = get_ohlcv(symbol)
        if not closes or len(closes) < 30:
            continue

        rsi = calculate_rsi(closes)
        if rsi > 35:
            continue

        ema21 = calculate_ema(closes[-21:], 21)
        if price < ema21:
            continue

        lower_bb, upper_bb = calculate_bollinger_bands(closes)
        if price > lower_bb:
            continue

        if volumes[-1] < sum(volumes[-5:]) / 5:
            continue

        if closes[-1] > closes[-2] and rsi > calculate_rsi(closes[:-1]):
            stop = round(min(lows[-5:]), 5)
            if (price - stop) / price > 0.05:
                continue

            tps = calculate_tp_levels(price, stop)
            rr = round((tps[3] - price) / (price - stop), 1)
            if rr < 3:
                continue

            signal_id = f"{symbol}-{round(price, 5)}"
            if signal_id in sent_signals:
                continue
            sent_signals.add(signal_id)

            msg = f"✅ BUY SIGNAL — {symbol}\nPrice: ${price}\nStop: ${stop}\nTP1: ${tps[0]}\nTP2: ${tps[1]}\nTP3: ${tps[2]}\nTP4: ${tps[3]}\nR/R: {rr}:1"
            bot.send_message(chat_id=CHAT_ID, text=msg)
            with open("signals_log.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now(), symbol, price, stop, *tps, rr])

    except Exception as e:
        print("Error:", e)

@app.route("/") def home(): return "V-reversal bot is running!"

if name == "main": bot.send_message(chat_id=CHAT_ID, text="🤖 V-reversal бот запущен!") while True: analyze() time.sleep(180)


