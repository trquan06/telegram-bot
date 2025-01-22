# utils/error_handler.py
from typing import Optional, Dict, Any
import traceback
import asyncio
from datetime import datetime
import logging
from dataclasses import dataclass, field

@dataclass
class ErrorRecord:
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: str = ""
    retry_count: int = 0
    resolved: bool = False

class ErrorHandler:
    def __init__(self):
        self.error_records: Dict[str, ErrorRecord] = {}
        self.logger = logging.getLogger('ErrorHandler')
        self.max_retries = 3
        self._setup_logging()

    def _setup_logging(self):
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        error_handler = logging.FileHandler('logs/errors.log')
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)

    async def handle_error(self, error: Exception, context: str = "", retry_func = None) -> Optional[ErrorRecord]:
        error_id = f"{context}_{datetime.utcnow().timestamp()}"
        
        error_record = ErrorRecord(
            error_type=type(error).__name__,
            message=str(error),
            context={"context": context},
            stack_trace=traceback.format_exc()
        )
        
        self.error_records[error_id] = error_record
        
        # Log the error
        self.logger.error(
            f"Error in {context}: {str(error)}\n"
            f"Stack trace:\n{error_record.stack_trace}"
        )

        # Handle specific error types
        if isinstance(error, asyncio.TimeoutError):
            return await self._handle_timeout_error(error_record, retry_func)
        elif "FloodWait" in str(error):
            return await self._handle_flood_wait(error_record, error)
        elif "ChatNotFound" in str(error):
            return self._handle_chat_not_found(error_record)
        
        return error_record

    async def _handle_timeout_error(self, error_record: ErrorRecord, retry_func) -> ErrorRecord:
        if retry_func and error_record.retry_count < self.max_retries:
            error_record.retry_count += 1
            self.logger.info(f"Retrying operation. Attempt {error_record.retry_count}/{self.max_retries}")
            try:
                await retry_func()
                error_record.resolved = True
            except Exception as e:
                self.logger.error(f"Retry attempt {error_record.retry_count} failed: {str(e)}")
        return error_record

    async def _handle_flood_wait(self, error_record: ErrorRecord, error) -> ErrorRecord:
        wait_time = int(str(error).split()[1])
        self.logger.warning(f"FloodWait error. Waiting for {wait_time} seconds")
        await asyncio.sleep(wait_time)
        error_record.context["wait_time"] = wait_time
        return error_record

    def _handle_chat_not_found(self, error_record: ErrorRecord) -> ErrorRecord:
        self.logger.error("Chat not found error")
        error_record.context["recoverable"] = False
        return error_record

    def get_error_summary(self) -> Dict[str, int]:
        error_counts = {}
        for error in self.error_records.values():
            error_type = error.error_type
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return error_counts
