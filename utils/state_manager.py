# utils/state_manager.py
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
from .base_util import BaseUtil, OperationResult

class OperationType:
    """Enum for operation types"""
    DOWNLOAD = "download"
    UPLOAD = "upload"
    PROCESSING = "processing"
    MAINTENANCE = "maintenance"

class OperationStatus:
    """Enum for operation statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class StateManager(BaseUtil):
    def __init__(self, config=None):
        super().__init__(config)
        # Operation states
        self._operations: Dict[str, Dict[str, Any]] = {}
        self._active_operations: Dict[str, Set[str]] = defaultdict(set)
        self._operation_locks: Dict[str, asyncio.Lock] = {}
        
        # Resource limits
        self.max_concurrent_downloads = config.MAX_CONCURRENT_DOWNLOADS if config else 5
        self.max_concurrent_uploads = config.MAX_CONCURRENT_UPLOADS if config else 3
        self.max_retries = config.MAX_RETRIES if config else 3
        
        # Statistics
        self._stats = defaultdict(lambda: defaultdict(int))
        
        # Initialize locks for different operation types
        for op_type in vars(OperationType).values():
            if isinstance(op_type, str):
                self._operation_locks[op_type] = asyncio.Lock()

    async def start_operation(
        self,
        operation_type: str,
        operation_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OperationResult:
        """Start a new operation with proper resource management"""
        async with self._operation_locks[operation_type]:
            # Check resource limits
            if not await self._can_start_operation(operation_type):
                return OperationResult(
                    success=False,
                    message=f"Resource limit reached for {operation_type} operations",
                    data={"current_count": len(self._active_operations[operation_type])}
                )

            # Initialize operation
            operation = {
                "type": operation_type,
                "id": operation_id,
                "status": OperationStatus.RUNNING,
                "start_time": datetime.utcnow(),
                "metadata": metadata or {},
                "progress": 0,
                "retry_count": 0,
                "errors": []
            }

            self._operations[operation_id] = operation
            self._active_operations[operation_type].add(operation_id)
            self._stats[operation_type]["total"] += 1
            self._stats[operation_type]["active"] += 1

            await self.log_operation(
                f"Started {operation_type} operation",
                OperationResult(
                    success=True,
                    message=f"Operation {operation_id} started",
                    data=operation
                )
            )

            return OperationResult(
                success=True,
                message=f"{operation_type} operation started",
                data=operation
            )

    async def update_operation_progress(
        self,
        operation_id: str,
        progress: float,
        status_message: Optional[str] = None
    ) -> OperationResult:
        """Update operation progress"""
        if operation_id not in self._operations:
            return OperationResult(
                success=False,
                message=f"Operation {operation_id} not found"
            )

        operation = self._operations[operation_id]
        operation["progress"] = progress
        
        if status_message:
            operation["status_message"] = status_message

        return OperationResult(
            success=True,
            message="Progress updated",
            data={"progress": progress}
        )

    async def complete_operation(
        self,
        operation_id: str,
        status: str = OperationStatus.COMPLETED,
        result: Optional[Dict[str, Any]] = None
    ) -> OperationResult:
        """Complete an operation"""
        if operation_id not in self._operations:
            return OperationResult(
                success=False,
                message=f"Operation {operation_id} not found"
            )

        operation = self._operations[operation_id]
        operation_type = operation["type"]

        async with self._operation_locks[operation_type]:
            operation["status"] = status
            operation["end_time"] = datetime.utcnow()
            operation["result"] = result

            self._active_operations[operation_type].remove(operation_id)
            self._stats[operation_type]["active"] -= 1
            
            if status == OperationStatus.COMPLETED:
                self._stats[operation_type]["completed"] += 1
            elif status == OperationStatus.FAILED:
                self._stats[operation_type]["failed"] += 1

            await self.log_operation(
                f"Completed {operation_type} operation",
                OperationResult(
                    success=True,
                    message=f"Operation {operation_id} completed with status {status}",
                    data=operation
                )
            )

            return OperationResult(
                success=True,
                message=f"Operation completed with status {status}",
                data=operation
            )

    async def pause_operation(self, operation_id: str) -> OperationResult:
        """Pause an active operation"""
        if operation_id not in self._operations:
            return OperationResult(
                success=False,
                message=f"Operation {operation_id} not found"
            )

        operation = self._operations[operation_id]
        if operation["status"] != OperationStatus.RUNNING:
            return OperationResult(
                success=False,
                message=f"Operation {operation_id} is not running"
            )

        operation["status"] = OperationStatus.PAUSED
        operation["pause_time"] = datetime.utcnow()

        return OperationResult(
            success=True,
            message="Operation paused",
            data=operation
        )

    async def resume_operation(self, operation_id: str) -> OperationResult:
        """Resume a paused operation"""
        if operation_id not in self._operations:
            return OperationResult(
                success=False,
                message=f"Operation {operation_id} not found"
            )

        operation = self._operations[operation_id]
        if operation["status"] != OperationStatus.PAUSED:
            return OperationResult(
                success=False,
                message=f"Operation {operation_id} is not paused"
            )

        operation["status"] = OperationStatus.RUNNING
        operation["resume_time"] = datetime.utcnow()

        return OperationResult(
            success=True,
            message="Operation resumed",
            data=operation
        )

    async def cancel_operation(self, operation_id: str) -> OperationResult:
        """Cancel an operation"""
        return await self.complete_operation(
            operation_id,
            status=OperationStatus.CANCELLED
        )

    async def retry_operation(self, operation_id: str) -> OperationResult:
        """Retry a failed operation"""
        if operation_id not in self._operations:
            return OperationResult(
                success=False,
                message=f"Operation {operation_id} not found"
            )

        operation = self._operations[operation_id]
        if operation["retry_count"] >= self.max_retries:
            return OperationResult(
                success=False,
                message="Maximum retry attempts exceeded"
            )

        operation["retry_count"] += 1
        operation["status"] = OperationStatus.RUNNING
        operation["retry_time"] = datetime.utcnow()

        return OperationResult(
            success=True,
            message=f"Operation retry attempt {operation['retry_count']}/{self.max_retries}",
            data=operation
        )

    def get_operation_status(self, operation_id: str) -> OperationResult:
        """Get current status of an operation"""
        if operation_id not in self._operations:
            return OperationResult(
                success=False,
                message=f"Operation {operation_id} not found"
            )

        return OperationResult(
            success=True,
            message="Operation status retrieved",
            data=self._operations[operation_id]
        )

    def get_active_operations(self, operation_type: Optional[str] = None) -> Dict[str, Any]:
        """Get all active operations, optionally filtered by type"""
        if operation_type:
            return {
                op_id: self._operations[op_id]
                for op_id in self._active_operations[operation_type]
            }
        
        active_ops = {}
        for op_type in self._active_operations:
            active_ops.update(self.get_active_operations(op_type))
        return active_ops

    def get_statistics(
        self,
        operation_type: Optional[str] = None,
        time_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Get operation statistics"""
        stats = {
            "total_operations": 0,
            "active_operations": 0,
            "completed_operations": 0,
            "failed_operations": 0,
            "average_duration": timedelta(0),
            "success_rate": 0.0,
            "by_type": {}
        }

        operations = self._operations.values()
        if operation_type:
            operations = [op for op in operations if op["type"] == operation_type]
        if time_range:
            start_time, end_time = time_range
            operations = [
                op for op in operations
                if start_time <= op["start_time"] <= end_time
            ]

        if not operations:
            return stats

        # Calculate statistics
        total_duration = timedelta(0)
        completed_ops = 0

        for op in operations:
            stats["total_operations"] += 1
            
            if op["status"] == OperationStatus.RUNNING:
                stats["active_operations"] += 1
            elif op["status"] == OperationStatus.COMPLETED:
                stats["completed_operations"] += 1
                completed_ops += 1
                if "end_time" in op:
                    total_duration += op["end_time"] - op["start_time"]
            elif op["status"] == OperationStatus.FAILED:
                stats["failed_operations"] += 1

            # Update type-specific stats
            op_type = op["type"]
            if op_type not in stats["by_type"]:
                stats["by_type"][op_type] = {
                    "total": 0,
                    "active": 0,
                    "completed": 0,
                    "failed": 0
                }
            
            stats["by_type"][op_type]["total"] += 1
            if op["status"] == OperationStatus.RUNNING:
                stats["by_type"][op_type]["active"] += 1
            elif op["status"] == OperationStatus.COMPLETED:
                stats["by_type"][op_type]["completed"] += 1
            elif op["status"] == OperationStatus.FAILED:
                stats["by_type"][op_type]["failed"] += 1

        # Calculate averages and rates
        if completed_ops > 0:
            stats["average_duration"] = total_duration / completed_ops
            stats["success_rate"] = (stats["completed_operations"] / 
                                   stats["total_operations"]) * 100

        return stats

    async def cleanup_old_operations(self, hours: int = 24):
        """Clean up completed operations older than specified hours"""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(hours=hours)

        # Identify operations to remove
        to_remove = []
        for op_id, operation in self._operations.items():
            if (operation["status"] in [OperationStatus.COMPLETED, 
                                      OperationStatus.FAILED,
                                      OperationStatus.CANCELLED] and
                operation["end_time"] < cutoff_time):
                to_remove.append(op_id)

        # Remove operations
        for op_id in to_remove:
            operation = self._operations[op_id]
            del self._operations[op_id]
            if op_id in self._active_operations[operation["type"]]:
                self._active_operations[operation["type"]].remove(op_id)

        return OperationResult(
            success=True,
            message=f"Cleaned up {len(to_remove)} old operations",
            data={"removed_count": len(to_remove)}
        )

    async def _can_start_operation(self, operation_type: str) -> bool:
        """Check if a new operation can be started"""
        current_count = len(self._active_operations[operation_type])
        
        if operation_type == OperationType.DOWNLOAD:
            return current_count < self.max_concurrent_downloads
        elif operation_type == OperationType.UPLOAD:
            return current_count < self.max_concurrent_uploads
        
        return True
