import os
import time
import sqlite3
import subprocess
from datetime import datetime
import telebot
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Configuration
CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "CHAT_IDS": [-1002281621284, 5637330580],
    "TEST_INTERVAL": 10  # Test every 10 seconds
}


# MarkdownV2 için kaçış fonksiyonu
def escape_markdown_v2(text: str) -> str:
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)


# Senkron Telegram botu
bot = telebot.TeleBot(CONFIG["BOT_TOKEN"])


def remove_git_lock():
    lock_path = os.path.join('.git', 'refs', 'remotes', 'origin', 'main.lock')
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
            print(f"[{datetime.now()}] Removed git lock file: {lock_path}")
        except Exception as e:
            print(f"[{datetime.now()}] Failed to remove git lock: {e}")


def git_push():
    try:
        remove_git_lock()

        subprocess.run(
            ["git", "config", "--global", "user.name", "mustafa-senyuz"],
            check=True,
            capture_output=True,
            text=True)
        subprocess.run([
            "git", "config", "--global", "user.email",
            "mustafasenyuz.git@gmail.com"
        ],
                       check=True,
                       capture_output=True,
                       text=True)

        BOT_PAT = os.getenv("BOT_PAT")
        if not BOT_PAT:
            raise Exception("BOT_PAT ortam değişkeni tanımlı değil!")

        repo_url = f"https://{BOT_PAT}@github.com/mustafa-senyuz/Coin_TelegramBOT.git"
        subprocess.run(["git", "remote", "set-url", "origin", repo_url],
                       check=True)

        subprocess.run(["git", "add", "-A"], check=True)
        status = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True,
                                text=True).stdout.strip()

        if status:
            subprocess.run(["git", "commit", "-m", "Auto update from script"],
                           check=True)
            remove_git_lock()
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print(f"[{datetime.now()}] Değişiklikler başarıyla push edildi")
        else:
            print(f"[{datetime.now()}] Değişiklik yok, push işlemi atlandı")

    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Git hatası: {e}")
    except Exception as e:
        print(f"[{datetime.now()}] Hata: {e}")


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
        print(f"[{datetime.now()}] Database rotation error: {e}")


def send_telegram_message(message: str, max_retries=3):
    for chat_id in CONFIG["CHAT_IDS"]:
        retries = 0
        while retries < max_retries:
            try:
                bot.send_message(chat_id, message, parse_mode="MarkdownV2")
                print(f"[{datetime.now()}] Message sent to {chat_id}")
                break
            except Exception as e:
                retries += 1
                print(
                    f"[{datetime.now()}] Error sending to {chat_id} (Try {retries}/{max_retries}): {e}"
                )
                time.sleep(2)


def main():
    print(f"[{datetime.now()}] Test script started")

    initialize_db('test_1h.db')
    initialize_db('test_24h.db')

    test_count = 0
    last_1h_rotation = datetime.now()
    last_24h_rotation = datetime.now()

    while True:
        try:
            test_count += 1
            current_time = datetime.now()

            test_value = f"Test value #{test_count}"
            save_test_data('test_1h.db', test_value)
            save_test_data('test_24h.db', test_value)

            if (current_time - last_1h_rotation).total_seconds() >= 3600:
                rotate_db('db/test_1h_old.db', 'db/test_1h.db')
                last_1h_rotation = current_time

            if (current_time - last_24h_rotation).total_seconds() >= 86400:
                rotate_db('db/test_24h_old.db', 'db/test_24h.db')
                last_24h_rotation = current_time

            # Mesajı oluştur ve kaçış uygula
            ts = current_time.strftime("%Y-%m-%d %H:%M:%S")
            message = (f"🔍 *Database Test*\n\n"
                       f"Test \\#{test_count}\n"
                       f"Time: `{escape_markdown_v2(ts)}`\n"
                       f"Value: `{escape_markdown_v2(test_value)}`\n\n"
                       f"✅ Data saved to databases")
            send_telegram_message(message)

            git_push()

            print(f"[{datetime.now()}] Test #{test_count} completed")
            time.sleep(CONFIG["TEST_INTERVAL"])

        except Exception as e:
            print(f"[{datetime.now()}] Error in main loop: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
