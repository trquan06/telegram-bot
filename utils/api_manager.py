# utils/api_manager.py
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta
from .base import BaseUtil, OperationResult

class APIManager(BaseUtil):
    def __init__(self, config):
        super().__init__(config)
        self.credentials = self._initialize_credentials(config.API_CREDENTIALS)
        self.current_index = 0
        self.request_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)
        self.last_request_time = datetime.utcnow()

    def _initialize_credentials(self, credentials_config: List[Dict[str, str]]):
        return [{
            'api_id': cred['api_id'],
            'api_hash': cred['api_hash'],
            'rate_limit': cred.get('rate_limit', 20),
            'used_count': 0,
            'last_reset': datetime.utcnow(),
            'error_count': 0
        } for cred in credentials_config]

    async def make_request(self, request_func, *args, **kwargs) -> OperationResult:
        async with self.request_semaphore:
            try:
                credentials = await self._get_next_credentials()
                await self._enforce_rate_limit()
                
                result = await request_func(*args, **kwargs)
                await self._update_request_stats(credentials, success=True)
                
                return OperationResult(
                    success=True,
                    message="Request completed successfully",
                    data=result
                )
                
            except Exception as e:
                await self._handle_request_error(e, credentials)
                return OperationResult(
                    success=False,
                    message=f"Request failed: {str(e)}",
                    error=e
                )

    async def _get_next_credentials(self) -> Dict:
        current_creds = self.credentials[self.current_index]
        
        # Reset counters if needed
        if datetime.utcnow() - current_creds['last_reset'] > timedelta(hours=1):
            current_creds.update({
                'used_count': 0,
                'error_count': 0,
                'last_reset': datetime.utcnow()
            })
        
        # Rotate if approaching limits
        if self._should_rotate_credentials(current_creds):
            self._rotate_credentials()
            current_creds = self.credentials[self.current_index]
            
        return current_creds

    def _should_rotate_credentials(self, credentials: Dict) -> bool:
        return (
            credentials['used_count'] >= credentials['rate_limit'] * 0.8 or
            credentials['error_count'] >= 5
        )

    async def _enforce_rate_limit(self):
        """Ensure minimum interval between requests"""
        min_interval = 0.05  # 50ms
        time_since_last = (datetime.utcnow() - self.last_request_time).total_seconds()
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self.last_request_time = datetime.utcnow()

    async def _update_request_stats(self, credentials: Dict, success: bool):
        """Update request statistics"""
        credentials['used_count'] += 1
        if not success:
            credentials['error_count'] += 1

    async def _handle_request_error(self, error: Exception, credentials: Dict):
        """Handle request errors"""
        error_type = type(error).__name__
        error_msg = str(error)
        
        await self._update_request_stats(credentials, success=False)
        
        if "FloodWait" in error_msg:
            wait_time = int(error_msg.split()[1])
            self.logger.warning(f"FloodWait detected, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            
        elif "Too Many Requests" in error_msg:
            self._rotate_credentials()
            
        self.logger.error(f"Request error: {error_type} - {error_msg}")

    def _rotate_credentials(self):
        """Rotate to next available API credentials"""
        self.current_index = (self.current_index + 1) % len(self.credentials)
        self.logger.info(f"Rotated to API credentials index: {self.current_index}")
