

import telebot
import yt_dlp
import os
import sqlite3
import time
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


# Bot token from BotFather
BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
bot = telebot.TeleBot(BOT_TOKEN)

# Database setup
DB_FILE = 'bot_users.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
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
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_url TEXT,
                download_time TEXT DEFAULT CURRENT_TIMESTAMP,
                format TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()

def with_retry(func, retries=5, delay=2):
    for _ in range(retries):
        try:
            return func()
        except sqlite3.OperationalError:
            time.sleep(delay)
    raise Exception("Database lock error: maximum retries exceeded.")

def register_user(user_id, username, first_name, last_name, phone_number):
    def operation():
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
            if not cursor.fetchone():
                start_time = time.strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute(''' 
                    INSERT INTO users (id, username, first_name, last_name, phone_number, start_time) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, phone_number, start_time))
                conn.commit()

    with_retry(operation)

def increment_video_downloads(user_id):
    def operation():
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET videos_downloaded = videos_downloaded + 1 WHERE id = ?', (user_id,))
            conn.commit()

    with_retry(operation)

def log_download(user_id, video_url, format_type):
    def operation():
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            download_time = time.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(''' 
                INSERT INTO downloads (user_id, video_url, download_time, format) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, video_url, download_time, format_type))
            conn.commit()

    with_retry(operation)

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
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded_file = 'downloaded_video.mp4'
        if not os.path.exists(downloaded_file):
            raise Exception("Downloaded video file does not exist.")
        return downloaded_file
    except Exception as e:
        raise Exception(f"Failed to download video: {e}")

@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    first_name = message.from_user.first_name or "Unknown"
    last_name = message.from_user.last_name or "Unknown"
    register_user(user_id, username, first_name, last_name, "Not Provided")

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    phone_button = KeyboardButton("📱 Share Contact (Optional)", request_contact=True)
    markup.add(phone_button)

    bot.send_message(
        message.chat.id,
        f"👋 Welcome, {first_name}! Send links from YouTube, Instagram, LinkedIn and other platforms to download media. 📱 Share your contact for complete registration (optional).",
        reply_markup=markup
    )

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact:
        user_id = message.contact.user_id
        phone_number = message.contact.phone_number

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET phone_number = ? WHERE id = ?', (phone_number, user_id))
            conn.commit()

        bot.reply_to(message, "✅ Thank you! Your phone number has been saved. You can now send video links for download.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    url = message.text.strip()
    register_user(user_id, message.from_user.username or "unknown", message.from_user.first_name or "Unknown", message.from_user.last_name or "Unknown", "Not Provided")

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "❌ Please send a valid link.")
        return

    bot.reply_to(message, "⏳ Processing your request...")
    try:
        file_path = download_media(url)

        if os.path.getsize(file_path) > 50 * 1024 * 1024:
            bot.reply_to(message, "❌ File size exceeds the 50 MB limit.")
            os.remove(file_path)
            return

        with open(file_path, 'rb') as file:
            bot.send_document(message.chat.id, file)
        increment_video_downloads(user_id)
        log_download(user_id, url, 'media')
        bot.reply_to(message, "✅ Done! Here's your file.")
        os.remove(file_path)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

logging.basicConfig(filename='bot_errors.log', level=logging.ERROR)
init_db()
bot.polling()








# import telebot
# import yt_dlp
# import os
# import sqlite3
# import time
# from telebot.types import ReplyKeyboardMarkup, KeyboardButton
# from PIL import Image
# import cv2

# # Replace with your bot token from BotFather
# BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
# bot = telebot.TeleBot(BOT_TOKEN)

# # Database setup
# DB_FILE = 'bot_users.db'

# # Initialize the database
# def init_db():
#     with sqlite3.connect(DB_FILE) as conn:
#         cursor = conn.cursor()
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY,
#                 username TEXT,
#                 first_name TEXT,
#                 last_name TEXT,
#                 phone_number TEXT DEFAULT 'Not Provided',
#                 videos_downloaded INTEGER DEFAULT 0,
#                 start_time TEXT DEFAULT CURRENT_TIMESTAMP,
#                 referrals INTEGER DEFAULT 0
#             )
#         ''')
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS downloads (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id INTEGER,
#                 video_url TEXT,
#                 download_time TEXT DEFAULT CURRENT_TIMESTAMP,
#                 format TEXT,
#                 FOREIGN KEY (user_id) REFERENCES users (id)
#             )
#         ''')
#         conn.commit()

# def get_db_connection():
#     conn = sqlite3.connect(DB_FILE)
#     conn.execute('PRAGMA busy_timeout = 10000')  # Set the busy timeout to 10 seconds
#     return conn

# def with_retry(func, retries=5, delay=2):
#     for _ in range(retries):
#         try:
#             return func()
#         except sqlite3.OperationalError as e:
#             print(f"Database lock error, retrying... ({_ + 1}/{retries})")
#             time.sleep(delay)
#     raise Exception("Database lock error: maximum retries exceeded.")

# def register_user(user_id, username, first_name, last_name, phone_number):
#     def operation():
#         with sqlite3.connect(DB_FILE) as conn:
#             cursor = conn.cursor()
#             cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
#             if not cursor.fetchone():
#                 start_time = time.strftime('%Y-%m-%d %H:%M:%S')
#                 cursor.execute(''' 
#                     INSERT INTO users (id, username, first_name, last_name, phone_number, start_time) 
#                     VALUES (?, ?, ?, ?, ?, ?)
#                 ''', (user_id, username, first_name, last_name, phone_number, start_time))
#                 conn.commit()

#     with_retry(operation)

# # Increment video download count
# def increment_video_downloads(user_id):
#     def operation():
#         with sqlite3.connect(DB_FILE) as conn:
#             cursor = conn.cursor()
#             cursor.execute('UPDATE users SET videos_downloaded = videos_downloaded + 1 WHERE id = ?', (user_id,))
#             conn.commit()

#     with_retry(operation)

# # Log download activity
# def log_download(user_id, video_url, format_type):
#     def operation():
#         with sqlite3.connect(DB_FILE) as conn:
#             cursor = conn.cursor()
#             download_time = time.strftime('%Y-%m-%d %H:%M:%S')
#             cursor.execute(''' 
#                 INSERT INTO downloads (user_id, video_url, download_time, format) 
#                 VALUES (?, ?, ?, ?)
#             ''', (user_id, video_url, download_time, format_type))
#             conn.commit()

#     with_retry(operation)

# # Download video using yt_dlp
# def download_media(url):
#     try:
#         ydl_opts = {
#             'format': 'best',
#             'outtmpl': 'downloaded_video.%(ext)s',
#             'quiet': True,
#         }
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])

#         downloaded_file = 'downloaded_video.mp4'
#         if not os.path.exists(downloaded_file):
#             raise Exception("Downloaded video file does not exist.")
#         return downloaded_file
#     except Exception as e:
#         raise Exception(f"Failed to download video: {e}")

# # NSFW content detection using OpenCV and Deep Learning
# def is_nsfw(file_path):
#     try:
#         # Example: Check for explicit content using frame sampling
#         cap = cv2.VideoCapture(file_path)
#         frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#         sample_rate = max(frame_count // 10, 1)  # Check every 10th frame

#         for i in range(0, frame_count, sample_rate):
#             cap.set(cv2.CAP_PROP_POS_FRAMES, i)
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             # Convert frame to grayscale or pass to pre-trained NSFW model
#             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#             if gray.mean() > 200:  # Placeholder threshold
#                 cap.release()
#                 return True

#         cap.release()
#         return False
#     except Exception as e:
#         return False

# # /start command handler
# @bot.message_handler(commands=['start'])
# def welcome(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     last_name = message.from_user.last_name or "Unknown"  # Fetch last_name if available
#     register_user(user_id, username, first_name, last_name, "Not Provided")

#     markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
#     phone_button = KeyboardButton("📱 Share Contact (Optional)", request_contact=True)
#     markup.add(phone_button)

#     bot.send_message(
#         message.chat.id,
#         f"👋 Welcome, {first_name}! Send links from YouTube, Instagram, LinkedIn and other platforms to download media. 📱 Share your contact for complete registration (optional).",
#         reply_markup=markup
#     )

# # Handle contact sharing
# @bot.message_handler(content_types=['contact'])
# def handle_contact(message):
#     if message.contact:
#         user_id = message.contact.user_id
#         phone_number = message.contact.phone_number

#         # Ensure to update phone number and the last_name if provided
#         with sqlite3.connect(DB_FILE) as conn:
#             cursor = conn.cursor()
#             cursor.execute('UPDATE users SET phone_number = ?, last_name = ? WHERE id = ?', 
#                            (phone_number, message.contact.last_name or "Not Provided", user_id))
#             conn.commit()

#         bot.reply_to(message, "✅ Thank you! Your phone number has been saved. You can now send video links for download.")

# # Handle user messages
# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     user_id = message.from_user.id
#     url = message.text.strip()
#     register_user(user_id, message.from_user.username or "unknown", message.from_user.first_name or "Unknown", message.from_user.last_name or "Unknown", "Not Provided")

#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid link.")
#         return

#     bot.reply_to(message, "⏳ Processing your request...")
#     try:
#         file_path = download_media(url)

#         if is_nsfw(file_path):
#             bot.reply_to(message, "❌ The video contains explicit content and cannot be shared.")
#             os.remove(file_path)
#             return

#         if os.path.getsize(file_path) > 50 * 1024 * 1024:
#             bot.reply_to(message, "❌ File size exceeds the 50 MB limit.")
#             os.remove(file_path)
#             return

#         with open(file_path, 'rb') as file:
#             bot.send_document(message.chat.id, file)
#         increment_video_downloads(user_id)
#         log_download(user_id, url, 'media')
#         bot.reply_to(message, "✅ Done! Here's your file.")
#         os.remove(file_path)
#     except Exception as e:
#         bot.reply_to(message, f"❌ Error: {str(e)}")

# # Initialize database and start bot
# init_db()
# bot.polling()













# import telebot
# import yt_dlp
# import os
# import sqlite3
# import time
# from telebot.types import ReplyKeyboardMarkup, KeyboardButton
# from PIL import Image
# import cv2

# # Replace with your bot token from BotFather
# BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
# bot = telebot.TeleBot(BOT_TOKEN)

# # Database setup
# DB_FILE = 'bot_users.db'

# # Initialize the database
# def init_db():
#     conn = sqlite3.connect(DB_FILE, check_same_thread=False)
#     cursor = conn.cursor()
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY,
#             username TEXT,
#             first_name TEXT,
#             last_name TEXT,
#             phone_number TEXT DEFAULT 'Not Provided',
#             videos_downloaded INTEGER DEFAULT 0,
#             start_time TEXT DEFAULT CURRENT_TIMESTAMP,
#             referrals INTEGER DEFAULT 0
#         )
#     ''')
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS downloads (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER,
#             video_url TEXT,
#             download_time TEXT DEFAULT CURRENT_TIMESTAMP,
#             format TEXT,
#             FOREIGN KEY (user_id) REFERENCES users (id)
#         )
#     ''')
#     conn.commit()
#     conn.close()


# def get_db_connection():
#     conn = sqlite3.connect(DB_FILE)
#     conn.execute('PRAGMA busy_timeout = 10000')  # Increase timeout
#     return conn


# def with_retry(func, retries=3, delay=1):
#     for _ in range(retries):
#         try:
#             return func()
#         except sqlite3.OperationalError as e:
#             print(f"Database lock error, retrying... ({_ + 1}/{retries})")
#             time.sleep(delay)
#     raise Exception("Database lock error: maximum retries exceeded.")

# def register_user(user_id, username, first_name, last_name, phone_number):
#     def operation():
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
#         if not cursor.fetchone():
#             start_time = time.strftime('%Y-%m-%d %H:%M:%S')
#             cursor.execute('''
#                 INSERT INTO users (id, username, first_name, last_name, phone_number, start_time)
#                 VALUES (?, ?, ?, ?, ?, ?)
#             ''', (user_id, username, first_name, last_name, phone_number, start_time))
#             conn.commit()
#         conn.close()
    
#     with_retry(operation)


# # Increment video download count
# def increment_video_downloads(user_id):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute('UPDATE users SET videos_downloaded = videos_downloaded + 1 WHERE id = ?', (user_id,))
#     conn.commit()
#     conn.close()

# # Log download activity
# def log_download(user_id, video_url, format_type):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     download_time = time.strftime('%Y-%m-%d %H:%M:%S')
#     cursor.execute('''
#         INSERT INTO downloads (user_id, video_url, download_time, format)
#         VALUES (?, ?, ?, ?)
#     ''', (user_id, video_url, download_time, format_type))
#     conn.commit()
#     conn.close()

# # Download video using yt_dlp
# def download_media(url):
#     try:
#         ydl_opts = {
#             'format': 'best',
#             'outtmpl': 'downloaded_video.%(ext)s',
#             'quiet': True,
#         }
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])

#         downloaded_file = 'downloaded_video.mp4'
#         if not os.path.exists(downloaded_file):
#             raise Exception("Downloaded video file does not exist.")
#         return downloaded_file
#     except Exception as e:
#         raise Exception(f"Failed to download video: {e}")

# # NSFW content detection using OpenCV and Deep Learning
# def is_nsfw(file_path):
#     try:
#         # Example: Check for explicit content using frame sampling
#         cap = cv2.VideoCapture(file_path)
#         frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#         sample_rate = max(frame_count // 10, 1)  # Check every 10th frame

#         for i in range(0, frame_count, sample_rate):
#             cap.set(cv2.CAP_PROP_POS_FRAMES, i)
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             # Convert frame to grayscale or pass to pre-trained NSFW model
#             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#             if gray.mean() > 200:  # Placeholder threshold
#                 cap.release()
#                 return True

#         cap.release()
#         return False
#     except Exception as e:
#         return False

# # /start command handler
# @bot.message_handler(commands=['start'])
# def welcome(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     register_user(user_id, username, first_name, "Unknown", "Not Provided")

#     markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
#     phone_button = KeyboardButton("📱 Share Contact (Optional)", request_contact=True)
#     markup.add(phone_button)

#     bot.send_message(
#         message.chat.id,
#         f"👋 Welcome, {first_name}! Send links from YouTube, Instagram, LinkedIn and other platforms to download media. 📱 Share your contact for complete registration (optional).",
#         reply_markup=markup
#     )

# # Handle contact sharing
# @bot.message_handler(content_types=['contact'])
# def handle_contact(message):
#     if message.contact:
#         user_id = message.contact.user_id
#         phone_number = message.contact.phone_number

#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute('UPDATE users SET phone_number = ? WHERE id = ?', (phone_number, user_id))
#         conn.commit()
#         conn.close()

#         bot.reply_to(message, "✅ Thank you! Your phone number has been saved. You can now send video links for download.")

# # Handle user messages
# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     user_id = message.from_user.id
#     url = message.text.strip()
#     register_user(user_id, message.from_user.username or "unknown", message.from_user.first_name or "Unknown", message.from_user.last_name or "Unknown", "Not Provided")

#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid link.")
#         return

#     bot.reply_to(message, "⏳ Processing your request...")
#     try:
#         file_path = download_media(url)

#         if is_nsfw(file_path):
#             bot.reply_to(message, "❌ The video contains explicit content and cannot be shared.")
#             os.remove(file_path)
#             return

#         if os.path.getsize(file_path) > 50 * 1024 * 1024:
#             bot.reply_to(message, "❌ File size exceeds the 50 MB limit.")
#             os.remove(file_path)
#             return

#         with open(file_path, 'rb') as file:
#             bot.send_document(message.chat.id, file)
#         increment_video_downloads(user_id)
#         log_download(user_id, url, 'media')
#         bot.reply_to(message, "✅ Done! Here's your file.")
#         os.remove(file_path)
#     except Exception as e:
#         bot.reply_to(message, f"❌ Error: {str(e)}")

# # Initialize database and start bot
# init_db()
# bot.polling()















# import telebot
# import yt_dlp
# import os
# import sqlite3
# import time
# from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# # Replace with your bot token from BotFather
# BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
# bot = telebot.TeleBot(BOT_TOKEN)

# # Database setup
# DB_FILE = 'bot_users.db'

# def init_db():
#     """Initialize the database with necessary tables."""
#     conn = sqlite3.connect(DB_FILE, check_same_thread=False)
#     cursor = conn.cursor()
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY,
#             username TEXT,
#             first_name TEXT,
#             last_name TEXT,
#             phone_number TEXT DEFAULT 'Not Provided',
#             videos_downloaded INTEGER DEFAULT 0,
#             start_time TEXT DEFAULT CURRENT_TIMESTAMP,
#             referrals INTEGER DEFAULT 0
#         )
#     ''')
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS downloads (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER,
#             video_url TEXT,
#             download_time TEXT DEFAULT CURRENT_TIMESTAMP,
#             format TEXT,
#             FOREIGN KEY (user_id) REFERENCES users (id)
#         )
#     ''')
#     conn.commit()
#     conn.close()

# def get_db_connection():
#     """Return a new SQLite connection."""
#     conn = sqlite3.connect(DB_FILE, check_same_thread=False)
#     conn.execute('PRAGMA busy_timeout = 5000')  # Wait up to 5 seconds for the lock
#     return conn

# def register_user(user_id, username, first_name, last_name, phone_number):
#     """Register a user in the database if not already registered."""
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
#     if not cursor.fetchone():
#         start_time = time.strftime('%Y-%m-%d %H:%M:%S')
#         cursor.execute('''
#             INSERT INTO users (id, username, first_name, last_name, phone_number, start_time)
#             VALUES (?, ?, ?, ?, ?, ?)
#         ''', (user_id, username, first_name, last_name, phone_number, start_time))
#         conn.commit()
#     conn.close()

# def increment_video_downloads(user_id):
#     """Increment the video download count for a user."""
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute('UPDATE users SET videos_downloaded = videos_downloaded + 1 WHERE id = ?', (user_id,))
#     conn.commit()
#     conn.close()

# def log_download(user_id, video_url, format_type):
#     """Log a video download for a user."""
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     download_time = time.strftime('%Y-%m-%d %H:%M:%S')
#     cursor.execute('''
#         INSERT INTO downloads (user_id, video_url, download_time, format)
#         VALUES (?, ?, ?, ?)
#     ''', (user_id, video_url, download_time, format_type))
#     conn.commit()
#     conn.close()

# def download_media(url):
#     """Download video from a given URL using yt_dlp."""
#     try:
#         ydl_opts = {
#             'format': 'best',
#             'outtmpl': 'downloaded_video.%(ext)s',
#             'quiet': True,
#         }
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])

#         downloaded_file = 'downloaded_video.mp4'
#         if not os.path.exists(downloaded_file):
#             raise Exception("Downloaded video file does not exist.")
#         return downloaded_file
#     except Exception as e:
#         raise Exception(f"Failed to download video: {e}")

# @bot.message_handler(commands=['start'])
# def welcome(message):
#     """Handle the /start command."""
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     register_user(user_id, username, first_name, "Unknown", "Not Provided")

#     markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
#     phone_button = KeyboardButton("📱 Share Contact (Optional)", request_contact=True)
#     markup.add(phone_button)

#     bot.send_message(
#         message.chat.id,
#         f"👋 Welcome, {first_name}!\n\n"
#         "Send links from YouTube, Instagram, LinkedIn, and other platforms to download media.\n\n"
#         "📱 You can share your contact for complete registration (optional).",
#         reply_markup=markup
#     )

# @bot.message_handler(content_types=['contact'])
# def handle_contact(message):
#     """Handle contact sharing by the user."""
#     if message.contact:
#         user_id = message.contact.user_id
#         phone_number = message.contact.phone_number

#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute('UPDATE users SET phone_number = ? WHERE id = ?', (phone_number, user_id))
#         conn.commit()
#         conn.close()

#         bot.reply_to(message, "✅ Thank you! Your phone number has been saved. You can now send video links for download.")

# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     """Handle user messages containing video links."""
#     user_id = message.from_user.id
#     url = message.text.strip()
#     register_user(user_id, message.from_user.username or "unknown", message.from_user.first_name or "Unknown", message.from_user.last_name or "Unknown", "Not Provided")

#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid link.")
#         return

#     bot.reply_to(message, "⏳ Processing your request...")
#     try:
#         file_path = download_media(url)
#         if os.path.getsize(file_path) > 50 * 1024 * 1024:
#             bot.reply_to(message, "❌ File size exceeds the 50 MB limit.")
#             os.remove(file_path)
#             return
#         with open(file_path, 'rb') as file:
#             bot.send_document(message.chat.id, file)
#         increment_video_downloads(user_id)
#         log_download(user_id, url, 'media')
#         bot.reply_to(message, "✅ Done! Here's your file.")
#         os.remove(file_path)
#     except Exception as e:
#         bot.reply_to(message, f"❌ Error: {str(e)}")

# # Initialize the database and start the bot
# init_db()
# bot.polling()














# import telebot
# import yt_dlp
# import os
# import sqlite3
# import time
# from telebot.types import ReplyKeyboardMarkup, KeyboardButton
# import requests

# # Replace with your bot token from BotFather
# BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
# bot = telebot.TeleBot(BOT_TOKEN)

# # Database setup
# DB_FILE = 'bot_users.db'

# def init_db():
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY,
#             username TEXT,
#             first_name TEXT,
#             last_name TEXT,
#             phone_number TEXT DEFAULT 'Not Provided',
#             videos_downloaded INTEGER DEFAULT 0,
#             start_time TEXT DEFAULT CURRENT_TIMESTAMP,
#             referrals INTEGER DEFAULT 0
#         )
#     ''')
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS downloads (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER,
#             video_url TEXT,
#             download_time TEXT DEFAULT CURRENT_TIMESTAMP,
#             format TEXT,
#             FOREIGN KEY (user_id) REFERENCES users (id)
#         )
#     ''')
#     conn.commit()
#     conn.close()

# def register_user(user_id, username, first_name, last_name, phone_number):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
#     if not cursor.fetchone():
#         start_time = time.strftime('%Y-%m-%d %H:%M:%S')
#         cursor.execute('''
#             INSERT INTO users (id, username, first_name, last_name, phone_number, start_time)
#             VALUES (?, ?, ?, ?, ?, ?)
#         ''', (user_id, username, first_name, last_name, phone_number, start_time))
#         conn.commit()
#     conn.close()

# def increment_video_downloads(user_id):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute('UPDATE users SET videos_downloaded = videos_downloaded + 1 WHERE id = ?', (user_id,))
#     conn.commit()
#     conn.close()

# def log_download(user_id, video_url, format_type):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     download_time = time.strftime('%Y-%m-%d %H:%M:%S')
#     cursor.execute('''
#         INSERT INTO downloads (user_id, video_url, download_time, format)
#         VALUES (?, ?, ?, ?)
#     ''', (user_id, video_url, download_time, format_type))
#     conn.commit()
#     conn.close()
# # Function to download video using yt_dlp
# def download_media(url):
#     try:
#         # Options for yt_dlp
#         ydl_opts = {
#             'format': 'best',
#             'outtmpl': 'downloaded_video.%(ext)s',  # Save the file with proper extension
#             'quiet': True,  # Suppress unnecessary logs
#         }
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])  # Download the video

#         # Get the downloaded file path (based on the output template)
#         downloaded_file = 'downloaded_video.mp4'  # Default output file name
#         if not os.path.exists(downloaded_file):
#             raise Exception("Downloaded video file does not exist.")
        
#         return downloaded_file
#     except Exception as e:
#         raise Exception(f"Failed to download video: {e}")


# @bot.message_handler(commands=['start'])
# def welcome(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     register_user(user_id, username, first_name, "Unknown", "Not Provided")

#     # Create a keyboard for sharing contact information
#     markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
#     phone_button = KeyboardButton("📱 Share Contact (Optional)", request_contact=True)
#     markup.add(phone_button)

#     bot.send_message(
#         message.chat.id,
#         f"👋 Welcome, {first_name}! \n\nSend links from YouTube, Instagram, LinkedIn, and other platforms to download media.\n\n"
#         "📱 You can share your contact for complete registration (optional)",
#         reply_markup=markup
#     )

# @bot.message_handler(content_types=['contact'])
# def handle_contact(message):
#     if message.contact:
#         user_id = message.contact.user_id
#         phone_number = message.contact.phone_number

#         # Update the user's phone number in the database
#         conn = sqlite3.connect(DB_FILE)
#         cursor = conn.cursor()
#         cursor.execute('UPDATE users SET phone_number = ? WHERE id = ?', (phone_number, user_id))
#         conn.commit()
#         conn.close()

#         bot.reply_to(message, "✅ Thank you! Your phone number has been saved. You can now send video links for download.")

# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     user_id = message.from_user.id
#     url = message.text.strip()
#     register_user(user_id, message.from_user.username or "unknown", message.from_user.first_name or "Unknown", message.from_user.last_name or "Unknown", "Not Provided")
    
#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid link.")
#         return
    
#     bot.reply_to(message, "⏳ Processing your request...")
#     try:
#         file_path = download_media(url)
#         if os.path.getsize(file_path) > 50 * 1024 * 1024:
#             bot.reply_to(message, "❌ File size exceeds the 50 MB limit.")
#             os.remove(file_path)
#             return
#         with open(file_path, 'rb') as file:
#             bot.send_document(message.chat.id, file)
#         increment_video_downloads(user_id)
#         log_download(user_id, url, 'media')
#         bot.reply_to(message, "✅ Done! Here's your file.")
#         os.remove(file_path)
#     except Exception as e:
#         bot.reply_to(message, f"❌ Error: {str(e)}")

# init_db()
# bot.polling()








# ###############################################3


# import telebot
# import yt_dlp
# import os
# import sqlite3
# import time
# from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# # Replace with your bot token from BotFather
# BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
# bot = telebot.TeleBot(BOT_TOKEN)

# # Database setup
# DB_FILE = 'bot_users.db'

# def init_db():
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     # Create the `users` table with additional fields if it doesn't exist
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY,
#             username TEXT,
#             first_name TEXT,
#             last_name TEXT,
#             phone_number TEXT DEFAULT 'Not Provided',
#             videos_downloaded INTEGER DEFAULT 0,
#             start_time TEXT DEFAULT CURRENT_TIMESTAMP,
#             referrals INTEGER DEFAULT 0
#         )
#     ''')

#     # Create the `downloads` table to log user downloads
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS downloads (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER,
#             video_url TEXT,
#             download_time TEXT DEFAULT CURRENT_TIMESTAMP,
#             format TEXT,
#             FOREIGN KEY (user_id) REFERENCES users (id)
#         )
#     ''')

#     conn.commit()
#     conn.close()

# # Register a user in the database
# def register_user(user_id, username, first_name, last_name, phone_number):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     # Check if the user already exists
#     cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
#     user_exists = cursor.fetchone()

#     if not user_exists:
#         start_time = time.strftime('%Y-%m-%d %H:%M:%S')  # Capture the start time
#         cursor.execute('''
#             INSERT INTO users (id, username, first_name, last_name, phone_number, start_time)
#             VALUES (?, ?, ?, ?, ?, ?)
#         ''', (user_id, username, first_name, last_name, phone_number, start_time))
#         conn.commit()
#     conn.close()

# # Update the video download count for a user
# def increment_video_downloads(user_id):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute('UPDATE users SET videos_downloaded = videos_downloaded + 1 WHERE id = ?', (user_id,))
#     conn.commit()
#     conn.close()

# # Log the download to the database
# def log_download(user_id, video_url, format_type):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     download_time = time.strftime('%Y-%m-%d %H:%M:%S')  # Capture the download time
#     cursor.execute('''
#         INSERT INTO downloads (user_id, video_url, download_time, format)
#         VALUES (?, ?, ?, ?)
#     ''', (user_id, video_url, download_time, format_type))
#     conn.commit()
#     conn.close()


# # Function to download image
# def download_image(url):
#     try:
#         # Get the image content from the URL
#         response = requests.get(url)
#         response.raise_for_status()  # Check for errors

#         # Save the image to a file
#         image_filename = 'downloaded_image.jpg'
#         with open(image_filename, 'wb') as f:
#             f.write(response.content)

#         return image_filename
#     except Exception as e:
#         raise Exception(f"Failed to download image: {e}")

# # Message handler for video and image links
# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     last_name = message.from_user.last_name or "Unknown"

#     # Ensure the user is registered
#     register_user(user_id, username, first_name, last_name, "NotProvided")

#     url = message.text.strip()

#     # Reply if the URL seems invalid
#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid link.")
#         return

#     bot.reply_to(message, "⏳ Processing your request... Please wait.")

#     try:
#         # Check if the URL is a video URL
#         if 'youtube.com' in url or 'youtu.be' in url:
#             file_path = download_video(url)
#             file_type = 'video'
#         # Check if the URL is an image URL
#         elif url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
#             file_path = download_image(url)
#             file_type = 'image'
#         else:
#             bot.reply_to(message, "❌ Unsupported link type.")
#             return

#         # Check file size (Telegram limit: 50 MB for free accounts)
#         if os.path.getsize(file_path) > 50 * 1024 * 1024:
#             bot.reply_to(message, "❌ File is too large for Telegram. Try a smaller file.")
#             os.remove(file_path)  # Clean up the file
#             return

#         # Send the file (video or image) to the user
#         with open(file_path, 'rb') as file:
#             if file_type == 'video':
#                 bot.send_video(message.chat.id, file)
#             elif file_type == 'image':
#                 bot.send_photo(message.chat.id, file)

#         # Log the download to the database
#         log_download(user_id, url, file_type)

#         # Update user's download count in the database
#         increment_video_downloads(user_id)

#         bot.reply_to(message, "✅ Done! Here's your file.")
#         os.remove(file_path)  # Clean up the file after sending

#     except Exception as e:
#         bot.reply_to(message, f"❌ An error occurred: {str(e)}")


# # Function to download video using yt_dlp
# def download_video(url):
#     try:
#         # Options for yt_dlp
#         ydl_opts = {
#             'format': 'best',
#             'outtmpl': 'downloaded_video.mp4',  # Save the file locally
#             'quiet': True,  # Suppress unnecessary logs
#         }
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])  # Download the video
#         return 'downloaded_video.mp4'
#     except Exception as e:
#         raise Exception(f"Failed to download video: {e}")

# # Start command handler
# @bot.message_handler(commands=['start'])
# def welcome(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     last_name = message.from_user.last_name or "Unknown"

#     # Prompt the user to share their phone number
#     markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
#     phone_button = KeyboardButton("📱 Share Contact", request_contact=True)
#     markup.add(phone_button)

#     bot.send_message(
#         message.chat.id,
#         "Welcome to the Downloader Bot! 👋 You can send media links from Instagram, YouTube, LinkedIn, and more. Optionally, you can share your contact to register fully.",
#         reply_markup=markup
#     )

#     # Save the user details without phone number for now
#     register_user(user_id, username, first_name, last_name, "NotProvided")

# # Handler for receiving contact information
# @bot.message_handler(content_types=['contact'])
# def handle_contact(message):
#     if message.contact:
#         user_id = message.contact.user_id
#         phone_number = message.contact.phone_number

#         # Update the user's phone number in the database
#         conn = sqlite3.connect(DB_FILE)
#         cursor = conn.cursor()
#         cursor.execute('UPDATE users SET phone_number = ? WHERE id = ?', (phone_number, user_id))
#         conn.commit()
#         conn.close()

#         bot.reply_to(message, "✅ Thank you! Your phone number has been saved. You can now send video links for download.")

# # Message handler for video links
# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     last_name = message.from_user.last_name or "Unknown"

#     # Ensure the user is registered
#     register_user(user_id, username, first_name, last_name, "NotProvided")

#     url = message.text.strip()

#     # Reply if the URL seems invalid
#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid video link.")
#         return

#     bot.reply_to(message, "⏳ Processing your request... Please wait.")

#     try:
#         # Download the video
#         file_path = download_video(url)

#         # Check file size (Telegram limit: 50 MB for free accounts)
#         if os.path.getsize(file_path) > 50 * 1024 * 1024:
#             bot.reply_to(message, "❌ Video is too large for Telegram. Try a smaller video.")
#             os.remove(file_path)  # Clean up the file
#             return

#         # Send the video to the user
#         with open(file_path, 'rb') as video:
#             bot.send_video(message.chat.id, video)

#         # Log the download to the database
#         log_download(user_id, url, 'video')

#         # Update user's download count in the database
#         increment_video_downloads(user_id)

#         bot.reply_to(message, "✅ Done! Here's your video.")
#         os.remove(file_path)  # Clean up the file after sending

#     except Exception as e:
#         bot.reply_to(message, f"❌ An error occurred: {str(e)}")

# # Initialize database and start the bot
# init_db()
# bot.polling()






##############################################################








# import telebot
# import yt_dlp
# import os
# import sqlite3
# from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# # Replace with your bot token from BotFather
# BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
# bot = telebot.TeleBot(BOT_TOKEN)

# # Database setup
# DB_FILE = 'bot_users.db'


# def init_db():
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     # Create the `users` table with additional fields if it doesn't exist
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY,
#             username TEXT,
#             first_name TEXT,
#             last_name TEXT,
#             phone_number TEXT,
#             videos_downloaded INTEGER
#         )
#     ''')
#     conn.commit()
#     conn.close()


# # Register a user in the database
# def register_user(user_id, username, first_name, last_name, phone_number):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     # Check if the user already exists
#     cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
#     user_exists = cursor.fetchone()

#     if not user_exists:
#         # Insert the user if they don't exist
#         cursor.execute('''
#             INSERT INTO users (id, username, first_name, last_name, phone_number, videos_downloaded)
#             VALUES (?, ?, ?, ?, ?, ?)
#         ''', (user_id, username, first_name, last_name, phone_number, 0))
#         conn.commit()
#     conn.close()


# # Update the video download count for a user
# def increment_video_downloads(user_id):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute('UPDATE users SET videos_downloaded = videos_downloaded + 1 WHERE id = ?', (user_id,))
#     conn.commit()
#     conn.close()


# # Function to download video using yt_dlp
# def download_video(url):
#     try:
#         # Options for yt_dlp
#         ydl_opts = {
#             'format': 'best',
#             'outtmpl': 'downloaded_video.mp4',  # Save the file locally
#             'quiet': True,  # Suppress unnecessary logs
#         }
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])  # Download the video
#         return 'downloaded_video.mp4'
#     except Exception as e:
#         raise Exception(f"Failed to download video: {e}")


# # Start command handler
# @bot.message_handler(commands=['start'])
# def welcome(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     last_name = message.from_user.last_name or "Unknown"

#     # Prompt the user to share their phone number
#     markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
#     phone_button = KeyboardButton("📱 Share Contact", request_contact=True)
#     markup.add(phone_button)

#     bot.send_message(
#         message.chat.id,
#         "Welcome! 👋 Please share your phone number to complete the registration:",
#         reply_markup=markup
#     )

#     # Save the user details without phone number for now
#     register_user(user_id, username, first_name, last_name, "NotProvided")


# # Handler for receiving contact information
# @bot.message_handler(content_types=['contact'])
# def handle_contact(message):
#     if message.contact:
#         user_id = message.contact.user_id
#         phone_number = message.contact.phone_number

#         # Update the user's phone number in the database
#         conn = sqlite3.connect(DB_FILE)
#         cursor = conn.cursor()
#         cursor.execute('UPDATE users SET phone_number = ? WHERE id = ?', (phone_number, user_id))
#         conn.commit()
#         conn.close()

#         bot.reply_to(message, "✅ Thank you! Your phone number has been saved. You can now send video links for download.")


# # Message handler for video links
# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     last_name = message.from_user.last_name or "Unknown"

#     # Ensure the user is registered
#     register_user(user_id, username, first_name, last_name, "NotProvided")

#     url = message.text.strip()

#     # Reply if the URL seems invalid
#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid video link.")
#         return

#     bot.reply_to(message, "⏳ Processing your request... Please wait.")

#     try:
#         # Download the video
#         file_path = download_video(url)

#         # Check file size (Telegram limit: 50 MB for free accounts)
#         if os.path.getsize(file_path) > 50 * 1024 * 1024:
#             bot.reply_to(message, "❌ Video is too large for Telegram. Try a smaller video.")
#             os.remove(file_path)  # Clean up the file
#             return

#         # Send the video to the user
#         with open(file_path, 'rb') as video:
#             bot.send_video(message.chat.id, video)

#         # Update user's download count in the database
#         increment_video_downloads(user_id)

#         bot.reply_to(message, "✅ Done! Here's your video.")
#         os.remove(file_path)  # Clean up the file after sending

#     except Exception as e:
#         bot.reply_to(message, f"❌ An error occurred: {str(e)}")


# # Initialize database and start the bot
# init_db()
# bot.polling()









#   json file save

# import telebot
# import yt_dlp
# import os
# import json

# # Replace with your bot token from BotFather
# BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
# bot = telebot.TeleBot(BOT_TOKEN)

# # File to store user data
# USER_DATA_FILE = 'users.json'

# # Load user data from JSON file
# def load_user_data():
#     if os.path.exists(USER_DATA_FILE):
#         with open(USER_DATA_FILE, 'r') as file:
#             return json.load(file)
#     return {}

# # Save user data to JSON file
# def save_user_data(data):
#     with open(USER_DATA_FILE, 'w') as file:
#         json.dump(data, file, indent=4)

# # Initialize user data
# user_data = load_user_data()

# # Function to register users
# def register_user(user_id, username):
#     if str(user_id) not in user_data:
#         user_data[str(user_id)] = {
#             "username": username,
#             "videos_downloaded": 0
#         }
#         save_user_data(user_data)

# # Function to download video using yt_dlp
# def download_video(url):
#     try:
#         # Options for yt_dlp
#         ydl_opts = {
#             'format': 'best',
#             'outtmpl': 'downloaded_video.mp4',  # Save the file locally
#             'quiet': True,  # Suppress unnecessary logs
#         }
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])  # Download the video
#         return 'downloaded_video.mp4'
#     except Exception as e:
#         raise Exception(f"Failed to download video: {e}")

# # Start command handler
# @bot.message_handler(commands=['start'])
# def welcome(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     register_user(user_id, username)

#     bot.reply_to(message, "Welcome! 👋 Send me a video link, and I'll download it for you.")

# # Message handler for video links
# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     register_user(user_id, username)

#     url = message.text.strip()

#     # Reply if the URL seems invalid
#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid video link.")
#         return

#     bot.reply_to(message, "⏳ Processing your request... Please wait.")

#     try:
#         # Download the video
#         file_path = download_video(url)

#         # Check file size (Telegram limit: 50 MB for free accounts)
#         if os.path.getsize(file_path) > 50 * 1024 * 1024:
#             bot.reply_to(message, "❌ Video is too large for Telegram. Try a smaller video.")
#             os.remove(file_path)  # Clean up the file
#             return

#         # Send the video to the user
#         with open(file_path, 'rb') as video:
#             bot.send_video(message.chat.id, video)

#         # Update user's download count
#         user_data[str(user_id)]["videos_downloaded"] += 1
#         save_user_data(user_data)

#         bot.reply_to(message, "✅ Done! Here's your video.")
#         os.remove(file_path)  # Clean up the file after sending

#     except Exception as e:
#         bot.reply_to(message, f"❌ An error occurred: {str(e)}")

# # Start the bot
# bot.polling()








# import telebot
# import yt_dlp
# import os
# import sqlite3
# import time
# from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
# from datetime import datetime

# # Replace with your bot token
# BOT_TOKEN = '7665537600:AAHggN60xuyzXP2gO_Us1Yg18IoDOLHa-6s'
# bot = telebot.TeleBot(BOT_TOKEN)

# # Database setup
# DB_FILE = 'bot_users.db'

# def init_db():
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     # Create the users table
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY,
#             username TEXT,
#             first_name TEXT,
#             last_name TEXT,
#             phone_number TEXT DEFAULT 'NotProvided',
#             videos_downloaded INTEGER DEFAULT 0,
#             referrals INTEGER DEFAULT 0,
#             start_time TEXT,
#             last_download_time TEXT,
#             language TEXT DEFAULT 'en'
#         )
#     ''')

#     # Check if the 'last_download_time' column exists, if not, add it
#     cursor.execute('''
#         PRAGMA table_info(users);
#     ''')
#     columns = [column[1] for column in cursor.fetchall()]
#     if 'last_download_time' not in columns:
#         cursor.execute('''
#             ALTER TABLE users ADD COLUMN last_download_time TEXT;
#         ''')

#     # Create the downloads table
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS downloads (
#             user_id INTEGER,
#             video_url TEXT,
#             download_time TEXT,
#             quality TEXT,
#             format TEXT,
#             FOREIGN KEY (user_id) REFERENCES users (id)
#         )
#     ''')
#     conn.commit()
#     conn.close()

# # Register a user
# def register_user(user_id, username, first_name, last_name):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
#     user_exists = cursor.fetchone()

#     if not user_exists:
#         start_time = time.strftime('%Y-%m-%d %H:%M:%S')
#         cursor.execute('''
#             INSERT INTO users (id, username, first_name, last_name, start_time)
#             VALUES (?, ?, ?, ?, ?)
#         ''', (user_id, username, first_name, last_name, start_time))
#         conn.commit()
#     conn.close()

# # Update user download count and log download
# def log_download(user_id, video_url, quality, format_type):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     last_download_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

#     # Update user's download count and time
#     cursor.execute('''
#         UPDATE users 
#         SET videos_downloaded = videos_downloaded + 1, last_download_time = ?
#         WHERE id = ?
#     ''', (last_download_time, user_id))

#     # Log the download
#     cursor.execute('''
#         INSERT INTO downloads (user_id, video_url, download_time, quality, format)
#         VALUES (?, ?, ?, ?, ?)
#     ''', (user_id, video_url, last_download_time, quality, format_type))
#     conn.commit()
#     conn.close()

# # Function to download video
# def download_video(url, quality, format_type):
#     try:
#         # Set options for yt-dlp based on format (audio or video)
#         if format_type == 'audio':
#             ydl_opts = {
#                 'format': 'bestaudio/best',  # Best audio quality
#                 'outtmpl': 'downloaded_audio.%(ext)s',  # Save as audio file
#                 'quiet': True,  # Suppress unnecessary logs
#             }
#         else:
#             # Set video format options based on the quality
#             ydl_opts = {
#                 'format': f'bestvideo[height<={quality}]+bestaudio/best',  # Video with specific quality
#                 'outtmpl': 'downloaded_video.%(ext)s',  # Save as video file
#                 'quiet': True,  # Suppress unnecessary logs
#             }

#         # Download the video or audio
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])  # Download the video/audio

#         # Return the correct file path (audio or video)
#         if format_type == 'audio':
#             return 'downloaded_audio.mp3'  # Assuming audio is downloaded as MP3
#         else:
#             return 'downloaded_video.mp4'  # Assuming video is downloaded as MP4

#     except Exception as e:
#         raise Exception(f"Failed to download video: {e}")

# # Start command handler
# @bot.message_handler(commands=['start'])
# def welcome(message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "unknown"
#     first_name = message.from_user.first_name or "Unknown"
#     last_name = message.from_user.last_name or "Unknown"

#     # Register the user
#     register_user(user_id, username, first_name, last_name)

#     # Display welcome message
#     bot.send_message(
#         message.chat.id,
#         "Welcome to the Instagram and YouTube Downloader Bot! 🚀\n"
#         "You can download videos in various formats and qualities.\n"
#         "Send a video link to get started."
#     )

# # Create a dictionary to store user URLs temporarily
# user_urls = {}

# # Message handler for video links
# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     user_id = message.from_user.id
#     url = message.text.strip()

#     # Validate URL
#     if not (url.startswith("http://") or url.startswith("https://")):
#         bot.reply_to(message, "❌ Please send a valid video link.")
#         return

#     # Store the URL in the dictionary for this user
#     user_urls[user_id] = url

#     # Ask for quality and format if the URL is valid
#     markup = InlineKeyboardMarkup()
#     markup.row(
#         InlineKeyboardButton("🔊 Audio Only", callback_data=f"audio_{user_id}"),
#         InlineKeyboardButton("📹 Video (Low)", callback_data=f"low_{user_id}")
#     )
#     markup.row(
#         InlineKeyboardButton("📹 Video (Medium)", callback_data=f"medium_{user_id}"),
#         InlineKeyboardButton("📹 Video (High)", callback_data=f"high_{user_id}")
#     )
#     bot.reply_to(message, "Choose the format and quality:", reply_markup=markup)

# # Callback handler for quality selection
# @bot.callback_query_handler(func=lambda call: True)
# def handle_callback(call):
#     user_id = call.from_user.id
#     data = call.data.split('_')
#     format_type = data[0]

#     # Get the video URL from the user_urls dictionary
#     url = user_urls.get(user_id)

#     if not url:
#         bot.send_message(call.message.chat.id, "❌ No valid URL found. Please send a video link first.")
#         return

#     # Quality mapping
#     quality_map = {'low': 360, 'medium': 720, 'high': 1080}
#     quality = quality_map.get(format_type, 720)

#     try:
#         bot.send_message(call.message.chat.id, "⏳ Downloading your video...")

#         # Adjust download function based on format (audio or video)
#         if format_type == 'audio':
#             file_path = download_video(url, quality, 'audio')  # Audio download
#             with open(file_path, 'rb') as audio:
#                 bot.send_audio(call.message.chat.id, audio)
#         else:
#             file_path = download_video(url, quality, 'video')  # Video download
#             with open(file_path, 'rb') as video:
#                 bot.send_video(call.message.chat.id, video)

#         # Log the download
#         log_download(user_id, url, quality, format_type)

#         # Clean up by deleting the downloaded file
#         os.remove(file_path)

#         bot.send_message(call.message.chat.id, "✅ Download complete!")
#     except Exception as e:
#         bot.send_message(call.message.chat.id, f"❌ Error: {str(e)}")


# # Initialize database and start the bot
# init_db()
# bot.polling()

