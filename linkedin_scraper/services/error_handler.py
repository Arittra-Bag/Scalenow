"""Error handling and recovery service for robust processing."""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Type, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path

from ..models.exceptions import (
    LinkedInKMSError, ScrapingError, ProcessingError, 
    StorageError, APIError, ValidationError, ConfigurationError
)
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Recovery actions for different error types."""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    FALLBACK = "fallback"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    id: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    occurred_at: datetime
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    recovery_action: Optional[RecoveryAction] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error record to dictionary."""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['occurred_at'] = self.occurred_at.isoformat()
        data['recovery_action'] = self.recovery_action.value if self.recovery_action else None
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorRecord':
        """Create error record from dictionary."""
        data = data.copy()
        data['severity'] = ErrorSeverity(data['severity'])
        data['occurred_at'] = datetime.fromisoformat(data['occurred_at'])
        data['recovery_action'] = RecoveryAction(data['recovery_action']) if data['recovery_action'] else None
        data['resolved_at'] = datetime.fromisoformat(data['resolved_at']) if data['resolved_at'] else None
        return cls(**data)


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_backoff: bool = True
    jitter: bool = True  # Add random jitter to delays
    
    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for a retry attempt."""
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** retry_count)
        else:
            delay = self.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
        
        return delay


class ErrorHandler:
    """Comprehensive error handling and recovery service."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the error handler."""
        self.config = config or Config.from_env()
        
        # Error tracking
        self.error_records: Dict[str, ErrorRecord] = {}
        self.error_counts: Dict[str, int] = {}
        self.error_patterns: Dict[str, List[str]] = {}
        
        # Recovery policies
        self.retry_policies: Dict[Type[Exception], RetryPolicy] = {
            ScrapingError: RetryPolicy(max_retries=3, base_delay=2.0, max_delay=30.0),
            APIError: RetryPolicy(max_retries=5, base_delay=1.0, max_delay=60.0),
            ProcessingError: RetryPolicy(max_retries=2, base_delay=1.0, max_delay=10.0),
            StorageError: RetryPolicy(max_retries=3, base_delay=0.5, max_delay=5.0),
            ValidationError: RetryPolicy(max_retries=1, base_delay=0.1, max_delay=1.0),
            Exception: RetryPolicy(max_retries=2, base_delay=1.0, max_delay=10.0)  # Default
        }
        
        # Error severity mapping
        self.severity_mapping: Dict[Type[Exception], ErrorSeverity] = {
            ConfigurationError: ErrorSeverity.CRITICAL,
            APIError: ErrorSeverity.HIGH,
            ScrapingError: ErrorSeverity.MEDIUM,
            ProcessingError: ErrorSeverity.MEDIUM,
            StorageError: ErrorSeverity.HIGH,
            ValidationError: ErrorSeverity.LOW,
            Exception: ErrorSeverity.MEDIUM  # Default
        }
        
        # Recovery action mapping
        self.recovery_mapping: Dict[Type[Exception], RecoveryAction] = {
            ConfigurationError: RecoveryAction.ABORT,
            APIError: RecoveryAction.RETRY,
            ScrapingError: RecoveryAction.RETRY,
            ProcessingError: RecoveryAction.FALLBACK,
            StorageError: RecoveryAction.RETRY,
            ValidationError: RecoveryAction.SKIP,
            Exception: RecoveryAction.RETRY  # Default
        }
        
        # Error log file
        self.error_log_file = Path(self.config.knowledge_repo_path) / "error_log.json"
        
        # Load existing error records
        self._load_error_records()
        
        logger.info("Error handler initialized")
    
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        operation: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Tuple[bool, Any]:
        """Handle an error with appropriate recovery action."""
        try:
            # Create error record
            error_record = self._create_error_record(error, context)
            
            # Log the error
            self._log_error(error_record)
            
            # Determine recovery action
            recovery_action = self._determine_recovery_action(error, error_record)
            error_record.recovery_action = recovery_action
            
            # Execute recovery action
            success, result = await self._execute_recovery_action(
                recovery_action, error, error_record, operation, *args, **kwargs
            )
            
            # Update error record
            error_record.recovery_attempted = True
            error_record.recovery_successful = success
            if success:
                error_record.resolved_at = datetime.now()
            
            # Store error record
            self.error_records[error_record.id] = error_record
            self._save_error_records()
            
            return success, result
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return False, None
    
    def _create_error_record(self, error: Exception, context: Dict[str, Any]) -> ErrorRecord:
        """Create an error record from an exception."""
        error_id = f"error_{int(datetime.now().timestamp() * 1000)}"
        error_type = type(error).__name__
        
        # Determine severity
        severity = self._get_error_severity(error)
        
        # Get stack trace
        stack_trace = traceback.format_exc()
        
        return ErrorRecord(
            id=error_id,
            error_type=error_type,
            error_message=str(error),
            severity=severity,
            occurred_at=datetime.now(),
            context=context,
            stack_trace=stack_trace
        )
    
    def _get_error_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on error type."""
        for error_type, severity in self.severity_mapping.items():
            if isinstance(error, error_type):
                return severity
        return ErrorSeverity.MEDIUM
    
    def _determine_recovery_action(self, error: Exception, error_record: ErrorRecord) -> RecoveryAction:
        """Determine the appropriate recovery action for an error."""
        # Check for specific error patterns
        error_message = str(error).lower()
        
        # Rate limiting errors
        if any(keyword in error_message for keyword in ['rate limit', 'quota', 'too many requests']):
            return RecoveryAction.RETRY
        
        # Network errors
        if any(keyword in error_message for keyword in ['network', 'connection', 'timeout', 'unreachable']):
            return RecoveryAction.RETRY
        
        # Authentication errors
        if any(keyword in error_message for keyword in ['unauthorized', 'forbidden', 'authentication']):
            return RecoveryAction.MANUAL_INTERVENTION
        
        # Data validation errors
        if any(keyword in error_message for keyword in ['invalid', 'malformed', 'validation']):
            return RecoveryAction.SKIP
        
        # Use default mapping
        for error_type, action in self.recovery_mapping.items():
            if isinstance(error, error_type):
                return action
        
        return RecoveryAction.RETRY
    
    async def _execute_recovery_action(
        self,
        action: RecoveryAction,
        error: Exception,
        error_record: ErrorRecord,
        operation: Optional[Callable],
        *args,
        **kwargs
    ) -> Tuple[bool, Any]:
        """Execute the determined recovery action."""
        try:
            if action == RecoveryAction.RETRY:
                return await self._retry_operation(error, error_record, operation, *args, **kwargs)
            
            elif action == RecoveryAction.SKIP:
                logger.info(f"Skipping operation due to error: {error_record.error_message}")
                return True, None
            
            elif action == RecoveryAction.ABORT:
                logger.error(f"Aborting due to critical error: {error_record.error_message}")
                return False, None
            
            elif action == RecoveryAction.FALLBACK:
                return await self._execute_fallback(error, error_record, operation, *args, **kwargs)
            
            elif action == RecoveryAction.MANUAL_INTERVENTION:
                logger.warning(f"Manual intervention required: {error_record.error_message}")
                return False, None
            
            else:
                logger.warning(f"Unknown recovery action: {action}")
                return False, None
                
        except Exception as e:
            logger.error(f"Recovery action failed: {e}")
            return False, None
    
    async def _retry_operation(
        self,
        error: Exception,
        error_record: ErrorRecord,
        operation: Optional[Callable],
        *args,
        **kwargs
    ) -> Tuple[bool, Any]:
        """Retry an operation with exponential backoff."""
        if not operation:
            return False, None
        
        # Get retry policy
        retry_policy = self._get_retry_policy(error)
        
        for retry_count in range(retry_policy.max_retries):
            try:
                # Calculate delay
                delay = retry_policy.calculate_delay(retry_count)
                
                if retry_count > 0:
                    logger.info(f"Retrying operation (attempt {retry_count + 1}/{retry_policy.max_retries}) after {delay:.1f}s delay")
                    await asyncio.sleep(delay)
                
                # Retry the operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Success
                error_record.retry_count = retry_count + 1
                logger.info(f"Operation succeeded on retry {retry_count + 1}")
                return True, result
                
            except Exception as retry_error:
                error_record.retry_count = retry_count + 1
                
                if retry_count == retry_policy.max_retries - 1:
                    # Final retry failed
                    logger.error(f"Operation failed after {retry_policy.max_retries} retries: {retry_error}")
                    return False, None
                else:
                    logger.warning(f"Retry {retry_count + 1} failed: {retry_error}")
        
        return False, None
    
    async def _execute_fallback(
        self,
        error: Exception,
        error_record: ErrorRecord,
        operation: Optional[Callable],
        *args,
        **kwargs
    ) -> Tuple[bool, Any]:
        """Execute fallback logic for an operation."""
        logger.info(f"Executing fallback for error: {error_record.error_message}")
        
        # Implement fallback strategies based on error type
        if isinstance(error, ProcessingError):
            # For processing errors, try rule-based processing instead of AI
            return await self._fallback_rule_based_processing(*args, **kwargs)
        
        elif isinstance(error, ScrapingError):
            # For scraping errors, try alternative scraping method
            return await self._fallback_simple_scraping(*args, **kwargs)
        
        else:
            # Generic fallback - return partial success
            logger.info("Using generic fallback - partial success")
            return True, {"fallback": True, "partial_result": True}
    
    async def _fallback_rule_based_processing(self, *args, **kwargs) -> Tuple[bool, Any]:
        """Fallback to rule-based processing when AI processing fails."""
        try:
            # This would integrate with your rule-based content processor
            logger.info("Falling back to rule-based content processing")
            
            # Simulate rule-based processing
            await asyncio.sleep(0.5)
            
            return True, {
                "processing_method": "rule_based",
                "fallback": True,
                "confidence": 0.7
            }
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return False, None
    
    async def _fallback_simple_scraping(self, *args, **kwargs) -> Tuple[bool, Any]:
        """Fallback to simple scraping when advanced scraping fails."""
        try:
            # This would integrate with a simpler scraping method
            logger.info("Falling back to simple scraping method")
            
            # Simulate simple scraping
            await asyncio.sleep(1.0)
            
            return True, {
                "scraping_method": "simple",
                "fallback": True,
                "limited_data": True
            }
            
        except Exception as e:
            logger.error(f"Fallback scraping failed: {e}")
            return False, None
    
    def _get_retry_policy(self, error: Exception) -> RetryPolicy:
        """Get retry policy for an error type."""
        for error_type, policy in self.retry_policies.items():
            if isinstance(error, error_type):
                return policy
        return self.retry_policies[Exception]  # Default policy
    
    def _log_error(self, error_record: ErrorRecord):
        """Log an error with appropriate level."""
        log_message = f"Error {error_record.id}: {error_record.error_message}"
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_record.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Update error counts
        error_type = error_record.error_type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)
        
        stats = {
            'total_errors': len(self.error_records),
            'error_counts_by_type': dict(self.error_counts),
            'errors_last_24h': 0,
            'errors_last_hour': 0,
            'severity_distribution': {},
            'recovery_success_rate': 0.0,
            'most_common_errors': [],
            'recent_critical_errors': []
        }
        
        # Analyze error records
        recovery_attempts = 0
        recovery_successes = 0
        severity_counts = {}
        recent_errors_24h = []
        recent_errors_1h = []
        
        for error_record in self.error_records.values():
            # Time-based counts
            if error_record.occurred_at >= last_24h:
                stats['errors_last_24h'] += 1
                recent_errors_24h.append(error_record)
            
            if error_record.occurred_at >= last_hour:
                stats['errors_last_hour'] += 1
                recent_errors_1h.append(error_record)
            
            # Severity distribution
            severity = error_record.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Recovery statistics
            if error_record.recovery_attempted:
                recovery_attempts += 1
                if error_record.recovery_successful:
                    recovery_successes += 1
            
            # Critical errors
            if error_record.severity == ErrorSeverity.CRITICAL:
                stats['recent_critical_errors'].append({
                    'id': error_record.id,
                    'message': error_record.error_message,
                    'occurred_at': error_record.occurred_at.isoformat()
                })
        
        stats['severity_distribution'] = severity_counts
        
        # Recovery success rate
        if recovery_attempts > 0:
            stats['recovery_success_rate'] = (recovery_successes / recovery_attempts) * 100
        
        # Most common errors
        sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)
        stats['most_common_errors'] = sorted_errors[:5]
        
        return stats
    
    def get_error_patterns(self) -> Dict[str, List[str]]:
        """Identify common error patterns."""
        patterns = {}
        
        for error_record in self.error_records.values():
            error_type = error_record.error_type
            error_message = error_record.error_message.lower()
            
            if error_type not in patterns:
                patterns[error_type] = []
            
            # Extract common patterns from error messages
            if 'timeout' in error_message:
                patterns[error_type].append('timeout')
            elif 'connection' in error_message:
                patterns[error_type].append('connection_issue')
            elif 'rate limit' in error_message:
                patterns[error_type].append('rate_limiting')
            elif 'unauthorized' in error_message:
                patterns[error_type].append('authentication')
            elif 'not found' in error_message:
                patterns[error_type].append('resource_not_found')
            else:
                patterns[error_type].append('other')
        
        # Remove duplicates and count occurrences
        for error_type in patterns:
            pattern_counts = {}
            for pattern in patterns[error_type]:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            patterns[error_type] = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
        
        return patterns
    
    def clear_old_errors(self, days_to_keep: int = 30) -> int:
        """Clear old error records."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        errors_to_remove = [
            error_id for error_id, error_record in self.error_records.items()
            if error_record.occurred_at < cutoff_date
        ]
        
        for error_id in errors_to_remove:
            del self.error_records[error_id]
        
        # Update error counts
        self.error_counts = {}
        for error_record in self.error_records.values():
            error_type = error_record.error_type
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        self._save_error_records()
        
        logger.info(f"Cleared {len(errors_to_remove)} old error records")
        return len(errors_to_remove)
    
    def _save_error_records(self):
        """Save error records to file."""
        try:
            error_data = {
                'error_records': {
                    error_id: error_record.to_dict()
                    for error_id, error_record in self.error_records.items()
                },
                'error_counts': self.error_counts,
                'saved_at': datetime.now().isoformat()
            }
            
            self.error_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save error records: {e}")
    
    def _load_error_records(self):
        """Load error records from file."""
        try:
            if not self.error_log_file.exists():
                return
            
            with open(self.error_log_file, 'r', encoding='utf-8') as f:
                error_data = json.load(f)
            
            # Load error records
            for error_id, error_dict in error_data.get('error_records', {}).items():
                try:
                    error_record = ErrorRecord.from_dict(error_dict)
                    self.error_records[error_id] = error_record
                except Exception as e:
                    logger.warning(f"Failed to load error record {error_id}: {e}")
            
            # Load error counts
            self.error_counts = error_data.get('error_counts', {})
            
            logger.info(f"Loaded {len(self.error_records)} error records")
            
        except Exception as e:
            logger.error(f"Failed to load error records: {e}")
    
    def export_error_report(self, output_path: str, include_stack_traces: bool = False) -> bool:
        """Export comprehensive error report."""
        try:
            report = {
                'report_generated': datetime.now().isoformat(),
                'statistics': self.get_error_statistics(),
                'error_patterns': self.get_error_patterns(),
                'error_records': []
            }
            
            # Add error records
            for error_record in self.error_records.values():
                record_dict = error_record.to_dict()
                if not include_stack_traces:
                    record_dict.pop('stack_trace', None)
                report['error_records'].append(record_dict)
            
            # Save report
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Error report exported to: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export error report: {e}")
            return False