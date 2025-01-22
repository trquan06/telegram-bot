# utils/error_handler.py
import logging
import traceback
from datetime import datetime

class ErrorHandler:
    def __init__(self):
        self.setup_logging()
        self.error_messages = set()

    def setup_logging(self):
        logging.basicConfig(
            filename=f'logs/bot_{datetime.utcnow().strftime("%Y%m%d")}.log',
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)

    async def handle_error(self, error, context=None):
        error_message = f"Error: {str(error)}"
        self.error_messages.add(error_message)
        
        # Log the full error with traceback
        self.logger.error(
            f"Error occurred: {error_message}\n"
            f"Context: {context}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        
        return error_message

    def get_recent_errors(self, limit=5):
        return list(self.error_messages)[-limit:]

    def clear_errors(self):
        self.error_messages.clear()
