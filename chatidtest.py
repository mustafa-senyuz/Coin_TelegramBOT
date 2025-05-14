import os
import time
from dotenv import load_dotenv
import telebot

# .env dosyasını yükle
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")  # veya direkt TOKEN = "xxx"       "BOT_TOKEN":

# Botu başlat
bot = telebot.TeleBot(TOKEN)

# Hedef chat ID'leri
CHAT_IDS = [-1002281621284, 5637330580]
INTERVAL = 60  # saniye


def create_test_message():
    return "✅ Test mesajı: Bot çalışıyor ve sen aktifsin!"


if __name__ == "__main__":
    print("Bot starting (synchronous)... Press Ctrl+C to stop.")
    while True:
        text = create_test_message()
        for chat_id in CHAT_IDS:
            try:
                bot.send_message(chat_id, text)
                print(f"✔️ Mesaj gönderildi → {chat_id}")
            except Exception as e:
                print(f"❌ Mesaj gönderilemedi → {chat_id} | Hata: {e}")
        time.sleep(INTERVAL)
