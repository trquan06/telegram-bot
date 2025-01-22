# utils/error_handler.py
from typing import Optional, Dict, Any, Callable, Awaitable
import traceback
import asyncio
from datetime import datetime
from .base_util import BaseUtil, OperationResult

class ErrorType:
    """Enum-like class for error types"""
    TIMEOUT = "TIMEOUT"
    FLOOD_WAIT = "FLOOD_WAIT"
    CHAT_NOT_FOUND = "CHAT_NOT_FOUND"
    NETWORK = "NETWORK"
    PERMISSION = "PERMISSION"
    RATE_LIMIT = "RATE_LIMIT"
    UNKNOWN = "UNKNOWN"

class ErrorHandler(BaseUtil):
    def __init__(self, config=None):
        super().__init__(config)
        self.error_records: Dict[str, Dict[str, Any]] = {}
        self.max_retries = config.MAX_RETRIES if config else 3
        self.retry_delay = config.RETRY_DELAY if config else 5
        self._error_handlers = self._register_error_handlers()

    def _register_error_handlers(self) -> Dict[str, Callable]:
        """Register specific error handlers"""
        return {
            ErrorType.TIMEOUT: self._handle_timeout_error,
            ErrorType.FLOOD_WAIT: self._handle_flood_wait,
            ErrorType.CHAT_NOT_FOUND: self._handle_chat_not_found,
            ErrorType.NETWORK: self._handle_network_error,
            ErrorType.PERMISSION: self._handle_permission_error,
            ErrorType.RATE_LIMIT: self._handle_rate_limit_error
        }

    async def handle_error(
        self,
        error: Exception,
        context: str = "",
        retry_func: Optional[Callable[[], Awaitable[Any]]] = None
    ) -> OperationResult:
        """Handle errors with improved context and retry support"""
        error_type = self._categorize_error(error)
        error_id = f"{context}_{datetime.utcnow().timestamp()}"
        
        # Create error record
        error_record = {
            "error_type": error_type,
            "message": str(error),
            "context": context,
            "stack_trace": traceback.format_exc(),
            "timestamp": datetime.utcnow(),
            "retry_count": 0,
            "resolved": False
        }
        
        self.error_records[error_id] = error_record
        
        # Log error
        await self.log_operation(
            f"Error in {context}",
            OperationResult(
                success=False,
                message=str(error),
                error=error,
                data={"error_type": error_type}
            )
        )

        # Handle specific error type
        handler = self._error_handlers.get(error_type, self._handle_unknown_error)
        result = await handler(error_record, error, retry_func)
        
        return result

    def _categorize_error(self, error: Exception) -> str:
        """Categorize error type"""
        if isinstance(error, asyncio.TimeoutError):
            return ErrorType.TIMEOUT
        elif "FloodWait" in str(error):
            return ErrorType.FLOOD_WAIT
        elif "ChatNotFound" in str(error):
            return ErrorType.CHAT_NOT_FOUND
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorType.NETWORK
        elif "permission" in str(error).lower():
            return ErrorType.PERMISSION
        elif "rate limit" in str(error).lower():
            return ErrorType.RATE_LIMIT
        return ErrorType.UNKNOWN

    async def _handle_timeout_error(
        self,
        error_record: Dict[str, Any],
        error: Exception,
        retry_func: Optional[Callable]
    ) -> OperationResult:
        """Handle timeout errors with exponential backoff"""
        if not retry_func or error_record["retry_count"] >= self.max_retries:
            return OperationResult(
                success=False,
                message="Max retries exceeded",
                error=error
            )

        retry_delay = self.retry_delay * (2 ** error_record["retry_count"])
        error_record["retry_count"] += 1
        
        self.logger.info(
            f"Retrying operation after {retry_delay}s. "
            f"Attempt {error_record['retry_count']}/{self.max_retries}"
        )
        
        await asyncio.sleep(retry_delay)
        
        try:
            await retry_func()
            error_record["resolved"] = True
            return OperationResult(
                success=True,
                message="Operation succeeded after retry",
                data={"retry_count": error_record["retry_count"]}
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Retry failed: {str(e)}",
                error=e
            )

    async def _handle_flood_wait(
        self,
        error_record: Dict[str, Any],
        error: Exception,
        retry_func: Optional[Callable]
    ) -> OperationResult:
        """Handle flood wait errors"""
        wait_time = int(str(error).split()[1])
        error_record["wait_time"] = wait_time
        
        self.logger.warning(f"FloodWait error. Waiting for {wait_time} seconds")
        await asyncio.sleep(wait_time)
        
        if retry_func:
            try:
                await retry_func()
                error_record["resolved"] = True
                return OperationResult(
                    success=True,
                    message="Operation succeeded after flood wait",
                    data={"wait_time": wait_time}
                )
            except Exception as e:
                return OperationResult(
                    success=False,
                    message=f"Operation failed after flood wait: {str(e)}",
                    error=e
                )
        
        return OperationResult(
            success=False,
            message=f"Flood wait handled, but no retry function provided",
            data={"wait_time": wait_time}
        )

    async def _handle_network_error(
        self,
        error_record: Dict[str, Any],
        error: Exception,
        retry_func: Optional[Callable]
    ) -> OperationResult:
        """Handle network-related errors"""
        if retry_func:
            return await self._handle_timeout_error(error_record, error, retry_func)
        return OperationResult(
            success=False,
            message="Network error occurred",
            error=error
        )

    async def _handle_permission_error(
        self,
        error_record: Dict[str, Any],
        error: Exception,
        retry_func: Optional[Callable]
    ) -> OperationResult:
        """Handle permission-related errors"""
        error_record["recoverable"] = False
        return OperationResult(
            success=False,
            message="Permission error occurred",
            error=error,
            data={"recoverable": False}
        )

    async def _handle_rate_limit_error(
        self,
        error_record: Dict[str, Any],
        error: Exception,
        retry_func: Optional[Callable]
    ) -> OperationResult:
        """Handle rate limit errors"""
        wait_time = self.retry_delay
        error_record["wait_time"] = wait_time
        
        self.logger.warning(f"Rate limit hit. Waiting for {wait_time} seconds")
        await asyncio.sleep(wait_time)
        
        if retry_func:
            return await self._handle_timeout_error(error_record, error, retry_func)
        
        return OperationResult(
            success=False,
            message="Rate limit error handled",
            data={"wait_time": wait_time}
        )

    async def _handle_chat_not_found(
        self,
        error_record: Dict[str, Any],
        error: Exception,
        retry_func: Optional[Callable]
    ) -> OperationResult:
        """Handle chat not found errors"""
        error_record["recoverable"] = False
        return OperationResult(
            success=False,
            message="Chat not found",
            error=error,
            data={"recoverable": False}
        )

    async def _handle_unknown_error(
        self,
        error_record: Dict[str, Any],
        error: Exception,
        retry_func: Optional[Callable]
    ) -> OperationResult:
        """Handle unknown errors"""
        if retry_func and error_record["retry_count"] < self.max_retries:
            return await self._handle_timeout_error(error_record, error, retry_func)
        
        return OperationResult(
            success=False,
            message=f"Unknown error occurred: {str(error)}",
            error=error
        )

    def get_error_summary(
        self,
        time_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Get summary of errors with optional time range filter"""
        summary = {
            "total_errors": 0,
            "resolved_errors": 0,
            "error_types": {},
            "recent_errors": []
        }

        for error_record in self.error_records.values():
            if time_range:
                start_time, end_time = time_range
                if not start_time <= error_record["timestamp"] <= end_time:
                    continue

            summary["total_errors"] += 1
            if error_record["resolved"]:
                summary["resolved_errors"] += 1

            error_type = error_record["error_type"]
            summary["error_types"][error_type] = summary["error_types"].get(error_type, 0) + 1

            # Add to recent errors if within last hour
            if datetime.utcnow() - error_record["timestamp"] < timedelta(hours=1):
                summary["recent_errors"].append({
                    "type": error_type,
                    "message": error_record["message"],
                    "context": error_record["context"],
                    "timestamp": error_record["timestamp"]
                })

        return summary

    def clear_old_errors(self, hours: int = 24):
        """Clear error records older than specified hours"""
        current_time = datetime.utcnow()
        self.error_records = {
            k: v for k, v in self.error_records.items()
            if (current_time - v["timestamp"]).total_seconds() < hours * 3600
        }
