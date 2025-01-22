# utils/base_util.py
from typing import Optional, Any, Dict
import logging
import os
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class OperationResult:
    """Generic result object for operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

class BaseUtil:
    """Base class for utility modules"""
    def __init__(self, config=None):
        self.config = config
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the utility"""
        logger = logging.getLogger(self.__class__.__name__)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        file_handler = logging.FileHandler(
            f'logs/{self.__class__.__name__.lower()}.log'
        )
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
        
        return logger

    async def log_operation(self, operation: str, result: OperationResult):
        """Log operation details"""
        log_level = logging.ERROR if not result.success else logging.INFO
        
        self.logger.log(
            log_level,
            f"Operation: {operation} - Success: {result.success} - "
            f"Message: {result.message}"
        )
        
        if result.error:
            self.logger.error(
                f"Error details: {str(result.error)}\n"
                f"Error type: {type(result.error).__name__}"
            )
