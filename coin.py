import requests
from telegram import Bot
#from telegram import TelegramBot
from telegram import Bot


import asyncio
from datetime import datetime

# Telegram bot bilgileri


# API bilgileri
API_KEY = "1534b0d1-22db-4969-8419-45bc9b7be9be" # Verdiğiniz API key
API_URL = "https://api.coingecko.com/api/v3/coins/markets" # CoinGecko API URL'si

def get_coins_with_high_volume_change():
    """
    API'den verileri al ve hacmi %60 veya daha fazla artan coinleri filtrele.
    """
    params = {
        "vs_currency": "usd", # Verileri USD cinsinden al
        "order": "volume_desc", # Hacme göre sırala
        "per_page": 100, # En fazla 100 coin getir
        "page": 1, # İlk sayfayı al
        "sparkline": False # Fiyat hareketlerini ekleme
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}" # API anahtarını ekle
    }

    try:
        response = requests.get(API_URL, params=params, headers=headers)
        if response.status_code != 200:
            print(f"API Error: {response.status_code} - {response.text}")
            return []

        coins = response.json()
        alert_coins = []

        for coin in coins:
            # Hacim değişim oranını hesapla (market cap'e göre)
            market_cap = coin.get("market_cap", 0)
            total_volume = coin.get("total_volume", 0)
            
            # Eğer market_cap sıfırsa bölme yapma
            if market_cap > 0:
                volume_change = total_volume / market_cap * 100
                if volume_change >= 60: # Hacmi %60 veya daha fazla artanlar
                    change_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Değişim zamanı
                    alert_coins.append(f"{coin['name']} ({coin['symbol']}): {volume_change:.2f}% - Last Change: {change_time}")
        return alert_coins

    except Exception as e:
        print(f"Error occurred: {e}")
        return []

async def send_alerts():
    """
    Hacim değişimi yüksek coinleri bul ve Telegram'a gönder.
    """
    bot = Bot(token=BOT_TOKEN)
    while True:
        alert_coins = get_coins_with_high_volume_change()
        if alert_coins:
            message = "🚨 High Volume Change Coins (24h):\n" + "\n".join(alert_coins)
            for chat_id in CHAT_IDS:
                await bot.send_message(chat_id=chat_id, text=message)
            print("Alert sent to all groups!")
        else:
            print("No coins with high volume change.")

        # 10 dakika beklemeden sonra tekrar kontrol et
        await asyncio.sleep(600) # 10 dakika bekle (600 saniye)

# Asenkron çalıştırma
if __name__ == "__main__":
    asyncio.run(send_alerts())
    
   
    
