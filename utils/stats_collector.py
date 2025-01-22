# utils/stats_collector.py
from typing import Dict, Any
import psutil
import humanize
from datetime import datetime, timedelta
from .base import BaseUtil, OperationResult

class StatsCollector(BaseUtil):
    def __init__(self, config):
        super().__init__(config)
        self.stats_history = []
        self.max_history_size = config.STATS_HISTORY_SIZE

    async def collect_system_stats(self) -> OperationResult:
        """Collect system statistics"""
        try:
            stats = {
                'timestamp': datetime.utcnow(),
                'system': self._get_system_stats(),
                'memory': self._get_memory_stats(),
                'disk': self._get_disk_stats(),
                'network': self._get_network_stats()
            }
            
            self.stats_history.append(stats)
            if len(self.stats_history) > self.max_history_size:
                self.stats_history.pop(0)
            
            return OperationResult(
                success=True,
                message="Statistics collected successfully",
                data=stats
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting stats: {str(e)}")
            return OperationResult(
                success=False,
                message=f"Failed to collect stats: {str(e)}",
                error=e
            )

    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        return {
            'cpu_percent': cpu_percent,
            'cpu_count': psutil.cpu_count(),
            'boot_time': datetime.fromtimestamp(psutil.boot_time())
        }

    def _get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        memory = psutil.virtual_memory()
        return {
            'total': humanize.naturalsize(memory.total),
            'available': humanize.naturalsize(memory.available),
            'percent': memory.percent,
            'used': humanize.naturalsize(memory.used)
        }

    def _get_disk_stats(self) -> Dict[str, Any]:
        """Get disk statistics"""
        disk = psutil.disk_usage(self.config.BASE_DOWNLOAD_FOLDER)
        return {
            'total': humanize.naturalsize(disk.total),
            'used': humanize.naturalsize(disk.used),
            'free': humanize.naturalsize(disk.free),
            'percent': disk.percent
        }

    def _get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': humanize.naturalsize(net_io.bytes_sent),
            'bytes_recv': humanize.naturalsize(net_io.bytes_recv),
            'packets
