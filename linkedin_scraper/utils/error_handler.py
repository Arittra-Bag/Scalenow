"""
Comprehensive error handling system for LinkedIn Knowledge Scraper.
Provides centralized error handling, recovery mechanisms, and error reporting.
"""

import logging
import traceback
from typing import Optional, Dict, Any, Callable, Type
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import asyncio


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    API = "api"
    CONFIGURATION = "configuration"
    DATA_PROCESSING = "data_processing"
    STORAGE = "storage"
    AUTHENTICATION = "authentication"
    RATE_LIMITING = "rate_limiting"
    VALIDATION = "validation"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors."""
    component: str
    operation: str
    url: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class ErrorInfo:
    """Comprehensive error information."""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception_type: str
    traceback: str
    context: ErrorContext
    retry_count: int = 0
    resolved: bool = False


class ScraperError(Exception):
    """Base exception for scraper-specific errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.original_exception = original_exception


class NetworkError(ScraperError):
    """Network-related errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context
        )


class APIError(ScraperError):
    """API-related errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            context=context
        )
        self.status_code = status_code


class ConfigurationError(ScraperError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            context=context
        )


class DataProcessingError(ScraperError):
    """Data processing errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            category=ErrorCategory.DATA_PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            context=context
        )


class StorageError(ScraperError):
    """Storage-related errors."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message,
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.HIGH,
            context=context
        )


class RateLimitError(ScraperError):
    """Rate limiting errors."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message,
            category=ErrorCategory.RATE_LIMITING,
            severity=ErrorSeverity.MEDIUM,
            context=context
        )
        self.retry_after = retry_after


class ErrorHandler:
    """Centralized error handling system."""
    
    def __init__(self, config=None):
        """Initialize error handler."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.error_history: Dict[str, ErrorInfo] = {}
        self.error_callbacks: Dict[ErrorCategory, list] = {}
        self.retry_strategies: Dict[ErrorCategory, Callable] = {}
        
        # Set up default retry strategies
        self._setup_default_retry_strategies()
    
    def _setup_default_retry_strategies(self):
        """Set up default retry strategies for different error categories."""
        
        async def network_retry_strategy(error_info: ErrorInfo, max_retries: int = 3) -> bool:
            """Retry strategy for network errors."""
            if error_info.retry_count >= max_retries:
                return False
            
            # Exponential backoff
            delay = min(2 ** error_info.retry_count, 60)
            await asyncio.sleep(delay)
            return True
        
        async def api_retry_strategy(error_info: ErrorInfo, max_retries: int = 2) -> bool:
            """Retry strategy for API errors."""
            if error_info.retry_count >= max_retries:
                return False
            
            # Check if it's a retryable API error
            if hasattr(error_info, 'status_code'):
                # Don't retry client errors (4xx)
                if 400 <= error_info.status_code < 500:
                    return False
            
            delay = min(5 * (error_info.retry_count + 1), 30)
            await asyncio.sleep(delay)
            return True
        
        async def rate_limit_retry_strategy(error_info: ErrorInfo, max_retries: int = 5) -> bool:
            """Retry strategy for rate limit errors."""
            if error_info.retry_count >= max_retries:
                return False
            
            # Use retry_after if available, otherwise exponential backoff
            if hasattr(error_info, 'retry_after') and error_info.retry_after:
                delay = error_info.retry_after
            else:
                delay = min(10 * (2 ** error_info.retry_count), 300)  # Max 5 minutes
            
            await asyncio.sleep(delay)
            return True
        
        self.retry_strategies = {
            ErrorCategory.NETWORK: network_retry_strategy,
            ErrorCategory.API: api_retry_strategy,
            ErrorCategory.RATE_LIMITING: rate_limit_retry_strategy
        }
    
    def register_error_callback(self, category: ErrorCategory, callback: Callable):
        """Register callback for specific error category."""
        if category not in self.error_callbacks:
            self.error_callbacks[category] = []
        self.error_callbacks[category].append(callback)
    
    def handle_error(
        self,
        exception: Exception,
        context: Optional[ErrorContext] = None,
        severity: Optional[ErrorSeverity] = None
    ) -> ErrorInfo:
        """
        Handle an error and create error information.
        
        Args:
            exception: The exception that occurred
            context: Context information about the error
            severity: Override severity level
            
        Returns:
            ErrorInfo object with error details
        """
        # Generate unique error ID
        error_id = f"err_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(exception)}"
        
        # Determine error category and severity
        if isinstance(exception, ScraperError):
            category = exception.category
            severity = severity or exception.severity
            message = exception.message
        else:
            category = self._classify_exception(exception)
            severity = severity or self._determine_severity(exception, category)
            message = str(exception)
        
        # Create error info
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            message=message,
            exception_type=type(exception).__name__,
            traceback=traceback.format_exc(),
            context=context or ErrorContext(component="unknown", operation="unknown")
        )
        
        # Store error
        self.error_history[error_id] = error_info
        
        # Log error
        self._log_error(error_info)
        
        # Execute callbacks
        self._execute_callbacks(error_info)
        
        return error_info
    
    def _classify_exception(self, exception: Exception) -> ErrorCategory:
        """Classify exception into error category."""
        exception_name = type(exception).__name__.lower()
        
        if any(keyword in exception_name for keyword in ['network', 'connection', 'timeout', 'dns']):
            return ErrorCategory.NETWORK
        elif any(keyword in exception_name for keyword in ['http', 'api', 'request', 'response']):
            return ErrorCategory.API
        elif any(keyword in exception_name for keyword in ['config', 'setting', 'parameter']):
            return ErrorCategory.CONFIGURATION
        elif any(keyword in exception_name for keyword in ['data', 'parse', 'json', 'xml']):
            return ErrorCategory.DATA_PROCESSING
        elif any(keyword in exception_name for keyword in ['storage', 'database', 'file', 'io']):
            return ErrorCategory.STORAGE
        elif any(keyword in exception_name for keyword in ['auth', 'permission', 'credential']):
            return ErrorCategory.AUTHENTICATION
        elif any(keyword in exception_name for keyword in ['rate', 'limit', 'quota']):
            return ErrorCategory.RATE_LIMITING
        elif any(keyword in exception_name for keyword in ['validation', 'value', 'type']):
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on exception and category."""
        if category == ErrorCategory.CRITICAL:
            return ErrorSeverity.CRITICAL
        elif category in [ErrorCategory.CONFIGURATION, ErrorCategory.AUTHENTICATION]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.API, ErrorCategory.STORAGE]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.NETWORK, ErrorCategory.RATE_LIMITING]:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error information."""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }[error_info.severity]
        
        log_message = (
            f"Error {error_info.error_id}: {error_info.message} "
            f"[{error_info.category.value}] in {error_info.context.component}::{error_info.context.operation}"
        )
        
        if error_info.context.url:
            log_message += f" (URL: {error_info.context.url})"
        
        self.logger.log(log_level, log_message)
        
        # Log full traceback for high severity errors
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.debug(f"Full traceback for {error_info.error_id}:\n{error_info.traceback}")
    
    def _execute_callbacks(self, error_info: ErrorInfo):
        """Execute registered callbacks for error category."""
        callbacks = self.error_callbacks.get(error_info.category, [])
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")
    
    async def should_retry(self, error_info: ErrorInfo) -> bool:
        """
        Determine if an operation should be retried based on error info.
        
        Args:
            error_info: Error information
            
        Returns:
            True if should retry, False otherwise
        """
        retry_strategy = self.retry_strategies.get(error_info.category)
        if not retry_strategy:
            return False
        
        try:
            return await retry_strategy(error_info)
        except Exception as e:
            self.logger.error(f"Error in retry strategy: {e}")
            return False
    
    async def retry_with_backoff(
        self,
        operation: Callable,
        context: ErrorContext,
        max_retries: int = 3,
        *args,
        **kwargs
    ):
        """
        Execute operation with automatic retry and backoff.
        
        Args:
            operation: Async function to execute
            context: Error context for logging
            max_retries: Maximum number of retries
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of successful operation
            
        Raises:
            Last exception if all retries failed
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_info = self.handle_error(e, context)
                error_info.retry_count = attempt
                
                if attempt < max_retries:
                    should_retry = await self.should_retry(error_info)
                    if should_retry:
                        self.logger.info(
                            f"Retrying operation {context.operation} "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        continue
                
                # Don't retry or max retries reached
                break
        
        # All retries failed
        raise last_exception
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with error statistics
        """
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        recent_errors = [
            error for error in self.error_history.values()
            if error.timestamp.timestamp() > cutoff_time
        ]
        
        # Count by category
        category_counts = {}
        for error in recent_errors:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for error in recent_errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_errors": len(recent_errors),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "critical_errors": [
                error.error_id for error in recent_errors
                if error.severity == ErrorSeverity.CRITICAL
            ],
            "time_period_hours": hours
        }
    
    def clear_error_history(self, older_than_hours: int = 168):  # 1 week default
        """Clear old errors from history."""
        cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
        
        errors_to_remove = [
            error_id for error_id, error_info in self.error_history.items()
            if error_info.timestamp.timestamp() < cutoff_time
        ]
        
        for error_id in errors_to_remove:
            del self.error_history[error_id]
        
        self.logger.info(f"Cleared {len(errors_to_remove)} old errors from history")


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler(config=None) -> ErrorHandler:
    """Get global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(config)
    return _global_error_handler


def handle_error(
    exception: Exception,
    context: Optional[ErrorContext] = None,
    severity: Optional[ErrorSeverity] = None
) -> ErrorInfo:
    """Convenience function to handle errors using global handler."""
    return get_error_handler().handle_error(exception, context, severity)


async def retry_with_backoff(
    operation: Callable,
    context: ErrorContext,
    max_retries: int = 3,
    *args,
    **kwargs
):
    """Convenience function for retry with backoff using global handler."""
    return await get_error_handler().retry_with_backoff(
        operation, context, max_retries, *args, **kwargs
    )