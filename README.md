# Telegram Crypto Bot

A Telegram bot for processing TRX payments with authorization and admin notifications.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd project
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables (or copy `.env.example`):
   ```
   BOT_TOKEN=your_telegram_bot_token
   TRON_NETWORK=nile  # or mainnet
   ADMIN_ID=your_admin_id
   TRX_RATE=3.25
   ```

4. Create a `data/` directory:
   ```bash
   mkdir data
   ```

5. Run the bot:
   ```bash
   python src/main.py
   ```

## Deployment

1. Copy the project to the server.
2. Update `.env` with production values (mainnet, real bot token).
