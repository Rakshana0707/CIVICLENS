import logging
import sys
from backend.core.config import config

def setup_logger(name: str) -> logging.Logger:
    """
    Centralized logger factory.
    Creates structured logs in production and readable logs in debug mode.
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if instantiated multiple times
    if logger.handlers:
        return logger
        
    level = logging.DEBUG if config.DEBUG else logging.INFO
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Use JSON-like structured format for production, human-readable for debug
    if config.DEBUG:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        # Structured log simulating JSON payload
        formatter = logging.Formatter(
            '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
        )
        
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
