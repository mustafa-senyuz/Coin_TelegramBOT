
import os
import sqlite3
from datetime import datetime
from telegram import Bot
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "CHAT_IDS": [-1002281621284, 5637330580],
    "TEST_INTERVAL": 10  # Test every 10 seconds
}

def initialize_db(file_name):
    if not os.path.exists('db'):
        os.makedirs('db')
    
    db_path = os.path.join('db', file_name)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_data (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            value TEXT
        )
    """)
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

def rotate_db(old_db, new_db):
    try:
        if os.path.exists(old_db):
            os.remove(old_db)
        if os.path.exists(new_db):
            os.rename(new_db, old_db)
        print(f"[{datetime.now()}] Database rotated: {new_db} -> {old_db}")
    except Exception as e:
        print(f"[{datetime.now()}] Database rotation error: {str(e)}")

async def send_telegram_message(message, max_retries=3):
    bot = Bot(token=CONFIG["BOT_TOKEN"])
    
    for chat_id in CONFIG["CHAT_IDS"]:
        retries = 0
        while retries < max_retries:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="MarkdownV2"
                )
                print(f"[{datetime.now()}] Message sent to {chat_id}")
                break
            except Exception as e:
                retries += 1
                print(f"[{datetime.now()}] Error sending to {chat_id} (Try {retries}/{max_retries}): {str(e)}")
                await asyncio.sleep(2)

async def main():
    print(f"[{datetime.now()}] Test script started")
    
    # Initialize test databases
    initialize_db('test_1h.db')
    initialize_db('test_24h.db')
    
    test_count = 0
    last_1h_rotation = datetime.now()
    last_24h_rotation = datetime.now()
    
    while True:
        try:
            test_count += 1
            current_time = datetime.now()
            
            # Save test data
            test_value = f"Test value #{test_count}"
            save_test_data('test_1h.db', test_value)
            save_test_data('test_24h.db', test_value)
            
            # Database rotation checks
            if (current_time - last_1h_rotation).total_seconds() >= 3600:
                rotate_db('db/test_1h_old.db', 'db/test_1h.db')
                last_1h_rotation = current_time
            
            if (current_time - last_24h_rotation).total_seconds() >= 86400:
                rotate_db('db/test_24h_old.db', 'db/test_24h.db')
                last_24h_rotation = current_time
            
            # Send test message
            message = f"🔍 *Database Test*\n\n" \
                     f"Test \\#{test_count}\n" \
                     f"Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                     f"Value: {test_value}\n\n" \
                     f"✅ Data saved to databases"
            
            await send_telegram_message(message)
            
            print(f"[{datetime.now()}] Test #{test_count} completed")
            await asyncio.sleep(CONFIG["TEST_INTERVAL"])
            
        except Exception as e:
            print(f"[{datetime.now()}] Error in main loop: {str(e)}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
