# Telegram Watermark Bot

A Telegram bot for automatically watermarking content with customizable branding and managing bulk processing operations.

## Features

- **Automatic Watermarking**: Adds watermarks to images and videos
- **Bulk Processing**: Handles large batches of content efficiently
- **Mega Integration**: Works with MEGA file storage
- **Account Management**: Automated account creation and management
- **Custom Branding**: Configurable watermark text and styling
- **File Organization**: Automatic file categorization and cleanup

## Setup

### Prerequisites

- Python 3.7+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Telegram API credentials (from [my.telegram.org](https://my.telegram.org))

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd Leakifyhub-copy
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the bot:
```bash
cp config.ini.template config.ini
```

4. Edit `config.ini` with your credentials:
   - Replace `your_api_id_here` with your Telegram API ID
   - Replace `your_api_hash_here` with your Telegram API Hash
   - Replace `your_bot_token_here` with your bot token

### Running the Bot

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

**Manual:**
```bash
python -m bot_management
```

## Configuration

The `config.ini` file contains all bot settings:

- **Pyrogram Settings**: API credentials and bot token
- **Mega Settings**: File naming patterns and cleanup rules
- **Keywords**: File type detection patterns

## Project Structure

```
├── bot_management/          # Main bot code
│   ├── plugins/            # Bot plugins and handlers
│   ├── mega/              # MEGA integration
│   ├── tempmail/          # Temporary email services
│   └── watermark.py       # Watermarking functionality
├── bulk_processes/        # Bulk processing data
├── uploads/               # Default upload directory
└── config.ini            # Configuration file (not in repo)
```

## Security Notice

⚠️ **Never commit sensitive files to version control:**
- `config.ini` (contains API keys)
- `credentials.txt` (contains account credentials)
- `new_accounts.txt` (contains account data)

These files are automatically excluded via `.gitignore`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational purposes. Please ensure compliance with Telegram's Terms of Service and applicable laws in your jurisdiction.

## Support

For issues and questions, please open an issue on GitHub.
