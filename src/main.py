from binance.enums import SIDE_BUY, SIDE_SELL
from src.strategy_loader import load_strategy
from src.sheets_updater import update_sheet
from src.trade_logger import log_trade
from src.notifier import send_email
from src.config import config
from src.logger import logger
from src.trader import Trader
from datetime import datetime
from src.art import art
import time


def main():
    logger.info("LET THE OBAMANATOR COOK...")
    time.sleep(1)
    print(art)
    trader = Trader()
    strategy = load_strategy(config.STRATEGY_NAME)
    symbols = trader.get_available_pairs()
    entry_time, exit_time = 0, 0
    logger.info(f"{len(symbols)} trading pairs fetched")
    logger.info(f"Looking for trades...")

    while True:
        for symbol in symbols:
            candles = trader.get_candles(symbol, config.TIMEFRAME, limit=config.CANDLE_LIMIT)
            if not candles:
                continue

            signal, side, entry_price, stop_loss, target = strategy.entry_signal(symbol, candles)
            if not signal:
                continue

            side_enum = SIDE_BUY if side == "LONG" else SIDE_SELL
            logger.info(f"{side_enum} Entry signal for {symbol} at {entry_price}, SL: {stop_loss}, TP: {target}")
            trader.set_leverage(symbol, config.LEVERAGE)
            quantity = trader.calculate_order_quantity(symbol, entry_price)
            if quantity <= 0:
                logger.warning(f"Trade amount too small for {symbol}; skipping..")
                continue

            order = trader.place_limit_order(
                symbol=symbol, side=side_enum, quantity=quantity, price=entry_price
            )
            if not order:
                logger.info(f"Looking for trades...")
                continue

            order_id = str(order["orderId"])
            order_filled = False

            while not order_filled:
                time.sleep(5)
                current = trader.get_ticker(symbol)
                if not current:
                    continue
                last_close = float(current["price"])

                if trader.check_order_filled(symbol, order_id):
                    logger.info(f"Entry order filled at {entry_price} (ID: {order_id})")
                    entry_time = time.time()
                    order_filled = True
                    break
                if strategy.exit_signal(side_enum, last_close, target, stop_loss):
                    logger.warning(f"SL/TP hit before fill for {symbol}; canceling order {order_id}")
                    trader.cancel_order(symbol, order_id)
                    break

            if not order_filled:
                logger.info(f"Looking for trades...")
                continue

            logger.info(f"Monitoring {symbol} for exit...")
            while True:
                time.sleep(5)
                last_traded_price = trader.get_ticker(symbol).get("price", None)
                if not last_traded_price:
                    continue
                if strategy.exit_signal(side, float(last_traded_price), target, stop_loss):
                    logger.info(f"Exit signal triggered for {symbol} (ID: {order_id})")
                    trader.close_position(symbol, quantity, side_enum)
                    exit_time = time.time()
                    break

            trade_cost = config.TRADE_QUANTITY_USDT
            exit_price = last_traded_price

            # Calculate profit and risk-reward ratio based on side
            if entry_price >= stop_loss:
                risk_reward = (target - entry_price) / (entry_price - stop_loss)
                profit = ((exit_price - entry_price) / entry_price) * trade_cost
            else:
                risk_reward = (entry_price - target) / (stop_loss - entry_price)
                profit = ((entry_price - exit_price)/entry_price) * trade_cost
            risk_reward = f"1:{round(risk_reward)}"

            log_trade(
                order_id=order_id,
                side=side,
                symbol=symbol,
                cost=trade_cost,
                quantity=quantity,
                profit=profit,
                risk_reward=risk_reward,
                entry_price=entry_price,
                exit_price=exit_price,
                entry_time=entry_time,
                exit_time=exit_time
            )

            email_body = f"""
Trade Completed!

Order ID: {order_id}
Pair: {symbol}
Side: {side}
Cost: {trade_cost}
Quantity: {quantity}
Profit: {round(profit, 8)}
Profit%: {round(profit*100/trade_cost, 2)}%
Risk:Reward: {risk_reward}
Entry Price: {entry_price}
Exit Price: {exit_price}
Entry Time: {datetime.fromtimestamp(entry_time)}
Exit Time: {datetime.fromtimestamp(exit_time)}
"""
            send_email(email_body)
            logger.info(f"Trade complete for {symbol}, logged and notified.")
            update_sheet(
                csv_path=config.TEMP_TRADE_LOG_FILE,
                sheet_name=config.GOOGLE_SHEET_NAME,
                credentials_json=config.GOOGLE_CREDENTIALS_JSON
            )
        time.sleep(3)
        logger.info(f"Looking for trades...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error in main execution: {e}", exc_info=True)
        logger.info("Bot shutdown unexpectedly")