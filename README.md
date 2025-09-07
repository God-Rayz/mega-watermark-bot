# Mega Watermark Bot

A Telegram bot for automatically watermarking content with customizable branding and managing bulk processing operations.

## ⚠️ LIMITED VERSION NOTICE

This repository contains a **limited version** of the Mega Watermark Bot. Some advanced features and full functionality are restricted in this public release.

**For the complete, full-featured version with all advanced capabilities, please contact the developer for licensing information.**

## Features (Limited Version)

- **Basic Watermarking**: Adds watermarks to images and videos *(limited functionality)*
- **Basic Processing**: Handles content processing *(reduced capabilities)*
- **Mega Integration**: Works with MEGA file storage *(basic features only)*
- **Account Management**: Basic account operations *(limited automation)*
- **Custom Branding**: Configurable watermark text and styling *(restricted options)*
- **File Organization**: Basic file categorization *(simplified version)*

### 🔒 Full Version Features (Available via License)

- **Advanced Bulk Processing**: Unlimited batch processing with optimization
- **Complete Account Automation**: Full automated account creation and management
- **Premium Watermarking**: Advanced watermarking with custom positioning and effects
- **Advanced Mega Integration**: Full MEGA API integration with bulk operations
- **Custom Branding Suite**: Complete branding customization options
- **Priority Support**: Direct developer support and updates
- **Commercial License**: Full commercial usage rights

## Setup

### Prerequisites

- Python 3.7+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Telegram API credentials (from [my.telegram.org](https://my.telegram.org))

### Installation

1. Clone the repository:
```bash
git clone https://github.com/God-Rayz/mega-watermark-bot.git
cd mega-watermark-bot
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

## 💰 Licensing & Full Version

This public repository contains a **limited version** of the Mega Watermark Bot. 

### Get the Full Version

For the complete, unrestricted version with all features:

- **Contact**: Reach out to the developer for licensing information
- **Features**: Full automation, advanced watermarking, unlimited processing
- **Support**: Priority support and regular updates
- **Commercial Use**: Full commercial licensing available

### Limited Version Restrictions

- Reduced processing capabilities
- Limited automation features
- Basic watermarking options only
- No commercial usage rights
- Community support only

## Support

For issues with the limited version, please open an issue on GitHub.

For full version inquiries and licensing, please contact the developer directly.
