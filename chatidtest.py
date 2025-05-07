import requests

BOT_TOKEN = "7699728190:AAHADXoDkFdEfvgJvW7Wdpf8grcR1smXn5k"
CHAT_IDS = [-1002281621284, 5637330580]
TEXT = "Test mesajı: Aktif misin?"

for chat_id in CHAT_IDS:
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": TEXT
        }
    )
    print(f"Chat ID {chat_id} - Status Code: {response.status_code}, Response: {response.json()}")
