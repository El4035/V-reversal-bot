import requests
import time
import threading
from flask import Flask

# --- Telegram конфиг ---
TOKEN = '8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y'
CHAT_ID = '944484522'

# --- Flask для Render ---
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ V-бoт работает!"

# --- Telegram отправка ---
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        requests.post(url, data=payload)
    except:
        pass

# --- Память сигналов ---
sent_ids = set()

# --- Технические расчёты ---
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

def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_bb_low(prices, period=20, std_mult=2):
    sma = sum(prices[-period:]) / period
    std = (sum((p - sma) ** 2 for p in prices[-period:]) / period) ** 0.5
    return sma - std_mult * std

def has_rsi_divergence(closes, rsi_now):
    return closes[-1] < closes[-2] < closes[-3] and rsi_now > calculate_rsi(closes[:-1])

# --- Основная логика V-разворота ---
def analyze_coin(symbol, listed):
    for interval in ['15m', '1h', '4h']:
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
                if signal_id in sent_ids:
                    continue
                sent_ids.add(signal_id)

                message = f"""📈 <b>V-РАЗВОРОТ BUY</b> — <b>{interval}</b>
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
                send_telegram_message(message)
        except:
            continue

# --- Получить список бирж из CoinGecko ---
def get_coin_exchanges(coin_id):
    try:
        url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/tickers'
        r = requests.get(url)
        data = r.json()
        exchanges = set()
        for item in data.get('tickers', []):
            ex = item.get('market', {}).get('name', '').lower()
            if ex:
                exchanges.add(ex)
        return exchanges
    except:
        return set()

# --- Главный цикл сканирования монет ---
def scan_v_reversals():
    while True:
        try:
            print("🔁 Сканирую CoinGecko...")
            url = 'https://api.coingecko.com/api/v3/coins/markets'
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 250,
                'page': 1,
                'sparkline': 'false'
            }
            response = requests.get(url, params=params)
            coins = response.json()

            for coin in coins:
                try:
                    coin_id = coin['id']
                    symbol = coin['symbol'].upper()
                    price = coin['current_price']
                    ath = coin['ath']
                    volume = coin['total_volume']
                    market_cap = coin['market_cap']

                    if ath == 0 or price == 0:
                        continue
                    if price > 5:
                        continue
                    if volume < 1_000_000:
                        continue
                    if market_cap < 5_000_000:
                        continue
                    if symbol in ['USDT', 'BUSD', 'TUSD', 'DAI', 'USD']:
                        continue

                    listed = get_coin_exchanges(coin_id)
                    if not listed or not any(x in listed for x in ['kraken', 'mexc', 'bybit']):
                        continue

                    analyze_coin(symbol, listed)

                except:
                    continue

            time.sleep(180)
        except Exception as e:
            print("Ошибка:", e)
            time.sleep(180)

# --- Запуск бота ---
if __name__ == '__main__':
    send_telegram_message("🤖 Бот V-разворота запущен!")
    print("🚀 Бот запущен и работает...")
    threading.Thread(target=scan_v_reversals).start()
    app.run(host='0.0.0.0', port=10000)
