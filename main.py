import requests
import time
import csv
from flask import Flask
from threading import Thread

# Telegram
TOKEN = "8111573872:AAE_LGmsgtGmKmOxx2v03Tsd5bL28z9bL3Y"
CHAT_ID = 944484522
TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# Файл логов
LOG_FILE = "signals_log.csv"

# Инициализация Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ V-Reversal bot is running!"

def send_telegram_message(text):
    try:
        requests.post(TG_URL, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print("Telegram error:", e)

def save_signal_log(data):
    with open(LOG_FILE, "a", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)

def check_signals():
    while True:
        try:
            # Получение монет с CoinGecko
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 200,
                "page": 1,
                "sparkline": "false"
            }
            response = requests.get(url, params=params).json()

            for coin in response:
                try:
                    # Фильтры
                    price = coin['current_price']
                    volume = coin['total_volume']
                    market_cap = coin['market_cap']
                    ath = coin['ath']
                    ath_change = (price - ath) / ath * 100
                    name = coin['name']
                    symbol = coin['symbol'].upper()
                    id = coin['id']
                    exchanges = ['kraken', 'mexc', 'bybit']
                    listed = [e for e in exchanges if e in [m['market']['name'].lower() for m in requests.get(f"https://api.coingecko.com/api/v3/coins/{id}/tickers").json()['tickers']]]

                    if price > 3 or volume < 1_000_000 or market_cap < 5_000_000:
                        continue
                    if "usd" in symbol.lower() or any(bad in symbol.lower() for bad in ["scam", "pig", "turd"]):
                        continue

                    # Проверка падения от ATH
                    if ath > 0 and ath_change <= -80:
                        # Расчёт целей
                        tp1 = round(price * 1.272, 4)
                        tp2 = round(price * 1.618, 4)
                        tp3 = round(price * 2.0, 4)
                        tp4 = round(price * 2.618, 4)
                        stop = round(price * 0.97, 4)  # стоп = -3%
                        rr = round((tp4 - price) / (price - stop), 1)

                        if rr < 3:
                            continue

                        # High Potential?
                        tag = "🔥 High Potential!" if tp4 >= price * 3 else ""

                        # Сообщение
                        message = (
                            f"📈 BUY сигнал на разворот\n"
                            f"🔹 Coin: {name} (${symbol})\n"
                            f"💰 Цена: ${price}\n"
                            f"📉 Падение от ATH: {round(ath_change, 2)}%\n"
                            f"🎯 TP1: ${tp1}\n"
                            f"🎯 TP2: ${tp2}\n"
                            f"🎯 TP3: ${tp3}\n"
                            f"🎯 TP4: ${tp4}\n"
                            f"🛑 Стоп: ${stop}\n"
                            f"⚖️ R/R: {rr}:1\n"
                            f"📊 Биржи: {', '.join(listed)}\n"
                            f"{tag}"
                        )

                        send_telegram_message(message)
                        save_signal_log([name, symbol, price, stop, tp1, tp2, tp3, tp4, rr, tag])
                        time.sleep(1)

                except Exception as e:
                    print("Ошибка при проверке монеты:", e)

        except Exception as e:
            print("Ошибка основного цикла:", e)

        time.sleep(180)

def start_bot():
    send_telegram_message("🤖 Бот на V‑разворот запущен!")
    check_signals()

# Запуск бота в потоке
t = Thread(target=start_bot)
t.daemon = True
t.start()

# Запуск сервера Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
