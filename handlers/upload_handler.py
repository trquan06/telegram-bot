# handlers/upload_handler.py
import os
import asyncio
import subprocess
from typing import List
from datetime import datetime
from .base_handler import BaseHandler, OperationResult

class UploadHandler(BaseHandler):
    def __init__(self, config, error_handler, state_manager):
        super().__init__(config, error_handler)
        self.state_manager = state_manager
        self.failed_uploads_file = os.path.join(config.BASE_DOWNLOAD_FOLDER, "failed_uploads.txt")
        self.retry_log_file = os.path.join(config.BASE_DOWNLOAD_FOLDER, "retry_upload_log.txt")

    async def upload_to_google_photos(self, message) -> OperationResult:
        """Upload files to Google Photos with improved error handling and progress tracking"""
        if self.state_manager.is_uploading():
            return OperationResult(
                success=False,
                message="An upload operation is already in progress."
            )

        try:
            self.state_manager.start_upload()
            status_message = await message.reply("🚀 Starting file sync to Google Photos...")
            
            # Clean up previous logs
            self._cleanup_logs()

            # Prepare upload command
            command = self._prepare_upload_command(self.config.BASE_DOWNLOAD_FOLDER)
            
            # Execute upload
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Monitor progress
            failed_files = []
            async for line in process.stderr:
                line = line.decode().strip()
                if "Transferred:" in line:
                    await self._update_upload_progress(status_message, line)
                elif "Failed to copy:" in line:
                    failed_files.append(line.split("Failed to copy:")[1].strip())

            await process.wait()
            
            # Handle results
            if process.returncode == 0 and not failed_files:
                await status_message.edit_text("✅ Successfully synced all files to Google Photos!")
                return OperationResult(success=True, message="Upload completed successfully")
            
            # Handle partial success
            await self._handle_failed_uploads(failed_files)
            
            status_text = (
                f"⚠️ Upload completed with issues:\n"
                f"❌ {len(failed_files)} files failed to upload\n"
                f"Use /retry_upload to retry failed uploads"
            )
            await status_message.edit_text(status_text)
            
            return OperationResult(
                success=False,
                message="Upload completed with errors",
                data={"failed_files": failed_files}
            )

        except Exception as e:
            await self.error_handler.handle_error(e, "upload_to_google_photos")
            return OperationResult(
                success=False,
                message=f"Upload error: {str(e)}",
                error=e
            )
        finally:
            self.state_manager.end_upload()

    async def retry_upload(self, message) -> OperationResult:
        """Retry failed uploads with improved error handling and progress tracking"""
        try:
            failed_files = await self._load_failed_files()
            if not failed_files:
                return OperationResult(
                    success=False,
                    message="No failed uploads to retry."
                )

            status_message = await message.reply(
                f"🔄 Retrying {len(failed_files)} failed uploads..."
            )

            results = await self._process_retry_uploads(failed_files, status_message)
            
            # Update status and clean up if needed
            status_text = self._format_retry_results(results)
            await status_message.edit_text(status_text)

            if not results['new_failed_files']:
                self._cleanup_logs()
                
            return OperationResult(
                success=len(results['new_failed_files']) == 0,
                message="Retry completed",
                data=results
            )

        except Exception as e:
            await self.error_handler.handle_error(e, "retry_upload")
            return OperationResult(
                success=False,
                message=f"Retry error: {str(e)}",
                error=e
            )

    def _prepare_upload_command(self, source_path: str) -> List[str]:
        """Prepare rclone command with optimized parameters"""
        return [
            "rclone", "copy",
            source_path,
            "GG PHOTO:album/ONLYFAN",
            "--transfers=32",
            "--drive-chunk-size=128M",
            "--tpslimit=20",
            "--track-renames",
            "--track-errors",
            "-P"  # Enable progress monitoring
        ]

    async def _update_upload_progress(self, message, progress_line: str):
        """Update upload progress message"""
        try:
            # Extract progress information from rclone output
            # Example: "Transferred: 1.234 GiB / 5.678 GiB, 45%, 2 files"
            stats = progress_line.split(",")
            progress_text = (
                f"📤 Upload Progress:\n"
                f"{stats[0]}\n"  # Transferred amount
                f"Speed: {stats[1] if len(stats) > 1 else 'N/A'}\n"
                f"Files: {stats[2] if len(stats) > 2 else 'N/A'}"
            )
            await message.edit_text(progress_text)
        except Exception as e:
            self.logger.error(f"Error updating upload progress: {str(e)}")

    def _cleanup_logs(self):
        """Clean up log files"""
        for log_file in [self.failed_uploads_file, self.retry_log_file]:
            if os.path.exists(log_file):
                try:
                    os.remove(log_file)
                except Exception as e:
                    self.logger.error(f"Error cleaning up log file {log_file}: {str(e)}")

    async def _load_failed_files(self) -> List[str]:
        """Load failed files from log"""
        if not os.path.exists(self.failed_uploads_file):
            return []
        
        try:
            with open(self.failed_uploads_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.logger.error(f"Error loading failed files: {str(e)}")
            return []

    async def _process_retry_uploads(self, failed_files: List[str], status_message) -> dict:
        """Process retry uploads with progress tracking"""
        results = {
            'success_count': 0,
            'new_failed_files': []
        }

        for i, file_path in enumerate(failed_files, 1):
            if not os.path.exists(file_path):
                results['new_failed_files'].append(file_path)
                continue

            try:
                await status_message.edit_text(
                    f"🔄 Retrying file {i}/{len(failed_files)}..."
                )

                command = self._prepare_upload_command(file_path)
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE
