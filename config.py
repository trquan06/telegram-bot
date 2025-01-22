import os

class Config:
    # Telegram Configuration
    API_IDS = ["21164074"]  # List to support multiple API IDs
    API_HASHES = ["9aebf8ac7742705ce930b06a706754fd"]  # List to support multiple API hashes
    BOT_TOKEN = "7878223314:AAGdrEWvu86sVWXCHIDFqqZw6m68mK6q5pY"
    
    # Path Configuration
    BASE_DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
    
    # Performance Settings
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    MAX_CONCURRENT_DOWNLOADS = 10
    
    # Media Types
    SUPPORTED_MEDIA_TYPES = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'],
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
        'archive': ['.zip', '.rar', '.7z']
    }
    
    def __init__(self):
        self.current_api_index = 0
        
    def get_current_api(self):
        return (self.API_IDS[self.current_api_index], 
                self.API_HASHES[self.current_api_index])
    
    def rotate_api(self):
        self.current_api_index = (self.current_api_index + 1) % len(self.API_IDS)
