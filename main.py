from pyrogram import Client
import asyncio
import os
from config import Config
from utils.flood_handler import FloodWaitHandler
from utils.download_manager import DownloadManager
from utils.system_monitor import get_system_status
from handlers.command_handlers import (
    start_command, download_command, stop_command,
    upload_command, status_command
)
from handlers.message_handlers import handle_message

# Initialize configuration
config = Config()

# Initialize components
flood_handler = FloodWaitHandler()
download_manager = DownloadManager()
download_lock = asyncio.Lock()
download_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)

# Global state
downloading = False
uploading = False
failed_files = []
error_messages = set()

# Initialize the bot
app = Client(
    "telegram_downloader",
    api_id=config.API_IDS[0],
    api_hash=config.API_HASHES[0],
    bot_token=config.BOT_TOKEN,
    sleep_threshold=60,
    max_concurrent_transmissions=config.MAX_CONCURRENT_DOWNLOADS
)

# Register command handlers
app.on_message(filters.command("start"))(start_command)
app.on_message(filters.command("download"))(
    lambda c, m: download_command(c, m, download_lock, downloading, download_from_url)
)
app.on_message(filters.command("stop"))(
    lambda c, m: stop_command(c, m, download_lock, downloading, uploading)
)
app.on_message(filters.command("upload"))(
    lambda c, m: upload_command(c, m, uploading, config.BASE_DOWNLOAD_FOLDER)
)
app.on_message(filters.command("status"))(
    lambda c, m: status_command(c, m, get_system_status, config, download_semaphore, failed_files, flood_handler)
)

# Register message handler
app.on_message()(
    lambda c, m: handle_message(c, m, downloading, download_from_url)
)

# Start the bot
if __name__ == "__main__":
    print("Bot starting...")
    if not os.path.exists(config.BASE_DOWNLOAD_FOLDER):
        os.makedirs(config.BASE_DOWNLOAD_FOLDER)
    app.run()
