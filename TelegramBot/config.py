import json
from os import getenv

API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")
BOT_TOKEN = getenv("BOT_TOKEN")

SUDO_USERID = json.loads(getenv("SUDO_USERID"))
AUTHORIZED_CHATS = json.loads(getenv("AUTHORIZED_CHATS"))
