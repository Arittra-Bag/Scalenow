"""
Privacy-safe logging system that automatically sanitizes PII from log messages.
"""

import logging
import sys
from typing import Any, Dict, Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

from .pii_detector import PIIDetector, PIISanitizer, detect_and_sanitize_pii
from .config import Config


class PIISafeFormatter(logging.Formatter):
    """Custom log formatter that sanitizes PII from log messages."""
    
    def __init__(self, fmt: str = None, datefmt: str = None, sanitize_pii: bool = True):
        super().__init__(fmt, datefmt)
        self.sanitize_pii = sanitize_pii
        self.detector = PIIDetector() if sanitize_pii else None
        self.sanitizer = PIISanitizer() if sanitize_pii else None
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with PII sanitization."""
        # First, format the record normally
        formatted = super().format(record)
        
        if not self.sanitize_pii or not self.detector or not self.sanitizer:
            return formatted
        
        try:
            # Detect and sanitize PII in the formatted message
            sanitized_text, _ = detect_and_sanitize_pii(
                formatted, 
                strategy="mask", 
                min_confidence=0.6
            )
            return sanitized_text
        except Exception:
            # If sanitization fails, return original (better than crashing)
            return formatted


class PrivacyLogger:
    """Privacy-aware logger that sanitizes PII and provides secure logging."""
    
    def __init__(self, name: str, config: Config):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(name)
        self.detector = PIIDetector() if config.enable_pii_detection else None
        self.sanitizer = PIISanitizer() if config.sanitize_content else None
        
        # Configure logger
        self._setup_logger()
    
    def _setup_logger(self):
        """Set up the logger with appropriate handlers and formatters."""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Create formatter
        formatter = PIISafeFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            sanitize_pii=self.config.enable_pii_detection
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        self.logger.addHandler(console_handler)
        
        # File handler (if enabled)
        if self.config.enable_file_logging:
            try:
                # Create log directory
                log_path = Path(self.config.log_file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Rotating file handler
                file_handler = RotatingFileHandler(
                    filename=self.config.log_file_path,
                    maxBytes=self.config.max_log_file_size_mb * 1024 * 1024,
                    backupCount=5,
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(log_level)
                self.logger.addHandler(file_handler)
                
            except Exception as e:
                # Log to console if file logging fails
                self.logger.warning(f"Failed to setup file logging: {e}")
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize a log message to remove PII."""
        if not self.config.enable_pii_detection or not self.detector or not self.sanitizer:
            return message
        
        try:
            sanitized_text, _ = detect_and_sanitize_pii(
                message, 
                strategy="mask", 
                min_confidence=0.6
            )
            return sanitized_text
        except Exception:
            return message
    
    def _log_with_context(self, level: int, message: str, extra_data: Dict = None, 
                         sanitize: bool = True):
        """Log message with optional context data."""
        if sanitize:
            message = self._sanitize_message(message)
        
        # Add context data if provided
        if extra_data:
            # Sanitize extra data if needed
            if sanitize and self.config.enable_pii_detection:
                sanitized_extra = {}
                for key, value in extra_data.items():
                    if isinstance(value, str):
                        sanitized_extra[key] = self._sanitize_message(value)
                    else:
                        sanitized_extra[key] = value
                extra_data = sanitized_extra
            
            # Format extra data as JSON
            try:
                extra_json = json.dumps(extra_data, default=str, indent=None)
                message = f"{message} | Context: {extra_json}"
            except Exception:
                message = f"{message} | Context: {extra_data}"
        
        self.logger.log(level, message)
    
    def debug(self, message: str, extra_data: Dict = None, sanitize: bool = True):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, extra_data, sanitize)
    
    def info(self, message: str, extra_data: Dict = None, sanitize: bool = True):
        """Log info message."""
        self._log_with_context(logging.INFO, message, extra_data, sanitize)
    
    def warning(self, message: str, extra_data: Dict = None, sanitize: bool = True):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, extra_data, sanitize)
    
    def error(self, message: str, extra_data: Dict = None, sanitize: bool = True, 
              exc_info: bool = False):
        """Log error message."""
        if exc_info:
            self.logger.error(self._sanitize_message(message) if sanitize else message, 
                            exc_info=True)
        else:
            self._log_with_context(logging.ERROR, message, extra_data, sanitize)
    
    def critical(self, message: str, extra_data: Dict = None, sanitize: bool = True):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, extra_data, sanitize)
    
    def log_pii_detection(self, text: str, matches_found: int, sanitized: bool = False):
        """Log PII detection events."""
        if matches_found > 0:
            self.warning(
                f"PII detected in content: {matches_found} matches found",
                extra_data={
                    "pii_matches": matches_found,
                    "content_sanitized": sanitized,
                    "content_length": len(text),
                    "timestamp": datetime.now().isoformat()
                },
                sanitize=True  # Always sanitize PII detection logs
            )
    
    def log_api_request(self, endpoint: str, method: str, status_code: int, 
                       response_time: float, user_id: str = None):
        """Log API request with privacy protection."""
        # Sanitize user_id if provided
        safe_user_id = None
        if user_id:
            safe_user_id = self._sanitize_message(user_id) if self.config.enable_pii_detection else user_id
        
        self.info(
            f"API Request: {method} {endpoint}",
            extra_data={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time_ms": round(response_time * 1000, 2),
                "user_id": safe_user_id,
                "timestamp": datetime.now().isoformat()
            },
            sanitize=False  # Already sanitized above
        )
    
    def log_processing_event(self, event_type: str, url: str, success: bool, 
                           processing_time: float, error_message: str = None):
        """Log content processing events."""
        # Sanitize URL and error message
        safe_url = self._sanitize_message(url) if self.config.enable_pii_detection else url
        safe_error = None
        if error_message:
            safe_error = self._sanitize_message(error_message) if self.config.enable_pii_detection else error_message
        
        level = logging.INFO if success else logging.ERROR
        message = f"Processing {event_type}: {'SUCCESS' if success else 'FAILED'}"
        
        self._log_with_context(
            level,
            message,
            extra_data={
                "event_type": event_type,
                "url": safe_url,
                "success": success,
                "processing_time_seconds": round(processing_time, 2),
                "error_message": safe_error,
                "timestamp": datetime.now().isoformat()
            },
            sanitize=False  # Already sanitized above
        )
    
    def log_security_event(self, event_type: str, severity: str, description: str, 
                          source_ip: str = None, user_agent: str = None):
        """Log security-related events."""
        # Sanitize potentially sensitive data
        safe_ip = None
        safe_user_agent = None
        
        if source_ip and self.config.enable_pii_detection:
            safe_ip = self._sanitize_message(source_ip)
        else:
            safe_ip = source_ip
        
        if user_agent and self.config.enable_pii_detection:
            safe_user_agent = self._sanitize_message(user_agent)
        else:
            safe_user_agent = user_agent
        
        level = logging.CRITICAL if severity == "high" else logging.WARNING
        
        self._log_with_context(
            level,
            f"Security Event: {event_type}",
            extra_data={
                "event_type": event_type,
                "severity": severity,
                "description": description,
                "source_ip": safe_ip,
                "user_agent": safe_user_agent,
                "timestamp": datetime.now().isoformat()
            },
            sanitize=False  # Already sanitized above
        )


class PrivacyLoggerManager:
    """Manager for creating and configuring privacy-aware loggers."""
    
    _loggers = {}
    _config = None
    
    @classmethod
    def initialize(cls, config: Config):
        """Initialize the logger manager with configuration."""
        cls._config = config
    
    @classmethod
    def get_logger(cls, name: str) -> PrivacyLogger:
        """Get or create a privacy-aware logger."""
        if not cls._config:
            raise RuntimeError("PrivacyLoggerManager not initialized. Call initialize() first.")
        
        if name not in cls._loggers:
            cls._loggers[name] = PrivacyLogger(name, cls._config)
        
        return cls._loggers[name]
    
    @classmethod
    def get_standard_logger(cls, name: str) -> logging.Logger:
        """Get a standard Python logger (for compatibility)."""
        privacy_logger = cls.get_logger(name)
        return privacy_logger.logger


# Convenience functions
def get_privacy_logger(name: str, config: Config = None) -> PrivacyLogger:
    """Get a privacy-aware logger instance."""
    if config:
        PrivacyLoggerManager.initialize(config)
    
    return PrivacyLoggerManager.get_logger(name)


def setup_privacy_logging(config: Config):
    """Set up privacy-aware logging for the entire application."""
    PrivacyLoggerManager.initialize(config)
    
    # Configure root logger to use privacy-safe formatter
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add privacy-safe console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(PIISafeFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        sanitize_pii=config.enable_pii_detection
    ))
    
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(log_level)


# Example usage and testing
if __name__ == "__main__":
    # Test the privacy logger
    from .config import Config
    
    # Create test config
    test_config = Config(
        gemini_api_key="test_key",
        enable_pii_detection=True,
        sanitize_content=True,
        log_level="DEBUG"
    )
    
    # Test logger
    logger = get_privacy_logger("test", test_config)
    
    # Test with PII
    logger.info("User john.doe@example.com logged in from 192.168.1.100")
    logger.warning("Failed login attempt for user with phone 555-123-4567")
    logger.error("Credit card 4111-1111-1111-1111 validation failed")
    
    print("Privacy logging test completed!")