# utils/base_util.py
from typing import Optional, Any, Dict
import logging
import os
from datetime import datetime
from dataclasses import dataclass, field
# Add at the top of base_util.py
class OperationStatus:
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class OperationType:
    DOWNLOAD = "download"
    UPLOAD = "upload"
    API_REQUEST = "api_request"
    SYSTEM = "system"
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
        """Enhanced operation logging with more context"""
        log_level = logging.ERROR if not result.success else logging.INFO
        
        log_context = {
            "operation": operation,
            "success": result.success,
            "message": result.message,
            "timestamp": result.timestamp.isoformat(),
        }
        
        if result.data:
            log_context["data"] = result.data
            
        if result.error:
            log_context["error_type"] = type(result.error).__name__
            log_context["error_details"] = str(result.error)
            self.logger.error(
                f"Error in operation {operation}",
                extra={"context": log_context}
            )
        else:
            self.logger.log(
                log_level,
                f"Operation {operation} completed",
                extra={"context": log_context}
            )
                f"Error type: {type(result.error).__name__}"
            )
def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f}TB"

    async def safe_execution(self, func, *args, operation_name: str = "", **kwargs) -> OperationResult:
        """Safely execute a function with error handling"""
        try:
            result = await func(*args, **kwargs)
            return OperationResult(
                success=True,
                message=f"{operation_name} completed successfully",
                data=result
            )
        except Exception as e:
            self.logger.exception(f"Error in {operation_name}")
            return OperationResult(
                success=False,
                message=f"{operation_name} failed: {str(e)}",
                error=e
            )
