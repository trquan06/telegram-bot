# utils/download_manager.py
import asyncio
import os
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import humanize
from .base import BaseUtil, OperationResult

class DownloadManager(BaseUtil):
    def __init__(self, config):
        super().__init__(config)
        self.active_downloads: Dict[str, Dict[str, Any]] = {}
        self.download_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
        self.stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes_downloaded': 0
        }

    async def start_download(
        self,
        url: str,
        file_path: str,
        message=None
    ) -> OperationResult:
        """Start a new download with progress tracking"""
        download_id = f"{url}_{datetime.utcnow().timestamp()}"
        
        if url in self.active_downloads:
            return OperationResult(
                success=False,
                message="Download already in progress",
                data={'download_id': download_id}
            )

        async with self.download_semaphore:
            try:
                download_info = {
                    'url': url,
                    'file_path': file_path,
                    'start_time': datetime.utcnow(),
                    'progress': 0,
                    'total_size': 0,
                    'downloaded_size': 0,
                    'speed': 0,
                    'status': 'downloading',
                    'message': message
                }
                
                self.active_downloads[download_id] = download_info
                self.stats['total_downloads'] += 1

                result = await self._perform_download(download_id)
                
                if result.success:
                    self.stats['successful_downloads'] += 1
                else:
                    self.stats['failed_downloads'] += 1

                return result

            except Exception as e:
                self.logger.error(f"Download error for {url}: {str(e)}")
                self.stats['failed_downloads'] += 1
                return OperationResult(
                    success=False,
                    message=f"Download failed: {str(e)}",
                    error=e
                )
            finally:
                if download_id in self.active_downloads:
                    del self.active_downloads[download_id]

    async def _perform_download(self, download_id: str) -> OperationResult:
        """Perform the actual download with progress tracking"""
        download_info = self.active_downloads[download_id]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_info['url']) as response:
                    if not response.ok:
                        return OperationResult(
                            success=False,
                            message=f"Download failed with status {response.status}"
                        )

                    download_info['total_size'] = int(
                        response.headers.get('content-length', 0)
                    )
                    
                    with open(download_info['file_path'], 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                                
                            f.write(chunk)
                            await self._update_progress(download_id, len(chunk))

            return OperationResult(
                success=True,
                message="Download completed successfully",
                data={
                    'file_path': download_info['file_path'],
                    'total_size': download_info['total_size'],
                    'download_time': (
                        datetime.utcnow() - download_info['start_time']
                    ).total_seconds()
                }
            )

        except Exception as e:
            self.logger.error(f"Download error: {str(e)}")
            return OperationResult(
                success=False,
                message=f"Download failed: {str(e)}",
                error=e
            )

    async def _update_progress(self, download_id: str, chunk_size: int):
        """Update download progress and speed"""
        download_info = self.active_downloads[download_id]
        download_info['downloaded_size'] += chunk_size
        self.stats['total_bytes_downloaded'] += chunk_size
        
        # Calculate progress percentage
        if download_info['total_size'] > 0:
            download_info['progress'] = (
                download_info['downloaded_size'] / download_info['total_size']
            ) * 100
        
        # Calculate speed
        elapsed_time = (
            datetime.utcnow() - download_info['start_time']
        ).total_seconds()
        if elapsed_time > 0:
            download_info['speed'] = download_info['downloaded_size'] / elapsed_time
        
        # Update progress message if available
        if download_info['message']:
            await self._update_progress_message(download_info)

    async def _update_progress_message(self, download_info: Dict):
        """Update progress message with current status"""
        try:
            progress_text = (
                f"📥 Downloading: {download_info['progress']:.1f}%\n"
                f"💨 Speed: {humanize.naturalsize(download_info['speed'])}/s\n"
                f"📦 Size: {humanize.naturalsize(download_info['downloaded_size'])}/"
                f"{humanize.naturalsize(download_info['total_size'])}\n"
                f"⏱ Elapsed: {timedelta(seconds=int((datetime.utcnow() - download_info['start_time']).total_seconds()))}"
            )
            
            await download_info['message'].edit_text(progress_text)
        except Exception as e:
            self.logger.error(f"Error updating progress message: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get download statistics"""
        return {
            **self.stats,
            'active_downloads': len(self.active_downloads),
            'total_bytes_readable': humanize.naturalsize(
                self.stats['total_bytes_downloaded']
            )
        }
