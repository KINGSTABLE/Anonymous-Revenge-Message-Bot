import os
import time
import threading
import requests
import logging
from flask import Flask
from datetime import datetime, timedelta
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

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

bot = Bot(token=BOT_TOKEN)

# ✅ CHECK IF USER IS SUBSCRIBED TO THE CHANNEL
def is_user_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# 🚫 FORCE JOIN MESSAGE
def force_join(update: Update):
    update.message.reply_text(
        f"🚨 *You must join our channel to use this bot!*\n"
        f"➡️ [Join Now]({f'https://t.me/{CHANNEL_USERNAME[1:]}'})\n"
        f"✅ Then click /start again.",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# 🏁 START COMMAND
def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if not is_user_subscribed(user_id):
        force_join(update)
        return

    update.message.reply_text(
        "👻 *Welcome to Anonymous Message Bot!*\n\n"
        "📩 Send messages anonymously to any Telegram user!\n"
        "🕒 Messages **self-destruct** after 10 minutes.\n"
        "📌 Use `/send @username your message` to send a message.\n"
        "🕓 Use `/schedule @username your message | HH:MM` to schedule a message.\n",
        parse_mode="Markdown"
    )

# ⏳ SCHEDULE MESSAGE HANDLER
def schedule_message(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if not is_user_subscribed(user_id):
        force_join(update)
        return

    if len(context.args) < 4 or "|" not in update.message.text:
        update.message.reply_text("❌ *Usage:* `/schedule @username your message | HH:MM`", parse_mode="Markdown")
        return

    parts = update.message.text.split("|")
    message_content = parts[0].split(" ", 2)
    schedule_time = parts[1].strip()

    try:
        target_username = message_content[1]
        message_text = message_content[2]
        target_user = bot.get_chat(target_username).id
        send_time = datetime.strptime(schedule_time, "%H:%M").time()

        current_time = datetime.now().time()
        if send_time <= current_time:
            update.message.reply_text("❌ Scheduled time must be in the future!", parse_mode="Markdown")
            return

        threading.Timer(
            (datetime.combine(datetime.today(), send_time) - datetime.now()).total_seconds(),
            lambda: send_anonymous_message(update, target_user, message_text, user_id)
        ).start()

        update.message.reply_text(f"✅ Message scheduled for {target_username} at {schedule_time}.", parse_mode="Markdown")

    except Exception as e:
        update.message.reply_text("❌ Invalid username or time format!", parse_mode="Markdown")

# 📩 SEND ANONYMOUS MESSAGE
def send_anonymous_message(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if not is_user_subscribed(user_id):
        force_join(update)
        return

    if user_id in last_message_time and (time.time() - last_message_time[user_id]) < COOLDOWN_TIME:
        update.message.reply_text(f"⏳ *Cooldown active!* Wait {COOLDOWN_TIME} sec.", parse_mode="Markdown")
        return

    if user_id in message_count and message_count[user_id] >= DAILY_LIMIT:
        update.message.reply_text("🚫 *Daily limit reached!* Try again tomorrow.", parse_mode="Markdown")
        return

    if len(context.args) < 2:
        update.message.reply_text("❌ *Usage:* `/send @username your message`", parse_mode="Markdown")
        return

    target_username = context.args[0]
    message_text = " ".join(context.args[1:])
    
    try:
        target_user = bot.get_chat(target_username).id
        sent_message = bot.send_message(target_user, f"📩 *Anonymous Message:*\n\n{message_text}", parse_mode="Markdown")

        # Auto-delete message
        threading.Timer(MESSAGE_LIFETIME, lambda: bot.delete_message(target_user, sent_message.message_id)).start()

        update.message.reply_text("✅ *Message sent anonymously!*", parse_mode="Markdown")

        # Logging to Admin Channel
        log_text = (
            f"📬 *Anonymous Message Sent!*\n"
            f"👤 *From:* {update.message.from_user.username} (ID: `{user_id}`)\n"
            f"🎯 *To:* {target_username}\n"
            f"📄 *Message:* {message_text}\n"
            f"📅 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        bot.send_message(LOG_CHANNEL_ID, log_text, parse_mode="Markdown")

        # Update cooldown & daily limit
        last_message_time[user_id] = time.time()
        message_count[user_id] = message_count.get(user_id, 0) + 1

    except Exception as e:
        update.message.reply_text("❌ Failed to send message. User may have privacy settings enabled.", parse_mode="Markdown")

# 🏁 MAIN FUNCTION
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("send", send_anonymous_message))
    dp.add_handler(CommandHandler("schedule", schedule_message))

    updater.start_polling()
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
