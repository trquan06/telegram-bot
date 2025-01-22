# utils/maintenance.py
import os
import shutil
from datetime import datetime, timedelta
import logging

class MaintenanceManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('Maintenance')

    async def cleanup_old_files(self, days_old=7):
        """Clean up files older than specified days"""
        cleanup_before = datetime.now() - timedelta(days=days_old)
        
        download_dir = self.config.BASE_DOWNLOAD_FOLDER
        for root, dirs, files in os.walk(download_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                
                if file_time < cleanup_before:
                    try:
                        os.remove(file_path)
                        self.logger.info(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up {file_path}: {e}")

    async def rotate_logs(self, max_logs=30):
        """Rotate log files, keeping only the most recent ones"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return

        log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.log')])
        while len(log_files) > max_logs:
            oldest_log = os.path.join(log_dir, log_files.pop(0))
            try:
                os.remove(oldest_log)
                self.logger.info(f"Removed old log file: {oldest_log}")
            except Exception as e:
                self.logger.error(f"Error removing log file {oldest_log}: {e}")

    async def check_disk_space(self, min_free_space_mb=500):
        """Check if there's enough disk space"""
        free_space = shutil.disk_usage(self.config.BASE_DOWNLOAD_FOLDER).free / (1024 * 1024)
        if free_space < min_free_space_mb:
            self.logger.warning(f"Low disk space: {free_space:.2f}MB free")
            return False
        return True
