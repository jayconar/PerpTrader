from loguru import logger
import sys

# Remove the default Loguru handler
logger.remove()

# Define a consistent log format
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Console handler: colored, human-readable
logger.add(
    sys.stdout,
    level="DEBUG",
    format=LOG_FORMAT,
    colorize=True,
    enqueue=True,
)

# File handler: daily rotation, keep one week of logs
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="00:00",            # rotate at midnight
    retention="7 days",         # keep logs for 7 days
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    enqueue=True,
)
