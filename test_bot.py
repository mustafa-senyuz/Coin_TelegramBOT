
import os
from telegram import Bot
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "CHAT_IDS": [-1002281621284, 5637330580],
    "INTERVAL": 60  # Her 60 saniyede bir mesaj gönder
}

async def send_test_message(message):
    bot = Bot(token=CONFIG["BOT_TOKEN"])
    
    for chat_id in CONFIG["CHAT_IDS"]:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="MarkdownV2"
            )
            print(f"Message sent to {chat_id}")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error sending to {chat_id}: {str(e)}")

async def main():
    while True:  # Sonsuz döngü
        try:
            # Test message with table
            message = """
🚨 *Test Alert* 🚨

```
Symbol | Price | Change
-------|-------|-------
BTC    | $40K  | +5%
ETH    | $2K   | +3%
```

⏱ Last Update: `2024\-01\-01 12:00:00`
"""
            await send_test_message(message)
            print(f"Waiting {CONFIG['INTERVAL']} seconds...")
            await asyncio.sleep(CONFIG["INTERVAL"])
            
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            await asyncio.sleep(5)  # Hata durumunda 5 saniye bekle

if __name__ == "__main__":
    print("Bot started. Press Ctrl+C to stop.")
    asyncio.run(main())
