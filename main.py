from pyrogram import Client, filters
import os
import asyncio
from config import Config
from handlers.message_handlers import handle_message
from handlers.upload_handler import UploadHandler
from utils.error_handler import ErrorHandler
from utils.state_manager import StateManager
from utils.download_manager import DownloadManager
from utils.flood_handler import FloodWaitHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.maintenance import MaintenanceManager

class TelegramBot:
    def __init__(self):
        # Initialize configuration and components
        self.config = Config()
        self.error_handler = ErrorHandler()
        self.state_manager = StateManager(self.config.MAX_CONCURRENT_DOWNLOADS)
        self.flood_handler = FloodWaitHandler()
        self.download_manager = DownloadManager()
        self.upload_handler = UploadHandler(self.config)
        self.maintenance_manager = MaintenanceManager(self.config)

        # Initialize the bot client
        self.app = Client(
            "telegram_downloader",
            api_id=self.config.API_IDS[0],
            api_hash=self.config.API_HASHES[0],
            bot_token=self.config.BOT_TOKEN,
            sleep_threshold=60,
            max_concurrent_transmissions=self.config.MAX_CONCURRENT_DOWNLOADS
        )

        # Set up maintenance scheduler
        self.scheduler = AsyncIOScheduler()
        self._setup_scheduler()
        self._register_handlers()

    def _setup_scheduler(self):
        """Setup maintenance tasks scheduler"""
        self.scheduler.add_job(self.maintenance_manager.cleanup_old_files, 'cron', hour=0)
        self.scheduler.add_job(self.maintenance_manager.rotate_logs, 'cron', hour=12)
        self.scheduler.add_job(self.maintenance_manager.check_disk_space, 'interval', hours=1)
        self.scheduler.start()

    def _register_handlers(self):
        """Register message handlers"""
        # Command handlers
        self.app.on_message(filters.command("start"))(self.start_command)
        self.app.on_message(filters.command("download"))(self.download_command)
        self.app.on_message(filters.command("stop"))(self.stop_command)
        self.app.on_message(filters.command("upload"))(self.upload_command)
        self.app.on_message(filters.command("retry_upload"))(self.retry_upload_command)
        self.app.on_message(filters.command("status"))(self.status_command)
        
        # General message handler
        self.app.on_message()(self.message_handler)

    async def start_command(self, client, message):
        """Handle /start command"""
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

    async def download_command(self, client, message):
        """Handle /download command"""
        try:
            if len(message.command) < 2:
                await message.reply("⚠️ Please provide a URL to download")
                return

            url = message.command[1]
            await self.download_manager.process_download(client, message, url)
        except Exception as e:
            await self.error_handler.handle_error(e, "download_command")
            await message.reply("❌ Download failed. Check /status for details.")

    async def stop_command(self, client, message):
        """Handle /stop command"""
        try:
            await self.state_manager.stop_all_operations()
            await message.reply("✅ All operations stopped")
        except Exception as e:
            await self.error_handler.handle_error(e, "stop_command")
            await message.reply("❌ Error stopping operations")

    async def upload_command(self, client, message):
        """Handle /upload command"""
        try:
            await self.upload_handler.upload_to_google_photos(message)
        except Exception as e:
            await self.error_handler.handle_error(e, "upload_command")
            await message.reply("❌ Upload failed")

    async def retry_upload_command(self, client, message):
        """Handle /retry_upload command"""
        try:
            await self.upload_handler.retry_upload(message)
        except Exception as e:
            await self.error_handler.handle_error(e, "retry_upload_command")
            await message.reply("❌ Retry failed")

    async def status_command(self, client, message):
        """Handle /status command"""
        try:
            status = await self.state_manager.get_status()
            error_summary = self.error_handler.get_error_summary()
            
            status_text = (
                f"📊 System Status:\n{status}\n\n"
                f"⚠️ Errors:\n{error_summary}\n\n"
                f"💾 Storage:\n"
                f"Free Space: {await self.maintenance_manager.get_free_space()}MB"
            )
            
            await message.reply(status_text)
        except Exception as e:
            await self.error_handler.handle_error(e, "status_command")
            await message.reply("❌ Error getting status")

    async def message_handler(self, client, message):
        """Handle general messages"""
        try:
            await handle_message(client, message, self.state_manager, self.download_manager)
        except Exception as e:
            await self.error_handler.handle_error(e, "message_handler")

    def run(self):
        """Start the bot"""
        print("Bot starting...")
        if not os.path.exists(self.config.BASE_DOWNLOAD_FOLDER):
            os.makedirs(self.config.BASE_DOWNLOAD_FOLDER)
        self.app.run()

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
