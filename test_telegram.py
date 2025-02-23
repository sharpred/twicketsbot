from telegram import TelegramBotClient

if __name__ == "__main__":
    client = TelegramBotClient()
    client.send_notification("Welcome", "Welcome to the Twickets Bot")