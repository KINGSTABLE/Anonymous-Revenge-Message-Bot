import os
import time
import threading
import logging
from flask import Flask
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters
)

# 🚀 BOT CONFIGURATION
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@TOOLS_BOTS_KING"  # Force join channel
LOG_CHANNEL_ID = -1002661069692  # Your log channel

# ⚙️ SETTINGS
DAILY_LIMIT = 5  # Max messages per day per user
COOLDOWN_TIME = 30  # Cooldown in seconds
MESSAGE_LIFETIME = 600  # Self-destruct after 10 minutes (600 sec)

# 🔥 STORAGE
message_count = {}
last_message_time = {}

# 🌐 Flask App for 24/7 Hosting on Koyeb
app = Flask(__name__)

@app.route('/')
def home():
    return "Anonymous Revenge Message Bot is Running! 🚀"

# ✅ CHECK IF USER IS SUBSCRIBED TO THE CHANNEL
async def is_user_subscribed(user_id: int, bot: Bot):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# 🚫 FORCE JOIN MESSAGE
async def force_join(update: Update):
    await update.message.reply_text(
        f"🚨 *You must join our channel to use this bot!*\n"
        f"➡️ [Join Now](https://t.me/{CHANNEL_USERNAME[1:]})\n"
        f"✅ Then click /start again.",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# 🏁 START COMMAND
async def start(update: Update, context):
    user_id = update.message.chat_id
    bot = context.bot

    if not await is_user_subscribed(user_id, bot):
        await force_join(update)
        return

    await update.message.reply_text(
        "👻 *Welcome to Anonymous Message Bot!*\n\n"
        "📩 Send messages anonymously to any Telegram user!\n"
        "🕒 Messages **self-destruct** after 10 minutes.\n"
        "📌 Use `/send @username your message` to send a message.\n",
        parse_mode="Markdown"
    )

# 📩 SEND ANONYMOUS MESSAGE
async def send_anonymous_message(update: Update, context):
    user_id = update.message.chat_id
    bot = context.bot

    if not await is_user_subscribed(user_id, bot):
        await force_join(update)
        return

    if user_id in last_message_time and (time.time() - last_message_time[user_id]) < COOLDOWN_TIME:
        await update.message.reply_text(f"⏳ *Cooldown active!* Wait {COOLDOWN_TIME} sec.", parse_mode="Markdown")
        return

    if user_id in message_count and message_count[user_id] >= DAILY_LIMIT:
        await update.message.reply_text("🚫 *Daily limit reached!* Try again tomorrow.", parse_mode="Markdown")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ *Usage:* `/send @username your message`", parse_mode="Markdown")
        return

    target_username = context.args[0]
    message_text = " ".join(context.args[1:])

    try:
        target_user = await bot.get_chat(target_username)
        sent_message = await bot.send_message(target_user.id, f"📩 *Anonymous Message:*\n\n{message_text}", parse_mode="Markdown")

        # Auto-delete message after MESSAGE_LIFETIME seconds
        threading.Timer(MESSAGE_LIFETIME, lambda: bot.delete_message(target_user.id, sent_message.message_id)).start()

        await update.message.reply_text("✅ *Message sent anonymously!*", parse_mode="Markdown")

        # Logging to Admin Channel
        log_text = (
            f"📬 *Anonymous Message Sent!*\n"
            f"👤 *From:* {update.message.from_user.username} (ID: `{user_id}`)\n"
            f"🎯 *To:* {target_username}\n"
            f"📄 *Message:* {message_text}\n"
            f"📅 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await bot.send_message(LOG_CHANNEL_ID, log_text, parse_mode="Markdown")

        # Update cooldown & daily limit
        last_message_time[user_id] = time.time()
        message_count[user_id] = message_count.get(user_id, 0) + 1

    except Exception as e:
        await update.message.reply_text("❌ Failed to send message. User may have privacy settings enabled.", parse_mode="Markdown")

# 🏁 MAIN FUNCTION
def main():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send", send_anonymous_message))

    application.run_polling()

if __name__ == "__main__":
    main()
