import requests
import sqlite3
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from telegram import Bot
from datetime import datetime
import json
import subprocess
from dotenv import load_dotenv
from flask import Flask, jsonify
import threading
from threading import Thread

load_dotenv()

# Configuration
CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "CHAT_IDS": [-1002281621284, 5637330580],
    "TEST_INTERVAL": 10  # Test every 10 seconds
}


# Initialize and handle database
def initialize_db(file_name):
    if not os.path.exists('db'):
        os.makedirs('db')

    db_path = os.path.join('db', file_name)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS test_data (id INTEGER PRIMARY KEY, timestamp TEXT, value TEXT)"""
    )
    conn.commit()
    conn.close()
    print(f"[{datetime.now()}] Database initialized: {db_path}")


def save_test_data(db_name, value):
    db_path = os.path.join('db', db_name)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO test_data (timestamp, value) VALUES (?, ?)",
                   (timestamp, value))
    conn.commit()
    conn.close()
    print(f"[{datetime.now()}] Data saved to {db_path}: {value}")


async def send_telegram_message(message, max_retries=3):
    bot = Bot(token=CONFIG["BOT_TOKEN"])
    for chat_id in CONFIG["CHAT_IDS"]:
        retries = 0
        while retries < max_retries:
            try:
                await bot.send_message(chat_id=chat_id,
                                       text=message,
                                       parse_mode="MarkdownV2")
                print(f"[{datetime.now()}] Message sent to {chat_id}")
                break
            except Exception as e:
                retries += 1
                print(
                    f"[{datetime.now()}] Error sending to {chat_id} (Try {retries}/{max_retries}): {str(e)}"
                )
                await asyncio.sleep(2)


def format_data_as_table():
    db_path = os.path.join('db', 'test_1h.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, value FROM test_data")
    rows = cursor.fetchall()
    conn.close()

    table_lines = [
        "*Database Data Table*:\n", "```", "Timestamp | Value",
        "----------|------"
    ]
    for row in rows:
        table_lines.append(f"{row[0]} | {row[1]}")
    table_lines.append("```")

    return "\n".join(table_lines)


async def main():
    print(f"[{datetime.now()}] Test script started")
    initialize_db('test_1h.db')

    test_count = 0
    while True:
        try:
            test_count += 1
            test_value = f"Test value #{test_count}"
            save_test_data('test_1h.db', test_value)

            # Send the formatted data as a message
            table_message = format_data_as_table()
            await send_telegram_message(table_message)

            print(f"[{datetime.now()}] Test #{test_count} completed")
            await asyncio.sleep(CONFIG["TEST_INTERVAL"])
        except Exception as e:
            print(f"[{datetime.now()}] Error in main loop: {str(e)}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
