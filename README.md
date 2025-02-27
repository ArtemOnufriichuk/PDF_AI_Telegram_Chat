# Telegram PDF Chat Bot

A Telegram bot that allows users to analyze PDF documents and answer questions about their content. The bot uses ChatPDF API to process documents and generate responses based on the PDF content.

## Features

- **PDF Processing**: Upload PDF documents to the bot for analysis
- **Question Answering**: Ask questions about the content of your uploaded PDF
- **Conversation History**: The bot maintains conversation history for better context understanding
- **Simple Interface**: Easy to use with intuitive commands and inline buttons

## Requirements

- Python 3.8+
- Telegram Bot Token (from BotFather)
- ChatPDF API Key

## Installation

1. Clone this repository:

   ```
   git clone <repository-url>
   cd telegram-pdf-bot
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   # Copy the example file
   cp .env.example .env
   # Edit the .env file with your actual API keys
   ```

## Usage

1. Start the bot:

   ```
   python bot.py
   ```

2. Open Telegram and find your bot by its username

3. Send the `/start` command to the bot to get started

4. Upload a PDF file to the bot

5. Ask questions about the content of the PDF

## Commands

- `/start` - Start the bot and get help information
- `/reset` - Clear the current document and conversation history

## Development

### Environment Variables

The following environment variables are required:

- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot token obtained from BotFather
- `CHATPDF_API_KEY`: Your ChatPDF API key

These can be set in the `.env` file or in your environment.

## License

[MIT License](LICENSE)

## Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - The Telegram Bot API wrapper
- [ChatPDF API](https://chatpdf.com/api) - For PDF processing and question answering capabilities
