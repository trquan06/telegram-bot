import psutil
import humanize

async def get_system_status(base_download_folder, max_concurrent_downloads, download_semaphore, failed_files, flood_handler):
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(base_download_folder)
    
    # Get network speeds
    net_io_counter = psutil.net_io_counters()
    
    # Calculate active downloads
    active_count = max_concurrent_downloads - download_semaphore._value
    
    status = {
        "system": {
            "cpu": f"{cpu_percent}%",
            "memory_percent": f"{memory.percent}%",
            "memory_used": humanize.naturalsize(memory.used),
            "memory_total": humanize.naturalsize(memory.total),
            "disk_free": humanize.naturalsize(disk.free),
            "disk_total": humanize.naturalsize(disk.total),
            "disk_percent": f"{disk.percent}%"
        },
        "network": {
            "bytes_sent": humanize.naturalsize(net_io_counter.bytes_sent),
            "bytes_recv": humanize.naturalsize(net_io_counter.bytes_recv)
        },
        "downloads": {
            "active": active_count,
            "failed": len(failed_files),
            "flood_wait": flood_handler.is_waiting()
        }
    }
    
    return status
