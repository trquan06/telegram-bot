from datetime import datetime, timedelta

class FloodWaitHandler:
    def __init__(self):
        self.is_active = False
        self.wait_until = None

    async def handle_flood_wait(self, seconds):
        self.is_active = True
        self.wait_until = datetime.now() + timedelta(seconds=seconds)
        wait_minutes = seconds // 60
        wait_seconds = seconds % 60
        
        message = f"⚠️ FloodWait detected: Waiting for "
        if wait_minutes > 0:
            message += f"{wait_minutes} minutes and "
        message += f"{wait_seconds} seconds"
        
        return message

    def is_waiting(self):
        if not self.is_active:
            return False
        if datetime.now() >= self.wait_until:
            self.is_active = False
            return False
        return True
