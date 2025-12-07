# Daily Hebrew Word Bot

This project sends 5 advanced Hebrew words to your Telegram chat every morning using GitHub Actions and the Gemini API.

## Setup Instructions

### 1. Get Credentials

*   **Telegram Bot Token**:
    1. Open Telegram and search for `@BotFather`.
    2. Send `/newbot` and follow the instructions.
    3. Copy the **HTTP API Token**.

*   **Telegram Chat ID**:
    1. Provide your Chat ID as you mentioned, OR:
    2. Start a chat with your new bot (send `/start`).
    3. Forward a message from that chat to `@userinfobot` to get your numeric ID.

*   **Gemini API Key**:
    1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
    2. Create a new API key.

### 2. Configure GitHub Secrets

1. Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**.
3. Add the following secrets:
    *   `TELEGRAM_BOT_TOKEN`: Your bot token.
    *   `TELEGRAM_CHAT_ID`: Your numeric chat ID.
    *   `GEMINI_API_KEY`: Your Google Gemini API key.

## How it Works

*   **Daily Trigger**: The bot runs automatically at 6:00 AM UTC via GitHub Actions.
*   **Word Generation**: Uses Gemini to generate 5 new words that are *not* in `history.json`.
*   **History**: It updates `history.json` automatically after each run to prevent duplicates.

## Testing Locally (Optional)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables (`TELEGRAM_BOT_TOKEN`, etc.) or create a `.env` file.
3. Run:
   ```bash
   python main.py
   ```
