
import os
import time
import logging
import sqlite3
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import yt_dlp

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s")
DB_FILE = "bot_users.db"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
LOG_FILE = "bot_errors.log"

# Initialize logger
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Initialize bot
bot = TeleBot(BOT_TOKEN)


# === Database Module ===
class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone_number TEXT DEFAULT 'Not Provided',
                    videos_downloaded INTEGER DEFAULT 0,
                    start_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    referrals INTEGER DEFAULT 0
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    video_url TEXT,
                    download_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    format TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """
            )
            conn.commit()

    def execute_with_retry(self, query_func, retries=5, delay=2):
        """Retry database operations in case of lock errors."""
        for _ in range(retries):
            try:
                return query_func()
            except sqlite3.OperationalError:
                time.sleep(delay)
        raise Exception("Database lock error: maximum retries exceeded.")

    def register_user(self, user_id, username, first_name, last_name, phone_number="Not Provided"):
        """Register a new user in the database."""
        def operation():
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
                if not cursor.fetchone():
                    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        """
                        INSERT INTO users (id, username, first_name, last_name, phone_number, start_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (user_id, username, first_name, last_name, phone_number, start_time),
                    )
                    conn.commit()

        self.execute_with_retry(operation)

    def increment_video_downloads(self, user_id):
        """Increment the video download count for a user."""
        def operation():
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET videos_downloaded = videos_downloaded + 1 WHERE id = ?", (user_id,))
                conn.commit()

        self.execute_with_retry(operation)

    def log_download(self, user_id, video_url, format_type):
        """Log a download in the database."""
        def operation():
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                download_time = time.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """
                    INSERT INTO downloads (user_id, video_url, download_time, format)
                    VALUES (?, ?, ?, ?)
                """,
                    (user_id, video_url, download_time, format_type),
                )
                conn.commit()

        self.execute_with_retry(operation)


# === Media Downloader Module ===
class MediaDownloader:
    @staticmethod
    def download_media(url):
        try:
            # Clear previous files
            for file in os.listdir():
                if file.startswith('downloaded_video'):
                    os.remove(file)

            ydl_opts = {
                'format': 'best',
                'outtmpl': 'downloaded_video.%(ext)s',
                'quiet': True,
                'cookiefile': 'cookies.txt',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            downloaded_file = 'downloaded_video.mp4'
            if not os.path.exists(downloaded_file):
                raise Exception("Downloaded video file does not exist.")
            
            # Return the downloaded file path
            return downloaded_file

        except Exception as e:
            raise Exception(f"Error downloading video: {e}")


# === Bot Logic ===
db = Database(DB_FILE)


@bot.message_handler(commands=["start"])
def welcome(message):
    """Handle the /start command."""
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    first_name = message.from_user.first_name or "Unknown"
    last_name = message.from_user.last_name or "Unknown"

    db.register_user(user_id, username, first_name, last_name)

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    phone_button = KeyboardButton("📱 Share Contact (Optional)", request_contact=True)
    markup.add(phone_button)

    bot.send_message(
        message.chat.id,
        f"👋 Welcome, {first_name}! Send links from YouTube, Instagram, LinkedIn, and other platforms to download media. 📱 Share your contact for complete registration (optional).",
        reply_markup=markup,
    )


@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    """Handle contact sharing."""
    if message.contact:
        user_id = message.contact.user_id
        phone_number = message.contact.phone_number

        db.execute_with_retry(
            lambda: db.register_user(user_id, "unknown", "Unknown", "Unknown", phone_number)
        )

        bot.reply_to(message, "✅ Thank you! Your phone number has been saved. You can now send video links for download.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle incoming messages."""
    user_id = message.from_user.id
    url = message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "❌ Please send a valid link.")
        return

    bot.reply_to(message, "⏳ Processing your request...")
    try:
        file_path = MediaDownloader.download_media(url)

        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            bot.reply_to(message, "❌ File size exceeds the 50 MB limit.")
            os.remove(file_path)
            return

        with open(file_path, "rb") as file:
            bot.send_document(message.chat.id, file)

        db.increment_video_downloads(user_id)
        db.log_download(user_id, url, "media")
        bot.reply_to(message, "✅ Done! Here's your file.")
        os.remove(file_path)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


# === Entry Point ===
if __name__ == "__main__":
    db.init_db()
    bot.polling(none_stop=True)