import requests 
import sqlite3
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from telegram import Bot 
from datetime import datetime

import json
import subprocess

def save_alert_to_json(symbol):
    # alerts.json dosyasını oku veya oluştur
    if os.path.exists("alerts.json"):
        with open("alerts.json", "r") as f:
            data = json.load(f)
    else:
        data = {}

    # Sembol zaten varsa, tekrar yazma
    if symbol not in data:
        data[symbol] = "alert_sent"
        with open("alerts.json", "w") as f:
            json.dump(data, f, indent=4)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {symbol} alerts.json dosyasına kaydedildi.")
        git_push()  # JSON dosyasını GitHub'a gönder
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {symbol} zaten alerts.json içinde var.")

def git_push():
    subprocess.run(["git", "config", "--global", "user.name", "mustafacoding"])
    subprocess.run(["git", "config", "--global", "user.email", "youremail@example.com"])
    subprocess.run(["git", "add", "alerts.json"])
    subprocess.run(["git", "commit", "-m", "update alerts"])
    subprocess.run(["git", "push", "origin", "main"])

# Yapılandırma
CONFIG = {
     # Çevresel değişkenler
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "CHAT_IDS": [-1002281621284, 5637330580],
    "ALERT_THRESHOLDS": {
        "volume_ratio": 20,        # V/MCAP oranı (%)
        "support_deviation": 2,    # Destek seviyesinden sapma (%)
        "pump_threshold": 20,      # Pump alarm eşiği (%)
        "inflow_threshold": 1,     # Inflow artış eşiği (%)
        "volume_spike": 5          # Hacim artış eşiği (%)
    },
    "API_URLS": {
        "coingecko": "https://api.coingecko.com/api/v3/coins/markets",
        "binance": "https://api.binance.com/api/v3/ticker/24hr"
    },
    "SCAN_INTERVAL": 30,           # Tarama aralığı (saniye)
    "ERROR_RETRY_DELAY": 60        # Hata durumunda bekleme süresi (saniye)
}

# --- VERİTABANI YÖNETİMİ ---
def initialize_db(file_name):
    if not os.path.exists(file_name):
        conn = sqlite3.connect(file_name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coin_volumes (
                symbol TEXT PRIMARY KEY,
                previous_volume REAL
            )
        """)
        conn.commit()
        conn.close()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Veritabanı başlatıldı: {file_name}")

def get_previous_volume(symbol):
    if not os.path.exists("coin_alertsOLD.db"):
        return 0
    conn = sqlite3.connect("coin_alertsOLD.db")
    cursor = conn.cursor()
    cursor.execute("SELECT previous_volume FROM coin_volumes WHERE symbol = ?", (symbol,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def save_current_volume(symbol, volume):
    conn = sqlite3.connect("coin_alertsNEW.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coin_volumes (
            symbol TEXT PRIMARY KEY,
            previous_volume REAL
        )
    """)
    cursor.execute("INSERT OR REPLACE INTO coin_volumes (symbol, previous_volume) VALUES (?, ?)", (symbol, volume))
    conn.commit()
    conn.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {symbol} anlık hacmi güncellendi: {volume}")

def rotate_db():
    try:
        if os.path.exists("coin_alertsOLD.db"):
            os.remove("coin_alertsOLD.db")
        if os.path.exists("coin_alertsNEW.db"):
            os.rename("coin_alertsNEW.db", "coin_alertsOLD.db")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Anlık veritabanı döndürüldü")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Anlık DB döndürme hatası: {str(e)}")

# 1h DB yönetimi
def get_previous_volume_1h(symbol):
    if not os.path.exists("coin_alerts1h_OLD.db"):
        return 0
    conn = sqlite3.connect("coin_alerts1h_OLD.db")
    cursor = conn.cursor()
    cursor.execute("SELECT previous_volume FROM coin_volumes WHERE symbol = ?", (symbol,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def save_current_volume_1h(symbol, volume):
    conn = sqlite3.connect("coin_alerts1h_NEW.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coin_volumes (
            symbol TEXT PRIMARY KEY,
            previous_volume REAL
        )
    """)
    cursor.execute("INSERT OR REPLACE INTO coin_volumes (symbol, previous_volume) VALUES (?, ?)", (symbol, volume))
    conn.commit()
    conn.close()

def rotate_db_1h():
    try:
        if os.path.exists("coin_alerts1h_OLD.db"):
            os.remove("coin_alerts1h_OLD.db")
        if os.path.exists("coin_alerts1h_NEW.db"):
            os.rename("coin_alerts1h_NEW.db", "coin_alerts1h_OLD.db")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 1h veritabanı döndürüldü")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 1h DB döndürme hatası: {str(e)}")

# 24h DB yönetimi
def get_previous_volume_24h(symbol):
    if not os.path.exists("coin_alerts24h_OLD.db"):
        return 0
    conn = sqlite3.connect("coin_alerts24h_OLD.db")
    cursor = conn.cursor()
    cursor.execute("SELECT previous_volume FROM coin_volumes WHERE symbol = ?", (symbol,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def save_current_volume_24h(symbol, volume):
    conn = sqlite3.connect("coin_alerts24h_NEW.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coin_volumes (
            symbol TEXT PRIMARY KEY,
            previous_volume REAL
        )
    """)
    cursor.execute("INSERT OR REPLACE INTO coin_volumes (symbol, previous_volume) VALUES (?, ?)", (symbol, volume))
    conn.commit()
    conn.close()

def rotate_db_24h():
    try:
        if os.path.exists("coin_alerts24h_OLD.db"):
            os.remove("coin_alerts24h_OLD.db")
        if os.path.exists("coin_alerts24h_NEW.db"):
            os.rename("coin_alerts24h_NEW.db", "coin_alerts24h_OLD.db")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 24h veritabanı döndürüldü")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 24h DB döndürme hatası: {str(e)}")

def initialize_databases():
    initialize_db("coin_alertsOLD.db")
    initialize_db("coin_alerts1h_OLD.db")
    initialize_db("coin_alerts24h_OLD.db")

# --- YARDIMCI FONKSİYONLAR ---
def format_volume(volume):
    if volume >= 1_000_000_000:
        return f"{volume/1_000_000_000:.1f}B"
    elif volume >= 1_000_000:
        return f"{volume/1_000_000:.1f}M"
    elif volume >= 1_000:
        return f"{volume/1_000:.1f}K"
    return f"{volume:.2f}"

def escape_markdown(text):
    escape_chars = {'_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'}
    return ''.join(['\\' + char if char in escape_chars else char for char in str(text)])

def create_alert_table(title, headers, data):
    escaped_title = escape_markdown(title)
    escaped_headers = [escape_markdown(h) for h in headers]
    
    table_rows = []
    for row in data:
        escaped_row = [escape_markdown(str(cell).replace('`', '\\`')) for cell in row]
        table_rows.append(" | ".join(escaped_row))

    table = f"*{escaped_title}*\n```\n"
    table += " | ".join(escaped_headers) + "\n"
    table += "-|-|-|-\n"
    table += "\n".join(table_rows) + "\n```"
    return table

def split_long_message(full_message, max_length=4096):
    parts = []
    current_part = []
    current_length = 0
    in_code_block = False

    for line in full_message.split('\n'):
        line_length = len(line) + 1
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        if current_length + line_length > max_length:
            if in_code_block:
                current_part.append('```')
                in_code_block = False
            parts.append('\n'.join(current_part))
            current_part = []
            current_length = 0
            if line.strip().startswith('```'):
                in_code_block = True
        current_part.append(line)
        current_length += line_length
    if current_part:
        if in_code_block:
            current_part.append('```')
        parts.append('\n'.join(current_part))
    return parts

# --- ALARM SİSTEMLERİ ---
async def fetch_coingecko_data():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CoinGecko verileri çekiliyor...")
    try:
        params = {"vs_currency": "usd", "order": "volume_desc", "per_page": 100}
        with ThreadPoolExecutor() as executor:
            response = await asyncio.get_event_loop().run_in_executor(executor, requests.get, CONFIG["API_URLS"]["coingecko"], params)
        coins = response.json()

        volume_alerts = []
        support_alerts = []
        
        for coin in coins:
            symbol = coin['symbol'].upper()
            market_cap = coin.get('market_cap', 0)
            volume = coin.get('total_volume', 0)
            if market_cap and volume and market_cap > 0:
                ratio = (volume / market_cap) * 100
                if ratio >= CONFIG["ALERT_THRESHOLDS"]["volume_ratio"]:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CoinGecko Volume Alert: {symbol} (V/MCAP: {ratio:.1f}%)")
                    volume_alerts.append({
                        'symbol': symbol,
                        'price': coin['current_price'],
                        'volume': volume,
                        'ratio': ratio
                    })
            low_price = coin.get('low_24h', 0)
            current_price = coin.get('current_price', 0)
            if low_price and current_price and low_price > 0:
                deviation = ((current_price - low_price) / low_price) * 100
                if deviation <= CONFIG["ALERT_THRESHOLDS"]["support_deviation"]:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CoinGecko Support Alert: {symbol} (Deviation: {deviation:.1f}%)")
                    support_alerts.append({
                        'symbol': symbol,
                        'price': current_price,
                        'low': low_price,
                        'deviation': deviation
                    })
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CoinGecko taraması tamamlandı: {len(volume_alerts)} volume, {len(support_alerts)} support alert")
        return volume_alerts, support_alerts
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CoinGecko hatası: {str(e)}")
        return [], []

async def fetch_binance_data():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance verileri çekiliyor...")
    try:
        with ThreadPoolExecutor() as executor:
            response = await asyncio.get_event_loop().run_in_executor(executor, requests.get, CONFIG["API_URLS"]["binance"])
        tickers = response.json()

        pump_alerts = []
        support_alerts = []
        inflow_alerts = []
        volume_spike_alerts = []
        # EKSTRA: 1h ve 24h volume increase listeleri
        volume_increase_1h = []
        volume_increase_24h = []
        volume_data = {}

        for ticker in tickers:
            symbol = ticker['symbol'].replace('USDT', '')
            try:
                last_price = float(ticker['lastPrice'])
                low_price = float(ticker['lowPrice'])
                price_change = float(ticker['priceChangePercent'])
                current_volume = float(ticker['quoteVolume'])
            except Exception:
                continue

            # Anlık hesaplamalar (inflow, volume spike)
            previous_volume = get_previous_volume(symbol)
            volume_data[symbol] = current_volume
            if previous_volume > 0:
                inflow_change = (current_volume / previous_volume) - 1
                if inflow_change >= CONFIG["ALERT_THRESHOLDS"]["inflow_threshold"] / 100:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance Inflow Alert: {symbol} ({inflow_change:.2%})")
                    inflow_alerts.append({
                        'symbol': symbol,
                        'price': last_price,
                        'volume': current_volume,
                        'change': inflow_change
                    })
                volume_change = (current_volume / previous_volume) - 1
                if volume_change >= CONFIG["ALERT_THRESHOLDS"]["volume_spike"] / 100:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance Volume Alert: {symbol} ({volume_change:.2%})")
                    volume_spike_alerts.append({
                        'symbol': symbol,
                        'price': last_price,
                        'volume': current_volume,
                        'change': volume_change
                    })

            # Pump Alarmı
            if price_change >= CONFIG["ALERT_THRESHOLDS"]["pump_threshold"]:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance Pump Alert: {symbol} ({price_change:.1f}%)")
                pump_alerts.append({
                    'symbol': symbol,
                    'price': last_price,
                    'change': price_change
                })

            # Support Zone Alarmı
            if low_price > 0 and last_price <= low_price * (1 + CONFIG["ALERT_THRESHOLDS"]["support_deviation"] / 100):
                deviation = ((last_price - low_price) / low_price) * 100
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance Support Alert: {symbol} (Deviation: {deviation:.1f}%)")
                support_alerts.append({
                    'symbol': symbol,
                    'price': last_price,
                    'low': low_price,
                    'deviation': deviation
                })

            # --- EKSTRA: 1h Volume Increase (>=2%) ---
            previous_volume_1h = get_previous_volume_1h(symbol)
            if previous_volume_1h > 0:
                vol_change_1h = (current_volume / previous_volume_1h - 1) * 100
                if vol_change_1h >= 2:
                    volume_increase_1h.append({
                        'symbol': symbol,
                        'price': last_price,
                        'volume': current_volume,
                        'change': vol_change_1h
                    })
            # --- EKSTRA: 24h Volume Increase (>=50%) ---
            previous_volume_24h = get_previous_volume_24h(symbol)
            if previous_volume_24h > 0:
                vol_change_24h = (current_volume / previous_volume_24h - 1) * 100
                if vol_change_24h >= 50:
                    volume_increase_24h.append({
                        'symbol': symbol,
                        'price': last_price,
                        'volume': current_volume,
                        'change': vol_change_24h
                    })
        # Tüm coinlerin anlık verilerini kaydet
        for symbol, volume in volume_data.items():
            save_current_volume(symbol, volume)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance taraması tamamlandı: {len(pump_alerts)} pump, {len(support_alerts)} support, {len(inflow_alerts)} inflow, {len(volume_spike_alerts)} volume")
        return pump_alerts, support_alerts, inflow_alerts, volume_spike_alerts, volume_increase_1h, volume_increase_24h
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance hatası: {str(e)}")
        return [], [], [], [], [], []

# --- MESAJ YÖNETİMİ ---
async def send_telegram_message(bot, message):
    success = True
    for chat_id in CONFIG["CHAT_IDS"]:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {chat_id} için mesaj gönderme hatası: {str(e)}")
            success = False
    return success

# --- ZAMAN AYARLARI ---
last_1h_rotation = datetime.now()
last_24h_rotation = datetime.now()

# --- ANA DÖNGÜ ---
async def main_loop():
    global last_1h_rotation, last_24h_rotation
    bot = Bot(token=CONFIG["BOT_TOKEN"])
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sistem başlatıldı")
    while True:
        try:
            start_time = datetime.now()
            print(f"\n[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Yeni tarama başlatılıyor...")
            
            # Veri çekme
            cg_volume, cg_support = await fetch_coingecko_data()
            bn_pump, bn_support, bn_inflow, bn_volume, bn_vol_incr_1h, bn_vol_incr_24h = await fetch_binance_data()
            
            # Mesaj oluşturma
            message_parts = ["🚨 *CRYPTO ALERT SYSTEM* 🚨\n"]
            
            # CoinGecko Volume Alerts
            if cg_volume:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['ratio']:.1f}%"] for item in cg_volume]
                message_parts.append(create_alert_table("COINGECKO VOLUME ALERTS (V/MCAP >20%)", ["Coin", "Price", "Volume", "Ratio"], table_data))
            # CoinGecko Support Alerts
            if cg_support:
                table_data = [[item['symbol'], f"${item['price']:.2f}", f"${item['low']:.2f}", f"{item['deviation']:+.2f}%"] for item in cg_support]
                message_parts.append(create_alert_table("COINGECKO SUPPORT ZONE (Price ≤102% of 24h Low)", ["Coin", "Price", "24h Low", "Deviation"], table_data))
            # Binance Pump Alerts
            if bn_pump:
                table_data = [[item['symbol'], f"${item['price']:.2f}", f"{item['change']:.1f}%"] for item in bn_pump]
                message_parts.append(create_alert_table("BINANCE PUMP ALERTS (24h Change >20%)", ["Coin", "Price", "Change"], table_data))
            # Binance Support Alerts
            if bn_support:
                table_data = [[item['symbol'], f"${item['price']:.2f}", f"${item['low']:.2f}", f"{item['deviation']:+.2f}%"] for item in bn_support]
                message_parts.append(create_alert_table("BINANCE SUPPORT ZONE (Price ≤102% of 24h Low)", ["Coin", "Price", "24h Low", "Deviation"], table_data))
            # Binance Inflow Alerts
            if bn_inflow:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['change']:.2%}"] for item in bn_inflow]
                message_parts.append(create_alert_table("BINANCE INFLOW ALERTS (1h Volume Increase >1%)", ["Coin", "Price", "Volume", "Change"], table_data))
            # Binance Volume Spike Alerts
            if bn_volume:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['change']:.2%}"] for item in bn_volume]
                message_parts.append(create_alert_table("BINANCE VOLUME SPIKE (1h Volume Increase >5%)", ["Coin", "Price", "Volume", "Change"], table_data))
            # --- EKSTRA: 1h Volume Increase (>=2%) ---
            if bn_vol_incr_1h:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['change']:.2f}%"] for item in bn_vol_incr_1h]
                message_parts.append(create_alert_table("BINANCE 1h VOLUME INCREASE (>=2%)", ["Coin", "Price", "Volume", "Change"], table_data))
            else:
                message_parts.append("*BINANCE 1h VOLUME INCREASE (>=2%)*\nNo coins found")
            # --- EKSTRA: 24h Volume Increase (>=50%) ---
            if bn_vol_incr_24h:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['change']:.2f}%"] for item in bn_vol_incr_24h]
                message_parts.append(create_alert_table("BINANCE 24h VOLUME INCREASE (>=50%)", ["Coin", "Price", "Volume", "Change"], table_data))
            else:
                message_parts.append("*BINANCE 24h VOLUME INCREASE (>=50%)*\nNo coins found")
            
            # Footer
            if len(message_parts) > 1:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message_parts.append(f"\n⏱ *Son Güncelleme:* `{escape_markdown(timestamp)}`")
                full_message = '\n'.join(message_parts)
                parts = split_long_message(full_message)
                for part in parts:
                    success = await send_telegram_message(bot, part)
                    if not success:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mesaj gönderilemedi")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {len(parts)} mesaj başarıyla gönderildi")
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Yeni alarm bulunamadı")
            
            # Veritabanı rotasyonu: Anlık DB her taramada döndürülüyor
            rotate_db()
            # 1h ve 24h rotasyonu zaman kontrolleri
            now = datetime.now()
            if (now - last_1h_rotation).total_seconds() >= 3600:
                rotate_db_1h()
                last_1h_rotation = now
            if (now - last_24h_rotation).total_seconds() >= 86400:
                rotate_db_24h()
                last_24h_rotation = now
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tarama süresi: {duration:.2f}s")
            await asyncio.sleep(CONFIG["SCAN_INTERVAL"])
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Kritik hata: {str(e)}")
            await asyncio.sleep(CONFIG["ERROR_RETRY_DELAY"])

# --- PROGRAMIN BAŞLATILMASI ---
if __name__ == "__main__":
    try:
        initialize_databases()
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bot kapatılıyor...")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Beklenmeyen hata: {str(e)}")
