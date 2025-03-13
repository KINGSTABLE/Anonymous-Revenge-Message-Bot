import os
import time
import threading
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask

# Load environment variables from .env file
load_dotenv()

# Bot credentials
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # Channel where users must join
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))  # Admin log channel

# Message limits
DAILY_LIMIT = 5  # Max messages per day per user
COOLDOWN_TIME = 30  # Cooldown time in seconds
MESSAGE_LIFETIME = 600  # Auto-delete messages after 10 minutes (600 sec)

# Initialize the bot
bot = Client("anon_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to track user limits
user_limits = {}
cooldown_tracker = {}

# Background scheduler for resetting daily limits
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: user_limits.clear(), 'cron', hour=0, minute=0)
scheduler.start()

# Flask app for 24/7 hosting
app = Flask(__name__)

@app.route('/')
def home():
    return "Anonymous Bot is running!"

# Function to check if the user is subscribed to the required channel
async def is_user_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# Function to force users to join before using the bot
async def force_join(message: Message):
    await message.reply_text(
        "❌ You must join our channel before using this bot.\n"
        f"🔗 [Click Here to Join](https://t.me/{CHANNEL_ID})",
        disable_web_page_preview=True,
    )

# Function to delete messages after a set time
def delete_message_later(chat_id, message_id, delay):
    time.sleep(delay)
    try:
        bot.delete_messages(chat_id, message_id)
    except Exception:
        pass

# Command: Start
@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text(
        "👋 Welcome to the Anonymous Message Bot!\n"
        "Send messages anonymously using `/send @username your message`"
    )

# Command: Send Anonymous Message
@bot.on_message(filters.command("send"))
async def send_anonymous_message(client, message):
    user_id = message.from_user.id

    # Check if user is subscribed
    if not await is_user_subscribed(user_id):
        await force_join(message)
        return

    # Check daily message limit
    if user_id in user_limits and user_limits[user_id] >= DAILY_LIMIT:
        await message.reply_text("❌ You've reached your daily limit for anonymous messages.")
        return

    # Check cooldown timer
    last_message_time = cooldown_tracker.get(user_id, 0)
    if time.time() - last_message_time < COOLDOWN_TIME:
        remaining_time = int(COOLDOWN_TIME - (time.time() - last_message_time))
        await message.reply_text(f"⏳ Please wait {remaining_time} seconds before sending another message.")
        return

    # Validate message format
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply_text("❌ *Usage:* `/send @username your message`", parse_mode="Markdown")
        return

    target_username = args[1]
    message_text = args[2]

    try:
        # Get recipient info
        target_user = await bot.get_chat(target_username)

        # Send anonymous message
        sent_message = await bot.send_message(target_user.id, f"📩 *Anonymous Message:*\n\n{message_text}", parse_mode="Markdown")

        # Schedule auto-delete
        threading.Thread(target=delete_message_later, args=(target_user.id, sent_message.message_id, MESSAGE_LIFETIME)).start()

        await message.reply_text("✅ *Message sent anonymously!*", parse_mode="Markdown")

        # Log message in admin channel
        log_text = (
            f"📬 *Anonymous Message Sent!*\n"
            f"👤 *From:* {message.from_user.username} (ID: `{user_id}`)\n"
            f"🎯 *To:* {target_username}\n"
            f"📄 *Message:* {message_text}\n"
            f"📅 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await bot.send_message(LOG_CHANNEL_ID, log_text, parse_mode="Markdown")

        # Update user limits
        user_limits[user_id] = user_limits.get(user_id, 0) + 1
        cooldown_tracker[user_id] = time.time()

    except Exception as e:
        if "privacy" in str(e).lower():
            await message.reply_text("❌ The user has privacy settings enabled. They need to /start the bot first.")
        else:
            await message.reply_text("❌ Failed to send the message. Please try again later.")

# Command: Schedule Message
@bot.on_message(filters.command("schedule"))
async def schedule_message(client, message):
    user_id = message.from_user.id

    # Check if user is subscribed
    if not await is_user_subscribed(user_id):
        await force_join(message)
        return

    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.reply_text("❌ *Usage:* `/schedule @username HH:MM your message`", parse_mode="Markdown")
        return

    target_username, schedule_time, message_text = args[1], args[2], args[3]

    try:
        # Parse time
        target_time = datetime.strptime(schedule_time, "%H:%M").time()
        now = datetime.now().time()
        if target_time <= now:
            await message.reply_text("❌ Scheduled time must be in the future.")
            return

        # Schedule the message
        def send_later():
            bot.loop.create_task(send_anonymous_message(client, message))

        delay = (datetime.combine(datetime.today(), target_time) - datetime.now()).seconds
        threading.Timer(delay, send_later).start()

        await message.reply_text(f"✅ *Message scheduled for {schedule_time}!*", parse_mode="Markdown")

    except ValueError:
        await message.reply_text("❌ Invalid time format. Use HH:MM.")

# Start the bot
if __name__ == "__main__":
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start()
    bot.run()
