import os
import time
from datetime import datetime
import telebot
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "CHAT_IDS": [-1002281621284, 5637330580],
    "INTERVAL": 60  # Send message every 60 seconds
}


class TelegramBot:

    def __init__(self, token, chat_ids, interval):
        self.bot = telebot.TeleBot(token)
        self.chat_ids = chat_ids
        self.interval = interval

    def escape_markdown_v2(self, text: str) -> str:
        escape_chars = '_*[]()~`>#+-=|{}.!'
        return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

    def create_test_message(self) -> str:
        coins = [
            {
                "symbol": "BTC",
                "price": "40000",
                "change": "+5.2"
            },
            {
                "symbol": "ETH",
                "price": "2000",
                "change": "+3.1"
            },
            {
                "symbol": "BNB",
                "price": "300",
                "change": "-1.5"
            },
        ]

        # Başlık
        message = ["🚨 *Crypto Alert* 🚨\n"]

        # Kod bloğu içinde tablo (kaçış gerekmiyor)
        table = ["```", "Symbol | Price | Change", "-------|--------|--------"]
        for coin in coins:
            row = f"{coin['symbol']} | ${coin['price']} | {coin['change']}%"
            table.append(row)
        table.append("```")
        message.extend(table)

        # Zaman damgası ve kaçış
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts_escaped = self.escape_markdown_v2(ts)
        message.append(f"\n⏱ Last Update: `{ts_escaped}`")

        return "\n".join(message)

    def send_messages(self, message: str):
        for chat_id in self.chat_ids:
            try:
                self.bot.send_message(chat_id,
                                      message,
                                      parse_mode="MarkdownV2")
                print(f"✅ Message sent to {chat_id}")
            except Exception as e:
                print(f"❌ Error sending to {chat_id}: {e}")

    def start(self):
        print("Bot (sync) starting... Press Ctrl+C to stop.")
        while True:
            msg = self.create_test_message()
            self.send_messages(msg)
            print(f"⏳ Waiting {self.interval} seconds...\n")
            time.sleep(self.interval)


if __name__ == "__main__":
    bot = TelegramBot(CONFIG["BOT_TOKEN"], CONFIG["CHAT_IDS"],
                      CONFIG["INTERVAL"])
    bot.start()
