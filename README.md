# Weekly Momentum Stocks Rebalance

This script fetches stocks from Screener.in, calculates momentum scores based on RSI and other metrics, and ranks the top 10 stocks for weekly rebalancing.

## Local Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv myvenv
   source myvenv/bin/activate  # On Windows: myvenv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the script:
   ```bash
   python weekly.py
   ```

## Automated Weekly Reports

The script is set up to run automatically every Friday at 8 PM IST via GitHub Actions, sending a report to a Telegram channel.

### Setup GitHub Repository

1. Create a new repository on GitHub.

2. Push this code to GitHub:
   ```bash
   git remote add origin https://github.com/yourusername/yourrepo.git
   git push -u origin main
   ```

### Configure Telegram Secrets

In your GitHub repository settings, go to Secrets and Variables > Actions, and add the following secrets:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (e.g., 5882732230:AAE5e3XlDU7ckuGbWLIavfGyuzpQTnSD5jE)
- `TELEGRAM_CHAT_ID`: The chat ID of your Telegram channel (e.g., -1001848013789)

**Note:** Ensure your bot is added to the channel and has permission to send messages/documents.

### Workflow Details

- **Schedule**: Every Friday at 14:30 UTC (8 PM IST)
- **Actions**:
  - Sets up Python 3.10
  - Installs dependencies
  - Runs the script and captures output
  - Sends Telegram message with output file attached

You can also trigger the workflow manually from the Actions tab.

## Script Output

The script outputs the top 10 momentum stocks with their symbols, sectors, and scores, sorted by momentum score descending.
