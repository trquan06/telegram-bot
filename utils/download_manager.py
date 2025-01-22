import time
import humanize
import zipfile
import os
import shutil
from datetime import timedelta

class DownloadManager:
    def __init__(self):
        self.active_downloads = {}
        self.progress_messages = {}
        self.download_speeds = {}
        self.start_times = {}

    async def update_progress(self, current, total, message_id, chat_id):
        if total == 0:
            return

        now = time.time()
        start_time = self.start_times.get((message_id, chat_id), now)
        
        # Calculate speed and progress
        elapsed_time = now - start_time
        if elapsed_time == 0:
            speed = 0
        else:
            speed = current / elapsed_time  # bytes per second

        progress = (current / total) * 100
        
        # Format progress message
        progress_text = (
            f"📥 Downloading: {progress:.1f}%\n"
            f"💨 Speed: {humanize.naturalsize(speed)}/s\n"
            f"📦 Size: {humanize.naturalsize(current)}/{humanize.naturalsize(total)}\n"
            f"⏱ Elapsed: {timedelta(seconds=int(elapsed_time))}"
        )

        return progress_text

    def start_download(self, message_id, chat_id):
        self.start_times[(message_id, chat_id)] = time.time()

    def finish_download(self, message_id, chat_id):
        if (message_id, chat_id) in self.start_times:
            del self.start_times[(message_id, chat_id)]

    async def handle_downloaded_file(self, file_path, message):
        """Handle downloaded file, including automatic ZIP extraction"""
        try:
            if file_path.lower().endswith('.zip'):
                await self.extract_archive(file_path, message)
            return True
        except Exception as e:
            await message.reply(f"Error handling downloaded file: {str(e)}")
            return False

    async def extract_archive(self, file_path, message):
        """Extract ZIP archive directly to download folder"""
        try:
            download_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            
            if file_path.lower().endswith('.zip'):
                status_msg = await message.reply(f"📦 Extracting {file_name}...")
                
                extracted_files = []
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    # Extract all files directly to download directory
                    for zip_info in zip_ref.infolist():
                        if not zip_info.filename.endswith('/'):  # Skip directories
                            extracted_name = os.path.basename(zip_info.filename)
                            target_path = os.path.join(download_dir, extracted_name)
                            
                            # Extract the file
                            with zip_ref.open(zip_info) as source, open(target_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                            extracted_files.append(extracted_name)
                
                # Remove the original zip file after extraction
                os.remove(file_path)
                
                # Update status message
                await status_msg.edit_text(
                    f"✅ Archive extracted successfully!\n"
                    f"📂 Location: {download_dir}\n"
                    f"📑 Files extracted: {len(extracted_files)}\n"
                )
            
        except Exception as e:
            await message.reply(f"❌ Error extracting archive: {str(e)}")
