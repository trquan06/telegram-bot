# Create a new file: state.py
class BotState:
    def __init__(self):
        self.downloading = False
        self.failed_files = []
        self.error_messages = set()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_DOWNLOADS)

    @property
    def lock(self):
        return self._lock

    @property
    def semaphore(self):
        return self._semaphore
