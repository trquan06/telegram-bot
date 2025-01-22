import os
import aiohttp
import mimetypes
import uuid
import time
from pyrogram import errors

async def handle_message(client, message, downloading, download_from_url):
    try:
        if not downloading:
            return

        if message.text and message.text.startswith("http"):
            url = message.text.strip()
            await download_from_url(message, url)
            return

        if message.photo or message.video or message.document:
            try:
                if message.photo:
                    await download_with_progress(message, "image")
                elif message.video:
                    await download_with_progress(message, "video")
                elif message.document:
                    await download_with_progress(message, "document")
            except Exception as e:
                await message.reply(f"Download error: {str(e)}")
        else:
            await message.reply("Message contains no media or valid URL.")
    except Exception as e:
        await message.reply(f"Error processing message: {str(e)}")
