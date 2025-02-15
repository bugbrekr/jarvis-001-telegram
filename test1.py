from telethon import TelegramClient, events
import toml

with open("config.toml") as f:
    config = toml.loads(f.read())

API_ID = config["telegram"]["API_ID"]
API_HASH = config["telegram"]["API_HASH"]

client =  TelegramClient('account', API_ID, API_HASH)
bot_client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=config["telegram"]["BOT_TOKEN"])

with client:
    client.action()