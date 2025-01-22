import os
import subprocess
import asyncio
from datetime import datetime

class UploadHandler:
    def __init__(self, config):
        self.config = config
        self.failed_uploads_log = os.path.join(config.BASE_DOWNLOAD_FOLDER, "failed_uploads.txt")
        self.retry_log = os.path.join(config.BASE_DOWNLOAD_FOLDER, "retry_upload_log.txt")
        self.uploading = False

    async def upload_to_google_photos(self, message):
        """Upload files to Google Photos"""
        try:
            if self.uploading:
                await message.reply("An upload operation is already in progress.")
                return

            self.uploading = True
            status_message = await message.reply("Starting file sync to Google Photos...")

            try:
                # Clear previous failed uploads log
                if os.path.exists(self.failed_uploads_log):
                    os.remove(self.failed_uploads_log)

                result = subprocess.run([
                    "rclone", "copy", self.config.BASE_DOWNLOAD_FOLDER,
                    "GG PHOTO:album/ONLYFAN",
                    "--transfers=32", "--drive-chunk-size=128M", "--tpslimit=20",
                    "--track-renames", "--track-errors"
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    await status_message.edit_text("✅ Successfully synced all files to Google Photos!")
                else:
                    # Parse error output to identify failed files
                    failed_files = []
                    for line in result.stderr.splitlines():
                        if "Failed to copy:" in line:
                            file_path = line.split("Failed to copy:")[1].strip()
                            failed_files.append(file_path)

                    # Save failed files to log
                    if failed_files:
                        with open(self.failed_uploads_log, 'w') as f:
                            for file_path in failed_files:
                                f.write(f"{file_path}\n")

                    await status_message.edit_text(
                        f"⚠️ Upload completed with errors:\n"
                        f"❌ {len(failed_files)} files failed to upload\n"
                        f"Use /retry_upload to retry failed uploads\n"
                    )

            except Exception as e:
                await message.reply(f"Upload error: {str(e)}")
            finally:
                self.uploading = False

        except Exception as e:
            await message.reply(f"Error in upload process: {str(e)}")
            self.uploading = False

    async def retry_upload(self, message):
        """Retry failed uploads"""
        try:
            if not os.path.exists(self.failed_uploads_log):
                await message.reply("No failed uploads to retry.")
                return

            with open(self.failed_uploads_log, 'r') as f:
                failed_files = f.read().splitlines()

            if not failed_files:
                await message.reply("No failed uploads to retry.")
                return

            status_message = await message.reply(
                f"🔄 Found {len(failed_files)} failed uploads. Starting retry..."
            )

            success_count = 0
            new_failed_files = []

            for file_path in failed_files:
                if os.path.exists(file_path):
                    try:
                        result = subprocess.run([
                            "rclone", "copy", file_path,
                            "GG PHOTO:album/ONLYFAN",
                            "--transfers=1", "--drive-chunk-size=128M",
                            "--tpslimit=20"
                        ], capture_output=True, text=True)

                        if result.returncode == 0:
                            success_count += 1
                        else:
                            new_failed_files.append(file_path)
                    except Exception as e:
                        new_failed_files.append(file_path)
                        with open(self.retry_log, 'a') as log:
                            log.write(f"Error uploading {file_path}: {str(e)}\n")

            # Update failed uploads log
            with open(self.failed_uploads_log, 'w') as f:
                for file_path in new_failed_files:
                    f.write(f"{file_path}\n")

            status_text = (
                f"📤 Retry Upload Results:\n"
                f"✅ Successfully uploaded: {success_count}\n"
                f"❌ Still failed: {len(new_failed_files)}\n\n"
            )

            if new_failed_files:
                status_text += "Use /retry_upload again to retry remaining files."
            else:
                status_text += "All files uploaded successfully!"
                # Clean up logs if everything succeeded
                if os.path.exists(self.retry_log):
                    os.remove(self.retry_log)
                os.remove(self.failed_uploads_log)

            await status_message.edit_text(status_text)

        except Exception as e:
            await message.reply(f"❌ Error in retry upload process: {str(e)}")
