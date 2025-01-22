import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Telegram Configuration
    API_IDS = os.getenv('TELEGRAM_API_IDS', '').split(',')
    API_HASHES = os.getenv('TELEGRAM_API_HASHES', '').split(',')
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # Path Configuration
    BASE_DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
 # Add to config.py
API_CREDENTIALS = [
    {"api_id": "YOUR_API_ID_1", "api_hash": "YOUR_API_HASH_1"},
    {"api_id": "YOUR_API_ID_2", "api_hash": "YOUR_API_HASH_2"},
    # Add more API credentials as needed
]

MAX_CONCURRENT_DOWNLOADS = 3
CHUNK_SIZE = 8192
MAX_RETRIES = 3
MIN_REQUEST_INTERVAL = 0.05   
    
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
