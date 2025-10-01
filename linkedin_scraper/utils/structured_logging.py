"""
Structured logging system for the LinkedIn Knowledge Management System.
"""

import json
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import structlog
from structlog.stdlib import LoggerFactory

from .config import Config
from .pii_detector import detect_and_sanitize_pii


class PIISafeProcessor:
    """Structlog processor that sanitizes PII from log messages."""
    
    def __init__(self, enable_pii_detection: bool = True):
        self.enable_pii_detection = enable_pii_detection
    
    def __call__(self, logger, method_name, event_dict):
        """Process log event and sanitize PII."""
        if not self.enable_pii_detection:
            return event_dict
        
        # Sanitize the main message
        if 'event' in event_dict:
            try:
                sanitized_text, _ = detect_and_sanitize_pii(
                    str(event_dict['event']), 
                    strategy="mask", 
                    min_confidence=0.6
                )
                event_dict['event'] = sanitized_text
            except Exception:
                pass  # If sanitization fails, keep original
        
        # Sanitize other string fields
        for key, value in event_dict.items():
            if isinstance(value, str) and key not in ['timestamp', 'level', 'logger']:
                try:
                    sanitized_text, _ = detect_and_sanitize_pii(
                        value, 
                        strategy="mask", 
                        min_confidence=0.6
                    )
                    event_dict[key] = sanitized_text
                except Exception:
                    pass  # If sanitization fails, keep original
        
        return event_dict


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class StructuredLogger:
    """Structured logger with PII sanitization and multiple output formats."""
    
    def __init__(self, name: str, config: Config):
        self.name = name
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Set up structured logger with processors and formatters."""
        # Configure structlog
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        
        # Add PII sanitization if enabled
        if self.config.enable_pii_detection:
            processors.append(PIISafeProcessor(True))
        
        # Add JSON processor for structured output
        if self.config.environment == 'production':
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Get the logger
        logger = structlog.get_logger(self.name)
        
        # Configure standard library logging
        self._configure_stdlib_logging()
        
        return logger
    
    def _configure_stdlib_logging(self):
        """Configure standard library logging handlers."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Set log level
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        root_logger.setLevel(log_level)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        
        if self.config.environment == 'production':
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
        
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)
        
        # File handler (if enabled)
        if self.config.enable_file_logging:
            try:
                log_path = Path(self.config.log_file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    filename=self.config.log_file_path,
                    maxBytes=self.config.max_log_file_size_mb * 1024 * 1024,
                    backupCount=5,
                    encoding='utf-8'
                )
                
                file_handler.setFormatter(JSONFormatter())
                file_handler.setLevel(log_level)
                root_logger.addHandler(file_handler)
                
            except Exception as e:
                console_handler.handle(
                    logging.LogRecord(
                        name=self.name,
                        level=logging.WARNING,
                        pathname="",
                        lineno=0,
                        msg=f"Failed to setup file logging: {e}",
                        args=(),
                        exc_info=None
                    )
                )
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, **kwargs)
    
    def log_request(self, method: str, path: str, status_code: int, 
                   response_time: float, user_id: str = None, **kwargs):
        """Log HTTP request with structured data."""
        self.logger.info(
            "HTTP request processed",
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=round(response_time * 1000, 2),
            user_id=user_id,
            **kwargs
        )
    
    def log_business_event(self, event_type: str, description: str, **kwargs):
        """Log business event with structured data."""
        self.logger.info(
            "Business event",
            event_type=event_type,
            description=description,
            **kwargs
        )
    
    def log_security_event(self, event_type: str, severity: str, description: str,
                          source_ip: str = None, user_agent: str = None, **kwargs):
        """Log security event with structured data."""
        level_map = {
            'low': self.logger.info,
            'medium': self.logger.warning,
            'high': self.logger.error,
            'critical': self.logger.critical
        }
        
        log_func = level_map.get(severity.lower(), self.logger.warning)
        
        log_func(
            "Security event",
            event_type=event_type,
            severity=severity,
            description=description,
            source_ip=source_ip,
            user_agent=user_agent,
            **kwargs
        )
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = None, **kwargs):
        """Log performance metric."""
        self.logger.info(
            "Performance metric",
            metric_name=metric_name,
            value=value,
            unit=unit,
            **kwargs
        )
    
    def log_pii_detection(self, content_type: str, matches_found: int, 
                         sanitized: bool = False, **kwargs):
        """Log PII detection event."""
        self.logger.warning(
            "PII detection event",
            content_type=content_type,
            matches_found=matches_found,
            sanitized=sanitized,
            **kwargs
        )
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with full context information."""
        self.logger.error(
            f"Error occurred: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {},
            exc_info=True
        )


class LogAggregator:
    """Aggregates and analyzes log data for insights."""
    
    def __init__(self, config: Config):
        self.config = config
        self.log_buffer = []
        self.max_buffer_size = 1000
        self.error_counts = {}
        self.performance_metrics = {}
        self.security_events = []
    
    def add_log_entry(self, log_entry: Dict[str, Any]):
        """Add log entry to buffer for analysis."""
        self.log_buffer.append(log_entry)
        
        # Keep buffer size manageable
        if len(self.log_buffer) > self.max_buffer_size:
            self.log_buffer = self.log_buffer[-self.max_buffer_size:]
        
        # Analyze log entry
        self._analyze_log_entry(log_entry)
    
    def _analyze_log_entry(self, log_entry: Dict[str, Any]):
        """Analyze individual log entry for patterns."""
        level = log_entry.get('level', '').lower()
        
        # Count errors
        if level in ['error', 'critical']:
            error_type = log_entry.get('error_type', 'unknown')
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Track performance metrics
        if 'response_time_ms' in log_entry:
            endpoint = log_entry.get('path', 'unknown')
            if endpoint not in self.performance_metrics:
                self.performance_metrics[endpoint] = []
            self.performance_metrics[endpoint].append(log_entry['response_time_ms'])
        
        # Track security events
        if log_entry.get('event_type') == 'security_event':
            self.security_events.append({
                'timestamp': log_entry.get('timestamp'),
                'severity': log_entry.get('severity'),
                'description': log_entry.get('description')
            })
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary from log analysis."""
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_types': dict(sorted(
                self.error_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )),
            'most_common_error': max(
                self.error_counts.items(), 
                key=lambda x: x[1]
            )[0] if self.error_counts else None
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary from log analysis."""
        summary = {}
        
        for endpoint, times in self.performance_metrics.items():
            if times:
                summary[endpoint] = {
                    'avg_response_time': sum(times) / len(times),
                    'max_response_time': max(times),
                    'min_response_time': min(times),
                    'request_count': len(times)
                }
        
        return summary
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security events summary."""
        if not self.security_events:
            return {'total_events': 0, 'severity_distribution': {}}
        
        severity_counts = {}
        for event in self.security_events:
            severity = event.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_events': len(self.security_events),
            'severity_distribution': severity_counts,
            'recent_events': self.security_events[-5:]  # Last 5 events
        }


# Global instances
_structured_loggers: Dict[str, StructuredLogger] = {}
_log_aggregator: Optional[LogAggregator] = None


def get_structured_logger(name: str, config: Config) -> StructuredLogger:
    """Get or create a structured logger instance."""
    if name not in _structured_loggers:
        _structured_loggers[name] = StructuredLogger(name, config)
    
    return _structured_loggers[name]


def initialize_log_aggregator(config: Config) -> LogAggregator:
    """Initialize the log aggregator."""
    global _log_aggregator
    _log_aggregator = LogAggregator(config)
    return _log_aggregator


def get_log_aggregator() -> Optional[LogAggregator]:
    """Get the log aggregator instance."""
    return _log_aggregator


# Convenience functions
def setup_structured_logging(config: Config):
    """Set up structured logging for the entire application."""
    # Initialize log aggregator
    initialize_log_aggregator(config)
    
    # Configure structlog globally
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if config.enable_pii_detection:
        processors.append(PIISafeProcessor(True))
    
    if config.environment == 'production':
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )