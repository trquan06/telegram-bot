from pyrogram import filters
import os
import subprocess
from datetime import datetime

async def start_command(client, message):
    await message.reply(
        "Welcome! Available commands:\n"
        "/download - Start download mode\n"
        "/stop - Stop all operations\n"
        "/upload - Sync files to Google Photos\n"
        "/retry_download - Retry failed downloads\n"
        "/status - Check system status\n"
        "You can also send a URL to download directly"
    )

async def download_command(client, message, download_lock, downloading, download_from_url):
    try:
        # Check if command includes URL
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            url = args[1].strip()
            if url.startswith("http"):
                await download_from_url(message, url)
                return
            else:
                await message.reply("Invalid URL. Please ensure you enter a valid URL.")
                return

        # Enter download mode
        async with download_lock:
            if downloading:
                await message.reply("A download task is already running.")
                return
            downloading = True

        await message.reply("Download mode started. Forward messages with media to download.")
    except Exception as e:
        await message.reply(f"Error starting download mode: {str(e)}")

async def stop_command(client, message, download_lock, downloading, uploading):
    try:
        async with download_lock:
            downloading = False
            uploading = False
            
        await message.reply("✅ All operations stopped:\n"
                          "- Downloads canceled\n"
                          "- Uploads canceled\n"
                          "- Retry operations canceled")
    except Exception as e:
        await message.reply(f"Error stopping operations: {str(e)}")

async def upload_command(client, message, uploading, base_download_folder):
    try:
        if uploading:
            await message.reply("An upload operation is already in progress.")
            return

        uploading = True
        status_message = await message.reply("Starting file sync to Google Photos...")

        try:
            album_name = "ONLYFAN"
            log_file_path = os.path.join(base_download_folder, "error_log.txt")
            
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                result = subprocess.run(
                    [
                        "rclone", "copy", base_download_folder, f"GG PHOTO:album/{album_name}",
                        "--transfers=32", "--drive-chunk-size=128M", "--tpslimit=20", "-P"
                    ],
                    stdout=log_file, stderr=log_file, text=True, encoding="utf-8"
                )

            if result.returncode == 0:
                await status_message.edit_text("✅ Successfully synced all files to Google Photos!")
            else:
                await status_message.edit_text(f"❌ Sync error, details in: {log_file_path}")

        except Exception as e:
            await message.reply(f"Upload error: {str(e)}")
        finally:
            uploading = False

    except Exception as e:
        await message.reply(f"Error in upload process: {str(e)}")
        uploading = False

async def status_command(client, message, system_monitor, config, download_semaphore, failed_files, flood_handler):
    try:
        status = await system_monitor.get_system_status(
            config.BASE_DOWNLOAD_FOLDER,
            config.MAX_CONCURRENT_DOWNLOADS,
            download_semaphore,
            failed_files,
            flood_handler
        )
        
        status_message = (
            "📊 System Status\n\n"
            f"💻 CPU Usage: {status['system']['cpu']}\n"
            f"🧮 RAM Usage: {status['system']['memory_percent']}\n"
            f"💾 Disk Space: {status['system']['disk_free']} free of {status['system']['disk_total']}\n\n"
            f"🌐 Network Stats:\n"
            f"⬆️ Sent: {status['network']['bytes_sent']}\n"
            f"⬇️ Received: {status['network']['bytes_recv']}\n\n"
            f"📥 Downloads:\n"
            f"▶️ Active: {status['downloads']['active']}\n"
            f"❌ Failed: {status['downloads']['failed']}\n"
            f"⏳ FloodWait: {'Yes' if status['downloads']['flood_wait'] else 'No'}"
        )
        
        await message.reply(status_message)

    # Add to your command handlers:

@app.on_message(filters.command("systemstatus"))
@monitor_performance
async def system_status(client, message):
    try:
        # Get system metrics
        metrics = system_monitor.get_system_metrics()
        
        # Format status message
        status_text = (
            "📊 System Status:\n"
            f"CPU Usage: {metrics['cpu_percent']}%\n"
            f"Memory Usage: {metrics['memory_percent']}%\n"
            f"Disk Usage: {metrics['disk_usage']}%\n\n"
            "📥 Download Statistics:\n"
            f"Total Downloads: {metrics['download_stats']['total_downloads']}\n"
            f"Successful: {metrics['download_stats']['successful_downloads']}\n"
            f"Failed: {metrics['download_stats']['failed_downloads']}\n"
            f"Total Size: {metrics['download_stats']['total_size'] / (1024*1024):.2f} MB\n\n"
            "🔄 API Statistics:\n"
            f"Total Requests: {metrics['api_stats']['requests_made']}\n"
            f"Rate Limits Hit: {metrics['api_stats']['rate_limits_hit']}"
        )
        
        await message.reply(status_text)
        bot_logger.log_command(message)
        
    except Exception as e:
        bot_logger.log_error(e, "system_status command")
        await message.reply("Error getting system status. Check logs for details.")
    except Exception as e:
        await message.reply(f"Error getting system status: {str(e)}")
