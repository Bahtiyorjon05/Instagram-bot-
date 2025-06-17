
import telebot
import yt_dlp
import os
import time
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Load .env vars
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN missing in .env")

bot = telebot.TeleBot(BOT_TOKEN)

# Setup logger
logging.basicConfig(filename="bot_errors.log", level=logging.ERROR)

def clean_downloads():
    for f in os.listdir():
        if f.startswith("downloaded_video"):
            os.remove(f)

def download_media(url):
    try:
        clean_downloads()

        if "pinterest.com" in url:
            raise Exception("📌 Pinterest blocks download access. Try downloading manually.")

        ydl_opts = {
            'format': 'bv*+ba/best',
            'outtmpl': 'downloaded_video.%(ext)s',
            'merge_output_format': 'mp4',
            'quiet': True,
            'noplaylist': True,
            'retries': 5,
            'force_overwrites': True,
            'ignoreerrors': True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }],
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("❌ Couldn’t extract video info.")

            filename = ydl.prepare_filename(info)
            if os.path.exists(filename):
                return filename
            else:
                raise Exception("❌ Video file not found after download.")

    except Exception as e:
        raise Exception(f"❌ Failed to download: {str(e)}")



@bot.message_handler(commands=["start"])
def handle_start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📱 Share Contact", request_contact=True))

    bot.send_message(
        message.chat.id,
        f"👋 Hello {message.from_user.first_name}!\n\nJust send me a video link (YouTube, Instagram, etc) and I'll download it for you. Optional: share your contact.",
        reply_markup=markup
    )

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact:
        bot.reply_to(message, "✅ Thank you! You're registered, now send a video link.")

@bot.message_handler(func=lambda msg: True)
def handle_video_link(message):
    url = message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "❌ Please send a valid link.")
        return

    bot.reply_to(message, "⏳ Downloading your video, hold tight...")

    try:
        file_path = download_media(url)

        if os.path.getsize(file_path) > 50 * 1024 * 1024:
            bot.reply_to(message, "❌ File too large for Telegram (>50MB).")
            os.remove(file_path)
            return

        with open(file_path, 'rb') as video:
            bot.send_document(message.chat.id, video)
        bot.reply_to(message, "✅ Here's your video!")
        os.remove(file_path)

    except Exception as e:
        logging.error(str(e))
        bot.reply_to(message, str(e))

bot.polling()

