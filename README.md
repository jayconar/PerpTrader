# Binance Perpetual Futures Trading Bot

A modular Python bot for automated trading on Binance USDT-margined perpetual futures. Designed for plug-and-play strategies, detailed logging, email notifications, and real-time Google Sheets updates.

---

## 🚀 Features
* **Testnet compatibility**: Easily switch between Testnet and Mainnet for testing by changing the boolean value of `TESTNET` in `config.py`
* **Modular Architecture**: Separate core logic from strategies. Swap strategies by name in the `config.py`, no code changes required.
* **Strategy Interface**: Define `entry_signal()` and `exit_signal()` by inheriting `StrategyInterface` in your custom strategy class.
* **Long & Short Support**: Dynamically determines trade side from strategy outputs.
* **Order Management**: Places limit buy orders and closes positions via market orders.
* **Precision Handling**: Automatically fetches symbol filters (tick size, step size) and rounds price/quantity using `decimal` for compliance.
* **Trade Logging**:

  * Appends each closed trade to `trades.csv` with columns:

    ```text
    Order ID | Side | Symbol | Quantity | Profit | Risk-to-Reward | Entry Price | Exit Price | Entry Time | Exit Time
    ```
* **Email Notifications**: Sends HTML-formatted trade summary emails after each trade.
* **Google Sheets Integration**: Appends the latest trade to a specified Google Sheet (Just add the sheets name in the config file).
* **Structured Logging**: Uses Loguru for colored console output and daily rotating log files.

---

## 📦 Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/jayconar/FuturesTrader.git
   ```

2. **Create & activate a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Copy `.env.example` to `.env` and fill in your keys:

   ```dotenv
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   SMTP_USERNAME=...
   SMTP_PASSWORD=...
   EMAIL_FROM=...
   EMAIL_TO=...
   ```

5. **Create Google service account**

   * Enable Google Sheets & Drive APIs.
   * Download JSON key, place it in the src/records folder and share your sheet with the service account email.

---

## 🗂️ Project Structure

```
FuturesTraderBot/
├── .env
├── requirements.txt
├── README.md
└── src/
    ├── main.py                     # Entry point and trade loop
    ├── config.py                   # Loads environment settings
    ├── logger.py                   # Loguru configuration
    ├── trader.py                   # Binance API wrapper and order logic
    ├── trade_logger.py             # CSV logging for closed trades
    ├── notifier.py                 # HTML email summaries
    ├── sheets_updater.py           # Append trades to Google Sheet
    ├── strategy_loader.py          # Dynamic strategy importer
    └── strategy/                   # Folder for custom strategies
        ├── strategy_template.py
        └── sample_strategy.py  <-- # Your Strategy goes here
```

---

## ⚙️ Usage

```bash
python src/main.py
```

The bot will:

1. Fetch all available USDT perpetual futures pairs.
2. Fetch candlestick data for each symbol one by one.
3. Evaluate `entry_signal()`; place limit order if true.
4. Monitor for fill, cancel on SL/TP misses.
5. Once filled, monitor `exit_signal()`; close position on trigger.
6. Log the trade to `trades.csv` and append to Google Sheet.
7. Send an HTML email summary.
8. Repeat indefinitely.

---

## 🎯 Creating Custom Strategies

1. Add a new file in `bot/strategy/`, e.g. `my_strategy.py`.
2. Inherit from `StrategyInterface`:

   ```python
   from src.strategy.strategy_template import StrategyInterface

   class MyStrategy(StrategyInterface):
       def entry_signal(self, candles):
           # return (bool, entry_price, stop_loss, target)

       def exit_signal(self, candles, entry_price):
           # return bool
   ```
3. Set `STRATEGY_NAME=my_strategy` in `config`.

---

*Trade responsibly! This bot is provided as-is; always test on paper/demo accounts first.*
