"""Logging configuration for the LinkedIn Knowledge Management System."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from .config import Config


def setup_logger(
    name: str = "linkedin_kms",
    config: Optional[Config] = None
) -> logging.Logger:
    """Set up structured logging for the application."""
    
    if config is None:
        config = Config.from_env()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if config.enable_file_logging:
        try:
            # Ensure log directory exists
            log_path = Path(config.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                config.log_file_path,
                maxBytes=config.max_log_file_size_mb * 1024 * 1024,  # Convert MB to bytes
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, config.log_level.upper()))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    return logger


def get_logger(name: str = "linkedin_kms") -> logging.Logger:
    """Get an existing logger or create a new one."""
    return logging.getLogger(name)