import os
from linebot import LineBotApi, WebhookHandler

# Single shared instances — import these from anywhere that needs to
# send/reply LINE messages or register message handlers, instead of
# creating new LineBotApi/WebhookHandler objects elsewhere.
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
