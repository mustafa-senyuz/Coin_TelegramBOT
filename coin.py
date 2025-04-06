import os
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from telegram import Bot
from telegram.constants import ParseMode
from datetime import datetime

from fastapi import FastAPI
import uvicorn

# SQLAlchemy async modülleri
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import MetaData, Table, Column, String, Float, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select

# Çevresel değişkenler
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # Örneğin: "postgresql+asyncpg://user:password@host:port/dbname"

if not BOT_TOKEN:
    print("⚠️ Hata: BOT_TOKEN çevresel değişken olarak tanımlanmamış!")
    exit(1)
if not DATABASE_URL:
    print("⚠️ Hata: DATABASE_URL çevresel değişken olarak tanımlanmamış!")
    exit(1)

# Yapılandırma
CONFIG = {
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
    "ERROR_RETRY_DELAY": 60,       # Hata durumunda bekleme süresi (saniye)
    "COUNTDOWN_INTERVAL": 30,      # Geri sayım süresi (saniye)
    "COUNTDOWN_STEP": 10           # Geri sayım adım süresi (saniye)
}

# --- VERİTABANI AYARLARI ---
metadata = MetaData()

coin_alerts_old = Table(
    "coin_alerts_old", metadata,
    Column("symbol", String, primary_key=True),
    Column("previous_volume", Float)
)

coin_alerts_1h_old = Table(
    "coin_alerts_1h_old", metadata,
    Column("symbol", String, primary_key=True),
    Column("previous_volume", Float)
)

coin_alerts_24h_old = Table(
    "coin_alerts_24h_old", metadata,
    Column("symbol", String, primary_key=True),
    Column("previous_volume", Float)
)

# Asenkron engine oluşturuluyor.
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async def initialize_db():
    try:
        async with engine.begin() as conn:
            # Tabloları oluştur. Eğer mevcut değilse.
            await conn.run_sync(metadata.create_all)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Veritabanı tabloları oluşturuldu")
    except SQLAlchemyError as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DB oluşturma hatası: {e}")

async def get_previous_volume(table: Table, symbol: str) -> float:
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(table.c.previous_volume).where(table.c.symbol == symbol)
        )
        row = result.scalar()
        return row if row is not None else 0

async def save_current_volume(table: Table, symbol: str, volume: float):
    async with AsyncSession(engine) as session:
        # INSERT or UPDATE
        stmt = table.insert().values(symbol=symbol, previous_volume=volume).on_conflict_do_update(
            index_elements=[table.c.symbol],
            set_={"previous_volume": volume}
        )
        # Eğer on_conflict_do_update desteklenmiyorsa alternatif yöntem kullanılabilir (örneğin, DELETE then INSERT)
        try:
            await session.execute(stmt)
            await session.commit()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {symbol} anlık hacmi güncellendi: {volume}")
        except SQLAlchemyError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DB kaydetme hatası: {e}")

async def rotate_db(table: Table):
    async with AsyncSession(engine) as session:
        try:
            # Tablonun tüm kayıtlarını silmek için:
            await session.execute(table.delete())
            await session.commit()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {table.name} tablosu döndürüldü (sıfırlandı)")
        except SQLAlchemyError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {table.name} döndürme hatası: {e}")

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
    table = f"*{escaped_title}*\n```\n" + " | ".join(escaped_headers) + "\n"
    table += "-|-|-|-\n" + "\n".join(table_rows) + "\n```"
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

# --- ALARM SİSTEMLERİ (ESKI YAPIYA BENZER) ---
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
            previous_volume = await get_previous_volume(coin_alerts_old, symbol)
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
            if price_change >= CONFIG["ALERT_THRESHOLDS"]["pump_threshold"]:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance Pump Alert: {symbol} ({price_change:.1f}%)")
                pump_alerts.append({
                    'symbol': symbol,
                    'price': last_price,
                    'change': price_change
                })
            if low_price > 0 and last_price <= low_price * (1 + CONFIG["ALERT_THRESHOLDS"]["support_deviation"] / 100):
                deviation = ((last_price - low_price) / low_price) * 100
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Binance Support Alert: {symbol} (Deviation: {deviation:.1f}%)")
                support_alerts.append({
                    'symbol': symbol,
                    'price': last_price,
                    'low': low_price,
                    'deviation': deviation
                })
            previous_volume_1h = await get_previous_volume(coin_alerts_1h_old, symbol)
            if previous_volume_1h > 0:
                vol_change_1h = (current_volume / previous_volume_1h - 1) * 100
                if vol_change_1h >= 2:
                    volume_increase_1h.append({
                        'symbol': symbol,
                        'price': last_price,
                        'volume': current_volume,
                        'change': vol_change_1h
                    })
            previous_volume_24h = await get_previous_volume(coin_alerts_24h_old, symbol)
            if previous_volume_24h > 0:
                vol_change_24h = (current_volume / previous_volume_24h - 1) * 100
                if vol_change_24h >= 50:
                    volume_increase_24h.append({
                        'symbol': symbol,
                        'price': last_price,
                        'volume': current_volume,
                        'change': vol_change_24h
                    })
        for symbol, volume in volume_data.items():
            await save_current_volume(coin_alerts_old, symbol, volume)
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
                parse_mode=ParseMode.MARKDOWN_V2,
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

# --- ANA DÖNGÜ: Countdown Dahil ---
async def main_loop():
    global last_1h_rotation, last_24h_rotation
    bot = Bot(token=BOT_TOKEN)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sistem başlatıldı")
    while True:
        try:
            start_time = datetime.now()
            print(f"\n[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Yeni tarama başlatılıyor...")
            
            # Geri sayım
            for remaining in range(CONFIG["COUNTDOWN_INTERVAL"], 0, -CONFIG["COUNTDOWN_STEP"]):
                countdown_message = f"API çağrısına {remaining} saniye kaldı..."
                await send_telegram_message(bot, countdown_message)
                await asyncio.sleep(CONFIG["COUNTDOWN_STEP"])
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] API çağrısına 0 saniye kaldı, veriler çekiliyor...")
            
            cg_volume, cg_support = await fetch_coingecko_data()
            bn_pump, bn_support, bn_inflow, bn_volume, bn_vol_incr_1h, bn_vol_incr_24h = await fetch_binance_data()
            
            message_parts = ["🚨 *CRYPTO ALERT SYSTEM* 🚨\n"]
            
            if cg_volume:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['ratio']:.1f}%"] for item in cg_volume]
                message_parts.append(create_alert_table("COINGECKO VOLUME ALERTS (V/MCAP >20%)", ["Coin", "Price", "Volume", "Ratio"], table_data))
            if cg_support:
                table_data = [[item['symbol'], f"${item['price']:.2f}", f"${item['low']:.2f}", f"{item['deviation']:+.2f}%"] for item in cg_support]
                message_parts.append(create_alert_table("COINGECKO SUPPORT ZONE (Price ≤102% of 24h Low)", ["Coin", "Price", "24h Low", "Deviation"], table_data))
            if bn_pump:
                table_data = [[item['symbol'], f"${item['price']:.2f}", f"{item['change']:.1f}%"] for item in bn_pump]
                message_parts.append(create_alert_table("BINANCE PUMP ALERTS (24h Change >20%)", ["Coin", "Price", "Change"], table_data))
            if bn_support:
                table_data = [[item['symbol'], f"${item['price']:.2f}", f"${item['low']:.2f}", f"{item['deviation']:+.2f}%"] for item in bn_support]
                message_parts.append(create_alert_table("BINANCE SUPPORT ZONE (Price ≤102% of 24h Low)", ["Coin", "Price", "24h Low", "Deviation"], table_data))
            if bn_inflow:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['change']:.2%}"] for item in bn_inflow]
                message_parts.append(create_alert_table("BINANCE INFLOW ALERTS (1h Volume Increase >1%)", ["Coin", "Price", "Volume", "Change"], table_data))
            if bn_volume:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['change']:.2%}"] for item in bn_volume]
                message_parts.append(create_alert_table("BINANCE VOLUME SPIKE (1h Volume Increase >5%)", ["Coin", "Price", "Volume", "Change"], table_data))
            if bn_vol_incr_1h:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['change']:.2f}%"] for item in bn_vol_incr_1h]
                message_parts.append(create_alert_table("BINANCE 1h VOLUME INCREASE (>=2%)", ["Coin", "Price", "Volume", "Change"], table_data))
            else:
                message_parts.append("*BINANCE 1h VOLUME INCREASE (>=2%)*\nNo coins found")
            if bn_vol_incr_24h:
                table_data = [[item['symbol'], f"${item['price']:.2f}", format_volume(item['volume']), f"{item['change']:.2f}%"] for item in bn_vol_incr_24h]
                message_parts.append(create_alert_table("BINANCE 24h VOLUME INCREASE (>=50%)", ["Coin", "Price", "Volume", "Change"], table_data))
            else:
                message_parts.append("*BINANCE 24h VOLUME INCREASE (>=50%)*\nNo coins found")
            
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
            
            # Veritabanı rotasyonu
            await rotate_db(coin_alerts_old)
            now = datetime.now()
            if (now - last_1h_rotation).total_seconds() >= 3600:
                await rotate_db(coin_alerts_1h_old)
                last_1h_rotation = now
            if (now - last_24h_rotation).total_seconds() >= 86400:
                await rotate_db(coin_alerts_24h_old)
                last_24h_rotation = now
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tarama süresi: {duration:.2f}s")
            await asyncio.sleep(CONFIG["SCAN_INTERVAL"])
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Kritik hata: {str(e)}")
            await asyncio.sleep(CONFIG["ERROR_RETRY_DELAY"])
            
# --- WEB SERVİS (FASTAPI) ---
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot Running", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

@app.on_event("startup")
async def startup_event():
    await initialize_db()
    asyncio.create_task(main_loop())

# --- PROGRAMIN BAŞLATILMASI ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("coin:app", host="0.0.0.0", port=port, log_level="info")
