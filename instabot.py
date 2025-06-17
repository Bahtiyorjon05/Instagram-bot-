import telebot
import yt_dlp
import os
import time
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN missing in .env")

bot = telebot.TeleBot(BOT_TOKEN)

# Setup logger
logging.basicConfig(
    filename="bot_errors.log", 
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Delete old video files before download
def clean_downloads():
    for f in os.listdir():
        if f.startswith("downloaded_video"):
            try:
                os.remove(f)
            except:
                pass

# Download video from any link
def download_media(url):
    try:
        clean_downloads()
        
        # Configure platform-specific options
        if "instagram.com" in url:
            # Special handling for Instagram
            ydl_opts = {
                'format': 'best',
                'outtmpl': 'downloaded_video.%(ext)s',
                'quiet': False,  # Enable output for debugging
                'noplaylist': True,
                'retries': 10,
                'cookiefile': 'cookies.txt',
                'force_overwrites': True,
                'verbose': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'headers': {
                    'referer': 'https://www.instagram.com/',
                    'origin': 'https://www.instagram.com',
                }
            }
        elif "pinterest.com" in url:
            raise Exception("📌 Pinterest blocks downloads. Please use a different platform.")
        else:
            # General configuration for other platforms
            ydl_opts = {
                'format': 'bv*+ba/best',
                'outtmpl': 'downloaded_video.%(ext)s',
                'merge_output_format': 'mp4',
                'quiet': False,  # Enable output for debugging
                'noplaylist': True,
                'retries': 10,
                'cookiefile': 'cookies.txt',
                'force_overwrites': True,
                'ignoreerrors': False,  # Don't ignore errors to get better feedback
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }],
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
        
        # Log the URL being processed
        logging.info(f"Processing URL: {url}")
        
        # Try to download the media
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("❌ Failed to extract video info.")
            
            # Look for the downloaded file
            filename = ydl.prepare_filename(info)
            # Handle different extensions
            possible_extensions = ['.mp4', '.webm', '.mkv', '.mov', '.avi']
            
            # First try the prepared filename
            if os.path.exists(filename):
                return filename
                
            # Try with different extensions
            base_filename = os.path.splitext(filename)[0]
            for ext in possible_extensions:
                potential_file = base_filename + ext
                if os.path.exists(potential_file):
                    return potential_file
            
            # If we get here, try to find any downloaded file
            for file in os.listdir():
                if file.startswith("downloaded_video"):
                    return file
                    
            # If still no file found
            raise Exception("❌ Video file not found after download.")

    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        raise Exception(f"❌ Failed to download: {str(e)}")

# /start handler
@bot.message_handler(commands=["start"])
def handle_start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📱 Share Contact", request_contact=True))

    bot.send_message(
        message.chat.id,
        f"👋 Hello {message.from_user.first_name}!\n\nSend me any video link (YouTube, TikTok, Instagram, etc) and I’ll download it for you. Optionally, share your contact.",
        reply_markup=markup
    )

# Contact handler
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact:
        bot.reply_to(message, "✅ Thank you! You're registered. Now send a video link.")

# Link handler
@bot.message_handler(func=lambda msg: True)
def handle_video_link(message):
    url = message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "❌ Please send a valid link.")
        return

    status_message = bot.reply_to(message, "⏳ Downloading your video...")
    logging.info(f"Processing URL from user {message.from_user.id}: {url}")

    try:
        file_path = download_media(url)
        
        if not os.path.exists(file_path):
            bot.edit_message_text("❌ Download failed: File not found", 
                                 message.chat.id, status_message.message_id)
            return
            
        file_size = os.path.getsize(file_path)
        logging.info(f"Downloaded file: {file_path}, size: {file_size} bytes")

        if file_size > 50 * 1024 * 1024:
            bot.edit_message_text("❌ File is too large for Telegram (50MB max).", 
                                 message.chat.id, status_message.message_id)
            os.remove(file_path)
            return
        elif file_size == 0:
            bot.edit_message_text("❌ Downloaded file is empty.", 
                                 message.chat.id, status_message.message_id)
            os.remove(file_path)
            return

        bot.edit_message_text("📤 Uploading to Telegram...", 
                             message.chat.id, status_message.message_id)
                             
        try:
            with open(file_path, 'rb') as video:
                sent_message = bot.send_document(message.chat.id, video)
                if sent_message:
                    bot.reply_to(message, "✅ Done! Here's your file.")
                else:
                    bot.reply_to(message, "❌ Failed to send the file to Telegram.")
        except Exception as upload_error:
            logging.error(f"Upload error: {str(upload_error)}")
            bot.edit_message_text(f"❌ Upload failed: {str(upload_error)}", 
                                 message.chat.id, status_message.message_id)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as e:
        error_message = str(e)
        logging.error(f"Download error: {error_message}")
        
        # Provide more helpful error messages
        if "Video file not found" in error_message:
            bot.edit_message_text("❌ Could not download this video. The platform may be blocking downloads.", 
                                 message.chat.id, status_message.message_id)
        elif "Unsupported URL" in error_message:
            bot.edit_message_text("❌ This URL is not supported.", 
                                 message.chat.id, status_message.message_id)
        else:
            bot.edit_message_text(f"❌ Error: {error_message}", 
                                 message.chat.id, status_message.message_id)

# Use a more robust polling method
try:
    logging.info("Bot started successfully")
    bot.polling(none_stop=True, interval=1, timeout=60)
except Exception as e:
    logging.error(f"Bot polling error: {str(e)}")
    # Try to restart polling after error
    bot.stop_polling()
    time.sleep(10)
    bot.polling(none_stop=True, interval=1, timeout=60)
