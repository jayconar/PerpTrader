import importlib
from src.logger import logger
from src.strategy.strategy_template import StrategyInterface


def load_strategy(strategy_name: str) -> StrategyInterface:
    """
    Dynamically import a strategy by name. It must be in src/strategy/
    and implement StrategyInterface.
    """
    try:
        module_path = f"src.strategy.{strategy_name}"
        module = importlib.import_module(module_path)

        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, StrategyInterface) and obj != StrategyInterface:
                # logger.info(f"Loaded strategy: {obj.__name__} from {strategy_name}.py")
                return obj()

        raise ImportError("No valid strategy class found.")
    except Exception as e:
        logger.error(f"Failed to load strategy '{strategy_name}': {e}")
        raise
