from abc import ABC, abstractmethod


class StrategyInterface(ABC):
    """
    All strategies must inherit from this interface and implement these methods.
    """

    @abstractmethod
    def entry_signal(self, symbol, candles: list) -> tuple[bool, str, float, float, float]:
        """
        Determine whether to enter a trade.

        Args:
            symbol (str): Symbol of the trade pair.
            candles (list): List of candlestick dictionaries.

        Returns:
            tuple: (should_enter: bool, side: str, entry_price: float, stop_loss: float, target_price: float)
        """
        pass

    @abstractmethod
    def exit_signal(self, side: str, ltp: float, target: float, stop: float) -> bool:
        """
        Determine whether to exit a trade.

        Args:
            side (str): Side ("Long"/"Short") of entry order.
            ltp (float): Last traded price of the Trade pair.
            target (float): Target price or the Take profit price.
            stop (float): Stop loss price.

        Returns:
            bool: True if exit conditions are met, False otherwise.
        """
        pass