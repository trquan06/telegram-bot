# utils/state_manager.py
import asyncio
from typing import List, Set
from dataclasses import dataclass, field

@dataclass
class DownloadTask:
    url: str
    status: str
    progress: float = 0.0
    error: str = None

class StateManager:
    def __init__(self, max_concurrent_downloads: int):
        self.downloading: bool = False
        self.failed_files: List[str] = []
        self.error_messages: Set[str] = set()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent_downloads)
        self.active_downloads: dict = {}
        
    @property
    def lock(self) -> asyncio.Lock:
        return self._lock
        
    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore
    
    def add_download(self, url: str) -> None:
        self.active_downloads[url] = DownloadTask(url=url, status="pending")
    
    def update_download_progress(self, url: str, progress: float) -> None:
        if url in self.active_downloads:
            self.active_downloads[url].progress = progress
    
    def complete_download(self, url: str) -> None:
        if url in self.active_downloads:
            self.active_downloads[url].status = "completed"
    
    def fail_download(self, url: str, error: str) -> None:
        if url in self.active_downloads:
            self.active_downloads[url].status = "failed"
            self.active_downloads[url].error = error
            self.failed_files.append(url)
    
    def get_active_downloads(self) -> List[DownloadTask]:
        return list(self.active_downloads.values())
