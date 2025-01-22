import time
import humanize
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
