from pyrogram import Client, filters
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
from handlers.upload_handler import UploadHandler
from utils.error_handler import ErrorHandler
from utils.api_manager import APIManager, DownloadOptimizer
from utils.state_manager import StateManager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.maintenance import MaintenanceManager
# Initialize configuration
config = Config()

# Initialize components
config = Config()
error_handler = ErrorHandler()
state_manager = StateManager(config.MAX_CONCURRENT_DOWNLOADS)
flood_handler = FloodWaitHandler()
download_manager = DownloadManager()
upload_handler = UploadHandler(config)
error_handler = ErrorHandler()
api_manager = APIManager(config.API_CREDENTIALS)
download_optimizer = DownloadOptimizer(max_concurrent=config.MAX_CONCURRENT_DOWNLOADS)
# Global state
downloading = False
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
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "Welcome! Available commands:\n"
        "/download - Start download mode\n"
        "/stop - Stop all operations\n"
        "/upload - Sync files to Google Photos\n"
        "/retry_upload - Retry failed uploads\n"
        "/retry_download - Retry failed downloads\n"
        "/status - Check system status\n"
        "You can also send a URL to download directly"
    )

# Modify your download command to use the new optimizations:
@app.on_message(filters.command("download"))
async def download_command(client, message):
    try:
        if len(message.command) < 2:
            await message.reply("Please provide a URL to download")
            return

        url = message.command[1]
        
        async def download_operation():
            # Your download logic here, using api_manager and download_optimizer
            await api_manager.make_request(
                download_optimizer.download_file,
                client, message, file_id, file_size
            )

        await download_operation()
        
    except Exception as e:
        error_record = await error_handler.handle_error(
            e, 
            "download_command",
            retry_func=download_operation
        )
        
        if error_record.resolved:
            await message.reply("Download completed after retry")
        else:
            await message.reply(
                f"Failed to download: {error_record.message}\n"
                f"Error ID: {error_record.error_type}"
            )
app.on_message(filters.command("stop"))(
    lambda c, m: stop_command(c, m, download_lock, downloading)
)
app.on_message(filters.command("upload"))(
    lambda c, m: upload_handler.upload_to_google_photos(m)
)
app.on_message(filters.command("retry_upload"))(
    lambda c, m: upload_handler.retry_upload(m)
)
app.on_message(filters.command("status"))(
    lambda c, m: status_command(c, m, get_system_status, config, download_semaphore, failed_files, flood_handler)
)

# Register message handler for downloads
app.on_message()(
    lambda c, m: handle_message(c, m, downloading, download_from_url)
)
# Update error handling in command handlers
@app.on_message(filters.command("status"))
async def status(client, message):
    try:
        system_status = get_system_status()
        active_downloads = state_manager.get_active_downloads()
        recent_errors = error_handler.get_recent_errors()
        
        status_text = (
            f"🖥 System Status:\n{system_status}\n\n"
            f"📥 Active Downloads: {len(active_downloads)}\n"
            f"❌ Failed Files: {len(state_manager.failed_files)}\n"
            f"⚠️ Recent Errors: {len(recent_errors)}\n"
        )
        
        await message.reply(status_text)
    except Exception as e:
        error_msg = await error_handler.handle_error(e, "status command")
        await message.reply(f"Error getting status: {error_msg}")
# Initialize maintenance manager
maintenance_manager = MaintenanceManager(config)

# Set up scheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(maintenance_manager.cleanup_old_files, 'cron', hour=0)
scheduler.add_job(maintenance_manager.rotate_logs, 'cron', hour=12)
scheduler.add_job(maintenance_manager.check_disk_space, 'interval', hours=1)
scheduler.start()        
# Start the bot
if __name__ == "__main__":
    print("Bot starting...")
    if not os.path.exists(config.BASE_DOWNLOAD_FOLDER):
        os.makedirs(config.BASE_DOWNLOAD_FOLDER)
    app.run()
