import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv

# .env dosyasını yükle (isteğe bağlı)
load_dotenv()

# Token'ı doğrudan yazabilir veya .env dosyasından çekebilirsin
<<<<<<< HEAD
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7699728190:AAHADXoDkFdEfvgJvW7Wdpf8grcR1smXn5k"
=======
TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN") or "7699728190:AAHADXoDkFdEfvgJvW7Wdpf8grcR1smXn5k"
>>>>>>> faf5feaa4bd403e9c0cf7d5c22aec151262f0e33

# Hedef chat ID'leri
CHAT_IDS = [-1002281621284, 5637330580]

<<<<<<< HEAD
=======

>>>>>>> faf5feaa4bd403e9c0cf7d5c22aec151262f0e33
# Mesajı gönderecek async fonksiyon
async def send_test_messages():
    bot = Bot(token=TOKEN)
    for chat_id in CHAT_IDS:
        try:
<<<<<<< HEAD
            msg = await bot.send_message(chat_id=chat_id, text="✅ Test mesajı: Aktif misin?")
            print(f"Mesaj gönderildi → Chat ID: {chat_id} | Mesaj ID: {msg.message_id}")
        except Exception as e:
            print(f"Hata oluştu → Chat ID: {chat_id} | Hata: {e}")

=======
            msg = await bot.send_message(chat_id=chat_id,
                                         text="✅ Test mesajı: Aktif misin?")
            print(
                f"Mesaj gönderildi → Chat ID: {chat_id} | Mesaj ID: {msg.message_id}"
            )
        except Exception as e:
            print(f"Hata oluştu → Chat ID: {chat_id} | Hata: {e}")


>>>>>>> faf5feaa4bd403e9c0cf7d5c22aec151262f0e33
# Programı başlat
if __name__ == "__main__":
    asyncio.run(send_test_messages())
