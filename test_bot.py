
import os
from telegram import Bot
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "CHAT_IDS": [-1002281621284, 5637330580]
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
    # Test message with code block
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

if __name__ == "__main__":
    asyncio.run(main())
