from datetime import datetime, timezone
from src.config import config
import csv
import os

files = [config.TRADE_LOG_FILE, config.TEMP_TRADE_LOG_FILE]


def log_trade(
        order_id: str,
        side: str,
        symbol: str,
        cost: float,
        quantity: float,
        profit: float,
        risk_reward: str,
        entry_price: float,
        exit_price: float,
        entry_time: int,
        exit_time: int
):
    for file in files:
        # Determine if we need headers (If file doesn't exist OR exists but empty)
        write_header = not os.path.exists(file) or os.stat(file).st_size == 0

        with open(file, mode="a", newline="") as f:
            writer = csv.writer(f)

            if write_header:
                writer.writerow([
                    "order_id",
                    "side",
                    "symbol",
                    "cost",
                    "quantity",
                    "profit",
                    "risk_to_reward",
                    "entry_price",
                    "exit_price",
                    "entry_time",
                    "exit_time"
                ])
            writer.writerow([
                order_id,
                side,
                symbol,
                cost,
                quantity,
                round(profit, 8),
                risk_reward,
                entry_price,
                exit_price,
                datetime.fromtimestamp(entry_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                datetime.fromtimestamp(exit_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            ])