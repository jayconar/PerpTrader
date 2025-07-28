from decimal import Decimal
from binance.client import Client
from src.logger import logger
from src.config import config

class Trader:
    def __init__(self):
        self.exchange = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=config.TESTNET)
        logger.info("Binance Futures client initialized.")

    def get_symbol_filters(self, symbol):
        info = self.exchange.futures_exchange_info()
        for s in info['symbols']:
            if s['symbol'] == symbol:
                filters = {f['filterType']: f for f in s['filters']}
                price_precision = int(s['pricePrecision'])
                quantity_precision = int(s['quantityPrecision'])
                return {
                    "price_precision": price_precision,
                    "quantity_precision": quantity_precision,
                    "min_qty": float(filters['LOT_SIZE']['minQty']),
                    "step_size": float(filters['LOT_SIZE']['stepSize']),
                    "tick_size": float(filters['PRICE_FILTER']['tickSize']),
                }
        return None

    def round_down(self, value, step):
        """
        Round down `value` to nearest multiple of `step` using Decimal for precision.
        """
        value_dec = Decimal(str(value))
        step_dec = Decimal(str(step))
        return float((value_dec // step_dec) * step_dec)

    def calculate_order_quantity(self, symbol, entry_price):
        filters = self.get_symbol_filters(symbol)
        if not filters:
            logger.error(f"Symbol filters not found for {symbol}, can't calculate quantity.")
            return 0

        usdt_amount = config.TRADE_QUANTITY_USDT
        raw_qty = (usdt_amount * config.LEVERAGE) / entry_price
        quantity = self.round_down(raw_qty, filters['step_size'])

        if quantity < filters['min_qty']:
            logger.warning(f"Calculated quantity {quantity} is less than minimum {filters['min_qty']} for {symbol}")
            return 0
        return quantity

    def place_limit_order(self, symbol, side, quantity, price):
        try:
            filters = self.get_symbol_filters(symbol)
            if not filters:
                logger.error(f"Symbol filters not found for {symbol}")
                return None

            price = self.round_down(price, filters["tick_size"])
            quantity = self.round_down(quantity, filters["step_size"])

            order = self.exchange.futures_create_order(
                symbol=symbol,
                side=side,
                type="LIMIT",
                quantity=quantity,
                price=price,
                timeInForce="GTC"
            )
            logger.info(f"Limit order placed: {order}")
            return order

        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            return None

    def set_leverage(self, symbol, leverage):
        try:
            self.exchange.futures_change_leverage(symbol=symbol, leverage=leverage)
        except Exception as e:
            logger.error(f"Failed to set leverage for {symbol}: {e}")

    def get_available_pairs(self):
        info = self.exchange.futures_exchange_info()
        return [s['symbol'] for s in info['symbols'] if s['contractType'] == 'PERPETUAL' and s['status'] == 'TRADING']

    def get_candles(self, symbol, interval, limit=100):
        try:
            klines = self.exchange.futures_klines(symbol=symbol, interval=interval, limit=limit)
            return [
                {
                    "timestamp": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                }
                for k in klines
            ]
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
            return []

    def get_ticker(self, symbol):
        """
        Fetches the latest price of a trade pair. Better than fetching candles since candles tend to have older data
        """
        try:
            return self.exchange.futures_symbol_ticker(symbol=symbol)
        except Exception as e:
            logger.error(f"Failed to get last traded price for {symbol}: {e}")
            return []

    def check_order_filled(self, symbol, order_id):
        try:
            order = self.exchange.futures_get_order(symbol=symbol, orderId=order_id)
            return order['status'] == 'FILLED'
        except Exception as e:
            logger.error(f"Failed to check order status: {e}")
            return False

    def cancel_order(self, symbol, order_id):
        try:
            self.exchange.futures_cancel_order(symbol=symbol, orderId=order_id)
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")

    def close_position(self, symbol, quantity, side):
        opposite_side = "SELL" if side == "BUY" else "BUY"
        try:
            order = self.exchange.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                type="MARKET",
                quantity=quantity,
            )
            logger.info(f"Position closed on {symbol} with {opposite_side} MARKET order.")
            return order
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            return None