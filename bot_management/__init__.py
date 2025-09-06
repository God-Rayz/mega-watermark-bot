from pyrogram import Client
from pyrogram.enums import ParseMode
from convopyro import Conversation
import logging
import os
import configparser
from logging.handlers import TimedRotatingFileHandler

def logging_init():
    if not os.path.exists('bot_management/logs'):
        os.makedirs('bot_management/logs')

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.WARNING,
        handlers=[
            TimedRotatingFileHandler(
                "bot_management/logs/bot_management.log",
                when="midnight",
                encoding=None,
                delay=False,
                backupCount=10,
            ),
            logging.StreamHandler(),
        ],
    )

    LOGS = logging.getLogger(__name__)
    LOGS.setLevel(logging.INFO)
    return LOGS

def app_init(api_id, api_hash, token):

    app = Client(f"WatermarkingBot",
                    api_id=api_id,
                    api_hash=api_hash,
                    bot_token=token,
                    plugins=dict(root="bot_management/plugins"),
                    workdir="./bot_management")

    parse_mode = ParseMode.HTML
    app.set_parse_mode(parse_mode=parse_mode)
    Conversation(app)
    
    return app

config = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')

API_ID = config['pyrogram']['API_ID']
API_HASH = config['pyrogram']['API_HASH']
BOT_TOKEN = config['pyrogram']['BOT_TOKEN']

FOLDER_NAME = config['mega']['folder_name']
FILE_NAME = config['mega']['file_name']
UPLOADS_FOLDER = 'uploads/'
DELETE_FILES = [file.strip() for file in config.get('mega', 'delete_files', fallback="").split(',') if file.strip()]
PICS_KEYWORDS = [file.strip() for file in config.get('mega', 'pics_keywords', fallback="").split(',') if file.strip()]
VIDS_KEYWORDS = [file.strip() for file in config.get('mega', 'vids_keywords', fallback="").split(',') if file.strip()]
PPV_KEYWORDS = [file.strip() for file in config.get('mega', 'ppv_keywords', fallback="").split(',') if file.strip()]
SITERIP_KEYWORDS = [file.strip() for file in config.get('mega', 'siterip_keywords', fallback="").split(',') if file.strip()]

authorized_users = [6569281895,1339883138]

app = app_init(API_ID, API_HASH, BOT_TOKEN)
LOGS = logging_init()

