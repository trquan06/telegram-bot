# utils/logger.py
import logging
import os
from datetime import datetime
from functools import wraps
import time

class BotLogger:
    def __init__(self):
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Set up file handler
        log_file = f'logs/bot_{datetime.utcnow().strftime("%Y%m%d")}.log'
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TelegramBot')

    def log_command(self, message):
        user_id = message.from_user.id if message.from_user else "Unknown"
        command = message.text if message.text else "Non-text command"
        self.logger.info(f"Command received - User: {user_id} - Command: {command}")

    def log_download(self, url, status, error=None):
        if error:
            self.logger.error(f"Download failed - URL: {url} - Error: {error}")
        else:
            self.logger.info(f"Download {status} - URL: {url}")

    def log_error(self, error, context=""):
        self.logger.error(f"Error occurred in {context}: {str(error)}")

bot_logger = BotLogger()

# Performance monitoring decorator
def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            bot_logger.logger.info(
                f"Function {func.__name__} completed in {elapsed_time:.2f} seconds"
            )
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            bot_logger.logger.error(
                f"Function {func.__name__} failed after {elapsed_time:.2f} seconds: {str(e)}"
            )
            raise
    return wrapper
