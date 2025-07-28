from src.strategy.strategy_template import StrategyInterface
from binance.client import Client
from src.config import config
from src.logger import logger


class LiquiditySweepStrategy(StrategyInterface):
    def _get_candles(self, symbol, interval, limit=100):
        try:
            exchange = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=config.TESTNET)
            klines = exchange.futures_klines(symbol=symbol, interval=interval, limit=limit)
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

    def _detect_fvg(self, candles: list, fvg_type: str) -> list:
        """
        Detect Fair Value Gaps (FVGs) in candle data

        Args:
            candles: List of candlestick data
            fvg_type: 'bullish' or 'bearish'

        Returns:
            List of FVG dictionaries with:
                'type': fvg_type
                'zone': (top, bottom) price levels
                'candle_index': index of the last candle in the FVG pattern
        """
        fvgs = []
        for i in range(2, len(candles)):
            if fvg_type == 'bullish':
                # Bullish FVG: Middle candle high < first candle low
                if candles[i - 1]['high'] < candles[i - 2]['low']:
                    fvgs.append({
                        'type': 'bullish',
                        'zone': (candles[i - 1]['high'], candles[i - 2]['low']),
                        'candle_index': i
                    })
            elif fvg_type == 'bearish':
                # Bearish FVG: Middle candle low > first candle high
                if candles[i - 1]['low'] > candles[i - 2]['high']:
                    fvgs.append({
                        'type': 'bearish',
                        'zone': (candles[i - 2]['high'], candles[i - 1]['low']),
                        'candle_index': i
                    })
        return fvgs

    def _check_inverse_fvg(self, candles: list, side: str) -> tuple:
        """
        Check for inverse FVG pattern according to specifications

        Args:
            candles: List of candlestick data
            side: 'LONG' or 'SHORT'

        Returns:
            tuple: (is_valid, entry_price, stop_loss, target_price)
        """
        if len(candles) < 20:
            return (False, 0, 0, 0)

        # Find key candle based on trade side
        if side == "LONG":
            # Find lowest low candle
            low_val = float('inf')
            key_index = -1
            for i, candle in enumerate(candles):
                if candle['low'] < low_val:
                    low_val = candle['low']
                    key_index = i
        else:
            # Find the highest high candle
            high_val = float('-inf')
            key_index = -1
            for i, candle in enumerate(candles):
                if candle['high'] > high_val:
                    high_val = candle['high']
                    key_index = i

        # Validate enough candles before and after key candle
        if key_index < 10 or key_index > len(candles) - 10:
            return False, 0, 0, 0

        # Find FVGs before and after the key candle
        if side == "LONG":
            # For LONG trades: look for bearish FVG before key candle
            bearish_fvgs = self._detect_fvg(candles[:key_index], 'bearish')
            if not bearish_fvgs:
                return False, 0, 0, 0

            # Get the most recent bearish FVG
            bearish_fvg = bearish_fvgs[-1]
            fvg_top = bearish_fvg['zone'][0]

            # Get OB top (high of candle before FVG)
            ob_top_candle = candles[bearish_fvg['candle_index'] - 3]
            ob_top = ob_top_candle['high']

            # Find bullish FVG after key candle
            bullish_fvgs = self._detect_fvg(candles[key_index:], 'bullish')
            if not bullish_fvgs:
                return False, 0, 0, 0

            # Get the first bullish FVG after key candle
            bullish_fvg = bullish_fvgs[0]
            fvg_candle_index = key_index + bullish_fvg['candle_index']
            fvg_candle = candles[fvg_candle_index]

            # Check conditions
            condition1 = any(candle['close'] > fvg_top
                             for candle in candles[key_index:])
            condition2 = any(candle['high'] > ob_top
                             for candle in candles[key_index:])

            if condition1 and condition2:
                # Entry price is max of open/close of third candle in bullish FVG
                entry_price = max(fvg_candle['open'], fvg_candle['close'])
                stop_loss = low_val * 0.999  # Slightly below key low
                risk = entry_price - stop_loss
                target_price = entry_price + (3 * risk)  # 1:3 RR
                return True, entry_price, stop_loss, target_price

        else:
            # For SHORT trades: look for bullish FVG before key candle
            bullish_fvgs = self._detect_fvg(candles[:key_index], 'bullish')
            if not bullish_fvgs:
                return False, 0, 0, 0

            # Get the most recent bullish FVG
            bullish_fvg = bullish_fvgs[-1]
            fvg_bottom = bullish_fvg['zone'][1]

            # Get OB bottom (low of candle before FVG)
            ob_bottom_candle = candles[bullish_fvg['candle_index'] - 3]
            ob_bottom = ob_bottom_candle['low']

            # Find bearish FVG after key candle
            bearish_fvgs = self._detect_fvg(candles[key_index:], 'bearish')
            if not bearish_fvgs:
                return False, 0, 0, 0

            # Get the first bearish FVG after key candle
            bearish_fvg = bearish_fvgs[0]
            fvg_candle_index = key_index + bearish_fvg['candle_index']
            fvg_candle = candles[fvg_candle_index]

            # Check conditions
            condition1 = any(candle['close'] < fvg_bottom
                             for candle in candles[key_index:])
            condition2 = any(candle['low'] < ob_bottom
                             for candle in candles[key_index:])

            if condition1 and condition2:
                # Entry price is min of open/close of third candle in bearish FVG
                entry_price = min(fvg_candle['open'], fvg_candle['close'])
                stop_loss = high_val * 1.001  # Slightly above key high
                risk = stop_loss - entry_price
                target_price = entry_price - (3 * risk)  # 1:3 RR
                return (True, entry_price, stop_loss, target_price)

        return False, 0, 0, 0

    # Existing liquidity sweep detection methods remain unchanged
    def detect_liquidity_sweep(self, candles: list) -> tuple:
        """
        Detect liquidity sweep both buy-side and sell-side
        """
        n = len(candles)
        if n < 15:  # Need sufficient data for reliable detection
            return None, None, None

        # Try to detect sell-side sweep for long positions
        sweep_type, swing_point, key_index = self._detect_sell_side_sweep(candles)
        if sweep_type:
            return sweep_type, swing_point, key_index

        # Try to detect buy-side sweep for short positions
        sweep_type, swing_point, key_index = self._detect_buy_side_sweep(candles)
        if sweep_type:
            return sweep_type, swing_point, key_index

        return None, None, None

    def _find_highest_high(self, candles: list, start: int, end: int) -> tuple:
        """
        Find the highest high in range with latest occurrence
        Returns: (high_value, index)
        """
        highest_high = -float('inf')
        highest_index = -1
        for i in range(start, end):
            if candles[i]['high'] > highest_high:
                highest_high = candles[i]['high']
                highest_index = i
            elif candles[i]['high'] == highest_high and i > highest_index:
                highest_index = i
        return highest_high, highest_index

    def _find_lowest_low(self, candles: list, start: int, end: int) -> tuple:
        """
        Find the lowest low in range with latest occurrence
        Returns: (low_value, index)
        """
        lowest_low = float('inf')
        lowest_index = -1
        for i in range(start, end):
            if candles[i]['low'] < lowest_low:
                lowest_low = candles[i]['low']
                lowest_index = i
            elif candles[i]['low'] == lowest_low and i > lowest_index:
                lowest_index = i
        return lowest_low, lowest_index

    def _detect_sell_side_sweep(self, candles: list) -> tuple:
        """Detect sell-side liquidity sweep for long positions"""
        n = len(candles)
        exclude_last = 5
        search_end = n - exclude_last

        # Find recent highest high excluding last 5 candles
        recent_high, recent_high_idx = self._find_highest_high(candles, 0, search_end)

        # Find prior highest high with at least 5 candles in between
        prior_search_end = max(0, recent_high_idx - 5)
        prior_high, prior_high_idx = self._find_highest_high(candles, 0, prior_search_end)

        # Validate we have at least 5 candles between highs
        if recent_high_idx - prior_high_idx < 5:
            return None, None, None

        # Find swing low between the two highs
        start_idx = min(prior_high_idx, recent_high_idx)
        end_idx = max(prior_high_idx, recent_high_idx)
        swing_low, _ = self._find_lowest_low(candles, start_idx, end_idx + 1)

        # Check sweep and reversal conditions
        swept = any(candle['low'] < swing_low for candle in candles[-5:])
        reversed = candles[-1]['close'] > swing_low

        if swept and reversed:
            return "LONG", swing_low, recent_high_idx

        return None, None, None

    def _detect_buy_side_sweep(self, candles: list) -> tuple:
        """Detect buy-side liquidity sweep (for short positions)"""
        n = len(candles)
        exclude_last = 5
        search_end = n - exclude_last

        # Find recent lowest low excluding last 5 candles
        recent_low, recent_low_idx = self._find_lowest_low(candles, 0, search_end)

        # Find prior lowest low with at least 5 candles in between
        prior_search_end = max(0, recent_low_idx - 5)
        prior_low, prior_low_idx = self._find_lowest_low(candles, 0, prior_search_end)

        # Validate we have at least 5 candles between lows
        if recent_low_idx - prior_low_idx < 5:
            return None, None, None

        # Find swing high between the two lows
        start_idx = min(prior_low_idx, recent_low_idx)
        end_idx = max(prior_low_idx, recent_low_idx)
        swing_high, _ = self._find_highest_high(candles, start_idx, end_idx + 1)

        # Check sweep and reversal conditions
        swept = any(candle['high'] > swing_high for candle in candles[-5:])
        reversed = candles[-1]['close'] < swing_high

        if swept and reversed:
            return "SHORT", swing_high, recent_low_idx

        return None, None, None

    def _find_fvg(self, candles: list, start_idx: int, end_idx: int, fvg_type: str) -> list:
        """
        Find Fair Value Gaps (FVGs) in candle data
        Args:
            candles: List of candles
            start_idx: Start index for search
            end_idx: End index for search
            fvg_type: 'bearish' or 'bullish'
        Returns:
            List of FVG dictionaries with keys:
                'start_index': Index of first candle in FVG
                'zone': (top_price, bottom_price) of FVG zone
                'fvg_top': Low of first candle (for bearish) or high of first candle (for bullish)
                'ob_top': High of candle before FVG (for bearish) or low of candle before FVG (for bullish)
        """
        fvgs = []
        for i in range(start_idx, end_idx - 2):
            candle1 = candles[i]
            candle2 = candles[i + 1]
            candle3 = candles[i + 2]

            if fvg_type == 'bearish':
                # Bearish FVG: High of candle1 < Low of candle3
                if candle1['high'] < candle3['low']:
                    # Get OB top (high of candle before FVG)
                    ob_top = candles[i - 1]['high'] if i > 0 else None
                    fvgs.append({
                        'start_index': i,
                        'zone': (candle1['high'], candle3['low']),
                        'fvg_top': candle1['low'],  # Low of first candle
                        'ob_top': ob_top  # High of candle before FVG
                    })

            elif fvg_type == 'bullish':
                # Bullish FVG: Low of candle1 > High of candle3
                if candle1['low'] > candle3['high']:
                    # Get OB bottom (low of candle before FVG)
                    ob_bottom = candles[i - 1]['low'] if i > 0 else None
                    fvgs.append({
                        'start_index': i,
                        'zone': (candle3['high'], candle1['low']),
                        'fvg_bottom': candle1['high'],  # High of first candle
                        'ob_bottom': ob_bottom  # Low of candle before FVG
                    })
        return fvgs

    def _verify_inverse_fvg(self, candles: list, lowest_low_index: int, order_type: str) -> tuple:
        """
        Verify inverse FVG conditions
        Returns:
            tuple: (is_valid, entry_price, stop_loss, target_price)
        """
        n = len(candles)
        # 1. Find bearish FVG before the lowest low (for long) or bullish FVG before the highest high (for short)
        fvg_before = self._find_fvg(
            candles,
            max(0, lowest_low_index - 50),  # Search up to 50 candles before
            lowest_low_index - 2,  # End before the lowest low
            'bearish' if order_type == 'LONG' else 'bullish'
        )

        if not fvg_before:
            return False, 0, 0, 0

        # Use the most recent FVG before the low point
        fvg_before = fvg_before[-1]

        # 2. Find FVG after the low point
        fvg_after = self._find_fvg(
            candles,
            lowest_low_index,
            n - 2,
            'bullish' if order_type == 'LONG' else 'bearish'
        )

        if not fvg_after:
            return False, 0, 0, 0

        # Use the first FVG after the low point
        fvg_after = fvg_after[0]

        # 3. Check violation conditions
        violation_condition1 = False
        violation_condition2 = False

        # Check candles after the low point
        for i in range(lowest_low_index + 1, n):
            candle = candles[i]

            if order_type == 'LONG':
                # Check close above fvg_top (low of first candle in bearish FVG)
                if candle['close'] > fvg_before['fvg_top']:
                    violation_condition1 = True

                # Check high above ob_top (high of candle before bearish FVG)
                if fvg_before['ob_top'] is not None and candle['high'] > fvg_before['ob_top']:
                    violation_condition2 = True

            else:  # SHORT
                # Check close below fvg_bottom (high of first candle in bullish FVG)
                if candle['close'] < fvg_before['fvg_bottom']:
                    violation_condition1 = True

                # Check low below ob_bottom (low of candle before bullish FVG)
                if fvg_before['ob_bottom'] is not None and candle['low'] < fvg_before['ob_bottom']:
                    violation_condition2 = True

            if violation_condition1 and violation_condition2:
                break

        if not (violation_condition1 and violation_condition2):
            return False, 0, 0, 0

        # 4. Calculate entry price (max of open/close for third candle in FVG after)
        third_candle_idx = fvg_after['start_index'] + 2
        third_candle = candles[third_candle_idx]
        entry_price = max(third_candle['open'], third_candle['close'])

        # 5. Calculate risk management (1:3 RR)
        if order_type == 'LONG':
            stop_loss = candles[lowest_low_index]['low'] * 0.999  # Slightly below lowest low
            risk = entry_price - stop_loss
            target_price = entry_price + (3 * risk)
        else:  # SHORT
            stop_loss = candles[lowest_low_index]['high'] * 1.001  # Slightly above highest high
            risk = stop_loss - entry_price
            target_price = entry_price - (3 * risk)

        return True, entry_price, stop_loss, target_price

    def entry_signal(self, symbol, candles: list) -> tuple:
        # Step 1: Detect liquidity sweep
        side, swing_point, key_index = self.detect_liquidity_sweep(candles)

        if not side:
            return False, "", 0, 0, 0

        # Step 2: Switch to lower timeframe
        ltf_candles = self._get_candles(
            symbol,
            config.LOWER_TIMEFRAME,
            config.LOWER_CANDLE_LIMIT
        )

        if len(ltf_candles) < 20:  # Need at least 20 candles
            return False, "", 0, 0, 0

        # Step 3: Find lowest low (for LONG) or highest high (for SHORT)
        if side == "LONG":
            # Find lowest low candle index
            lowest_low = float('inf')
            lowest_low_index = -1
            for i, candle in enumerate(ltf_candles):
                if candle['low'] < lowest_low:
                    lowest_low = candle['low']
                    lowest_low_index = i
        else:  # SHORT
            # Find highest high candle index
            highest_high = -float('inf')
            lowest_low_index = -1  # Actually will be highest high index
            for i, candle in enumerate(ltf_candles):
                if candle['high'] > highest_high:
                    highest_high = candle['high']
                    lowest_low_index = i

        # Step 4: Verify we have enough candles around the key point
        if lowest_low_index < 10 or len(ltf_candles) - lowest_low_index < 10:
            return False, "", 0, 0, 0

        # Step 5: Verify inverse FVG conditions
        valid, entry_price, stop_loss, target_price = self._verify_inverse_fvg(
            ltf_candles,
            lowest_low_index,
            side
        )

        if valid:
            return True, side, entry_price, stop_loss, target_price

        return False, "", 0, 0, 0

    def exit_signal(self, side: str, ltp: float, target: float, stop: float) -> bool:
        # Simple exit when price hits target or stop loss
        if side == "LONG":
            return ltp >= target or ltp <= stop
        elif side == "SHORT":
            return ltp <= target or ltp >= stop
        return False
