import logging
import asyncio
import logging
import os
from bot_management import app, LOGS
from pyrogram.handlers import MessageHandler
from pyrogram import filters

logging.basicConfig(level=logging.INFO)

async def main():
    
    await app.start()    
    LOGS.info("BOT STARTED")
    
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
