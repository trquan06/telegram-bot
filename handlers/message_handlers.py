# handlers/message_handler.py
import os
import aiohttp
import mimetypes
import uuid
from typing import Optional, Tuple
from datetime import datetime
from .base_handler import BaseHandler, OperationResult
from utils.file_manager import FileManager

class MessageHandler(BaseHandler):
    def __init__(self, config, error_handler, state_manager):
        super().__init__(config, error_handler)
        self.state_manager = state_manager
        self.file_manager = FileManager(config.BASE_DOWNLOAD_FOLDER)
        self.supported_types = {
            'photo': {'mime_types': ['image/jpeg', 'image/png', 'image/gif'],
                     'max_size': 20 * 1024 * 1024},  # 20MB
            'video': {'mime_types': ['video/mp4', 'video/quicktime'],
                     'max_size': 2 * 1024 * 1024 * 1024},  # 2GB
            'document': {'mime_types': None,  # Accept all
                        'max_size': 2 * 1024 * 1024 * 1024}  # 2GB
        }

    async def process_message(self, client, message) -> OperationResult:
        """Process incoming message and handle media/URLs"""
        try:
            if not self.state_manager.is_downloading():
                return OperationResult(
                    success=False,
                    message="Download mode is not active. Use /download to start."
                )

            if message.text and message.text.startswith("http"):
                return await self._handle_url(message, message.text.strip())

            if message.media:
                return await self._handle_media(message)

            return OperationResult(
                success=False,
                message="Message contains no media or valid URL."
            )

        except Exception as e:
            await self.error_handler.handle_error(e, "message_processing")
            return OperationResult(
                success=False,
                message=f"Error processing message: {str(e)}",
                error=e
            )

    async def _handle_url(self, message, url: str) -> OperationResult:
        """Handle URL downloads with validation and progress tracking"""
        try:
            # Validate URL and get metadata
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True) as response:
                    if not response.ok:
                        return OperationResult(
                            success=False,
                            message=f"URL returned status code: {response.status}"
                        )

                    content_type = response.headers.get('content-type', '')
                    content_length = int(response.headers.get('content-length', 0))

                    # Validate content type and size
                    if not await self._validate_file(content_type, content_length):
                        return OperationResult(
                            success=False,
                            message="File type or size not supported"
                        )

            # Start download with progress tracking
            status_message = await message.reply("⏳ Starting download...")
            download_result = await self.file_manager.download_url(
                url,
                progress_callback=lambda p: self._update_progress(status_message, p)
            )

            if download_result.success:
                await status_message.edit_text("✅ Download completed successfully!")
            else:
                await status_message.edit_text(f"❌ Download failed: {download_result.message}")

            return download_result

        except Exception as e:
            await self.error_handler.handle_error(e, "url_download")
            return OperationResult(
                success=False,
                message=f"Download failed: {str(e)}",
                error=e
            )

    async def _handle_media(self, message) -> OperationResult:
        """Handle media file downloads with type validation and progress tracking"""
        try:
            media_type, file_id = await self._get_media_info(message)
            if not media_type:
                return OperationResult(
                    success=False,
                    message="Unsupported media type"
                )

            status_message = await message.reply("⏳ Processing media...")
            
            # Generate unique filename
            ext = mimetypes.guess_extension(message.media.mime_type) or '.unknown'
            filename = f"{uuid.uuid4()}{ext}"
            
            # Download with progress tracking
            progress = {"current": 0, "total": message.media.file_size}
            
            def progress_callback(current, total):
                progress["current"] = current
                progress["total"] = total
                self._update_progress(status_message, progress)

            file_path = os.path.join(self.config.BASE_DOWNLOAD_FOLDER, filename)
            
            try:
                await message.download(
                    file_name=file_path,
                    progress=progress_callback
                )
                
                await status_message.edit_text("✅ Media downloaded successfully!")
                return OperationResult(
                    success=True,
                    message="Media downloaded successfully",
                    data={"file_path": file_path}
                )
                
            except Exception as e:
                await self.error_handler.handle_error(e, "media_download")
                return OperationResult(
                    success=False,
                    message=f"Failed to download media: {str(e)}",
                    error=e
                )

        except Exception as e:
            await self.error_handler.handle_error(e, "media_processing")
            return OperationResult(
                success=False,
                message=f"Error processing media: {str(e)}",
                error=e
            )

    async def _get_media_info(self, message) -> Tuple[Optional[str], Optional[str]]:
        """Extract media type and file ID from message"""
        if message.photo:
            return 'photo', message.photo.file_id
        elif message.video:
            return 'video', message.video.file_id
        elif message.document:
            return 'document', message.document.file_id
        return None, None

    async def _validate_file(self, mime_type: str, file_size: int) -> bool:
        """Validate file type and size against supported types"""
        for media_type, constraints in self.supported_types.items():
            if (constraints['mime_types'] is None or 
                mime_type in constraints['mime_types']) and \
               file_size <= constraints['max_size']:
                return True
        return False

    async def _update_progress(self, message, progress: dict):
        """Update download progress message"""
        try:
            percentage = (progress["current"] / progress["total"]) * 100
            progress_text = (
                f"📥 Downloading: {percentage:.1f}%\n"
                f"💾 Size: {self.format_size(progress['current'])}/{self.format_size(progress['total'])}"
            )
            await message.edit_text(progress_text)
        except Exception as e:
            self.logger.error(f"Error updating progress: {str(e)}")
