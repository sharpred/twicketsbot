import requests
import os

class TelegramBotClient:

    def __init__(self):
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    
    def send_notification(self,title, message):
        """Send a notification via Telegram."""
        text = f"*{title}*\n{message}"
        url = f"https://api.telegram.org/bot{self.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": self.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Error sending message: {response.text}")
