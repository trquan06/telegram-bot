# utils/monitor.py
import psutil
import os
from datetime import datetime

class SystemMonitor:
    def __init__(self):
        self.download_stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_size': 0
        }
        self.api_stats = {
            'requests_made': 0,
            'rate_limits_hit': 0
        }

    def get_system_metrics(self):
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'download_stats': self.download_stats,
            'api_stats': self.api_stats
        }

    def update_download_stats(self, success=True, size=0):
        self.download_stats['total_downloads'] += 1
        if success:
            self.download_stats['successful_downloads'] += 1
        else:
            self.download_stats['failed_downloads'] += 1
        self.download_stats['total_size'] += size

    def update_api_stats(self, rate_limited=False):
        self.api_stats['requests_made'] += 1
        if rate_limited:
            self.api_stats['rate_limits_hit'] += 1

system_monitor = SystemMonitor()
