# handlers/base_handler.py
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class OperationResult:
    success: bool
    message: str
    error: Optional[Exception] = None
    data: Optional[dict] = None

class BaseHandler:
    def __init__(self, config, error_handler):
        self.config = config
        self.error_handler = error_handler
        self.logger = logging.getLogger(self.__class__.__name__)

    async def log_operation(self, operation: str, status: str, details: dict = None):
        """Log operation details"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "status": status,
            "details": details or {}
        }
        self.logger.info(f"Operation log: {log_entry}")
        return log_entry

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f}TB"
