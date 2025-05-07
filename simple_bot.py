
import os
from telegram import Bot
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "CHAT_IDS": [-1002281621284, 5637330580],
    "INTERVAL": 60  # Send message every 60 seconds
}

def escape_markdown_v2(text):
    # Characters that need to be escaped in MarkdownV2
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

def create_test_message():
    coins = [
        {"symbol": "BTC", "price": "40000", "change": "+5.2"},
        {"symbol": "ETH", "price": "2000", "change": "+3.1"},
        {"symbol": "BNB", "price": "300", "change": "-1.5"}
    ]
    
    # Create header
    message = ["🚨 *Crypto Alert* 🚨\n"]
    
    # Create table in code block (no need to escape inside code blocks)
    table = ["```",
             "Symbol | Price | Change",
             "-------|--------|--------"]
    
    # Add rows
    for coin in coins:
        row = f"{coin['symbol']} | ${coin['price']} | {coin['change']}%"
        table.append(row)
    
    table.append("```")
    message.extend(table)
    
    # Add timestamp (need to escape special characters)
    timestamp = datetime.now().strftime("%Y\\-%m\\-%d %H:%M:%S")
    message.append(f"\n⏱ Last Update: `{timestamp}`")
    
    return "\n".join(message)

async def send_message(message):
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
    print("Bot started. Press Ctrl+C to stop.")
    while True:
        try:
            message = create_test_message()
            await send_message(message)
            print(f"Waiting {CONFIG['INTERVAL']} seconds...")
            await asyncio.sleep(CONFIG["INTERVAL"])
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
