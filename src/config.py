from dotenv import load_dotenv
from pathlib import Path
import os

# Get the path to the current file
BASE_DIR = Path(__file__).resolve().parent

# Load .env in project root
load_dotenv()

class Config:
    # Binance API
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
    TESTNET = True

    # Email (SMTP)
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM = os.getenv("EMAIL_FROM")
    EMAIL_TO = os.getenv("EMAIL_TO")

    # Strategy Specific Settings
    TRADE_QUANTITY_USDT = 122.0
    LEVERAGE = 3
    TIMEFRAME = "1h"
    LOWER_TIMEFRAME = "5m"
    CANDLE_LIMIT = 44
    LOWER_CANDLE_LIMIT = 60
    STRATEGY_NAME = "liquidity_sweep_strategy"

    # File Paths
    GOOGLE_SHEET_NAME = "Obamanator_Trades"
    TRADE_LOG_FILE = BASE_DIR / 'records' / 'trades.csv'
    TEMP_TRADE_LOG_FILE = BASE_DIR / 'records' / 'recent_trades.csv'
    GOOGLE_CREDENTIALS_JSON = BASE_DIR / 'records' / 'credentials.json'

config = Config()