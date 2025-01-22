# utils/api_manager.py
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import random

@dataclass
class APICredentials:
    api_id: str
    api_hash: str
    rate_limit: int = 20
    used_count: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)

class APIManager:
    def __init__(self, api_credentials: List[Dict[str, str]]):
        self.logger = logging.getLogger('APIManager')
        self.credentials = [
            APICredentials(cred['api_id'], cred['api_hash'])
            for cred in api_credentials
        ]
        self.current_index = 0
        self.last_request_time = datetime.utcnow()
        self.min_request_interval = 0.05  # 50ms between requests
        self.rotation_threshold = 0.8  # Rotate APIs at 80% usage

    async def get_next_credentials(self) -> APICredentials:
        """Get the next available API credentials using smart rotation"""
        current_creds = self.credentials[self.current_index]
        
        # Check if we need to reset the counter
        if datetime.utcnow() - current_creds.last_reset > timedelta(hours=1):
            current_creds.used_count = 0
            current_creds.last_reset = datetime.utcnow()

        # If current credentials are approaching limit, rotate
        if current_creds.used_count >= (current_creds.rate_limit * self.rotation_threshold):
            self.rotate_credentials()
            
        return self.credentials[self.current_index]

    def rotate_credentials(self):
        """Rotate to next API credentials"""
        self.current_index = (self.current_index + 1) % len(self.credentials)
        self.logger.info(f"Rotated to API credentials index: {self.current_index}")

    async def make_request(self, request_func, *args, **kwargs):
        """Make an API request with rate limiting and automatic rotation"""
        while True:
            try:
                # Ensure minimum interval between requests
                time_since_last = (datetime.utcnow() - self.last_request_time).total_seconds()
                if time_since_last < self.min_request_interval:
                    await asyncio.sleep(self.min_request_interval - time_since_last)

                credentials = await self.get_next_credentials()
                credentials.used_count += 1
                self.last_request_time = datetime.utcnow()

                # Make the actual request
                result = await request_func(*args, **kwargs)
                return result

            except Exception as e:
                if "FloodWait" in str(e):
                    wait_time = int(str(e).split()[1])
                    self.logger.warning(f"FloodWait detected, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                
                if "Too Many Requests" in str(e):
                    self.rotate_credentials()
                    continue
                
                raise e

    async def handle_batch_requests(self, requests: List[dict], max_concurrent: int = 3):
        """Handle multiple requests concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def wrapped_request(request):
            async with semaphore:
                return await self.make_request(**request)
        
        return await asyncio.gather(
            *[wrapped_request(req) for req in requests],
            return_exceptions=True
        )

class DownloadOptimizer:
    def __init__(self, max_concurrent: int = 3, chunk_size: int = 8192):
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        self.active_downloads = 0
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger('DownloadOptimizer')

    async def optimize_chunk_size(self, file_size: int) -> int:
        """Dynamically optimize chunk size based on file size"""
        if file_size > 100 * 1024 * 1024:  # > 100MB
            return 32768
        elif file_size > 10 * 1024 * 1024:  # > 10MB
            return 16384
        return self.chunk_size

    async def download_file(self, client, message, file_id: str, file_size: int):
        """Optimized file download with dynamic chunking and concurrent handling"""
        async with self.semaphore:
            self.active_downloads += 1
            try:
                chunk_size = await self.optimize_chunk_size(file_size)
                self.logger.info(f"Starting download with chunk size: {chunk_size}")
                
                # Download implementation here
                # This is where you'd implement your actual download logic
                
                self.logger.info(f"Download completed successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Download failed: {str(e)}")
                raise
            finally:
                self.active_downloads -= 1
