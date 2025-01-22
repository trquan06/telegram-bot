# Add to utils/error_handler.py
class ErrorHandler:
    def __init__(self):
        self.error_messages = set()

    async def handle_error(self, error, context):
        error_message = f"Error: {str(error)}"
        self.error_messages.add(error_message)
        # Log error
        logging.error(f"Error occurred: {error_message}")
        return error_message
