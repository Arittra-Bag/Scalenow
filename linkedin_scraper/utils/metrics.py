"""
Metrics collection and monitoring for the LinkedIn Knowledge Management System.
"""

import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server

from .config import Config
from .privacy_logger import get_privacy_logger


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    uptime_seconds: float
    timestamp: str


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    active_connections: int
    queue_size: int
    knowledge_items_processed: int
    pii_detections: int
    cache_hits: int
    cache_misses: int
    timestamp: str


class MetricsCollector:
    """Collects and manages application and system metrics."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_privacy_logger(__name__, config)
        self.start_time = time.time()
        
        # Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Internal metrics storage
        self.request_times = deque(maxlen=1000)  # Last 1000 request times
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.pii_detection_count = 0
        self.knowledge_items_count = 0
        self.cache_stats = {"hits": 0, "misses": 0}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Start metrics server if enabled
        if config.enable_metrics_collection:
            self._start_metrics_server()
    
    def _setup_prometheus_metrics(self):
        """Set up Prometheus metrics."""
        # Request metrics
        self.request_counter = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint']
        )
        
        # Application metrics
        self.pii_detections = Counter(
            'pii_detections_total',
            'Total PII detections'
        )
        
        self.knowledge_items = Counter(
            'knowledge_items_processed_total',
            'Total knowledge items processed'
        )
        
        self.processing_queue_size = Gauge(
            'processing_queue_size',
            'Current processing queue size'
        )
        
        self.cache_operations = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation']  # hit, miss
        )
        
        # System metrics
        self.system_cpu_percent = Gauge(
            'system_cpu_percent',
            'System CPU usage percentage'
        )
        
        self.system_memory_percent = Gauge(
            'system_memory_percent',
            'System memory usage percentage'
        )
        
        self.system_disk_percent = Gauge(
            'system_disk_percent',
            'System disk usage percentage'
        )
        
        # Application info
        self.app_info = Info(
            'linkedin_kms_info',
            'LinkedIn Knowledge Management System information'
        )
        
        self.app_info.info({
            'version': '1.0.0',
            'environment': self.config.environment,
            'pii_detection_enabled': str(self.config.enable_pii_detection),
            'content_sanitization_enabled': str(self.config.sanitize_content)
        })
    
    def _start_metrics_server(self):
        """Start Prometheus metrics server."""
        try:
            # Start on port 8001 (different from main app)
            start_http_server(8001)
            self.logger.info("Metrics server started on port 8001")
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}")
    
    def record_request(self, method: str, endpoint: str, status_code: int, 
                      response_time: float):
        """Record HTTP request metrics."""
        with self._lock:
            # Prometheus metrics
            self.request_counter.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code)
            ).inc()
            
            self.request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_time)
            
            # Internal metrics
            self.request_times.append(response_time)
            self.request_counts[f"{method}:{endpoint}"] += 1
            
            if status_code >= 400:
                self.error_counts[f"{method}:{endpoint}:{status_code}"] += 1
    
    def record_pii_detection(self, count: int = 1):
        """Record PII detection event."""
        with self._lock:
            self.pii_detections.inc(count)
            self.pii_detection_count += count
    
    def record_knowledge_item_processed(self, count: int = 1):
        """Record knowledge item processing."""
        with self._lock:
            self.knowledge_items.inc(count)
            self.knowledge_items_count += count
    
    def record_cache_operation(self, operation: str):
        """Record cache operation (hit/miss)."""
        with self._lock:
            self.cache_operations.labels(operation=operation).inc()
            self.cache_stats[operation + "s"] += 1
    
    def update_queue_size(self, size: int):
        """Update processing queue size."""
        self.processing_queue_size.set(size)
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / 1024 / 1024
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / 1024 / 1024 / 1024
            
            # Uptime
            uptime_seconds = time.time() - self.start_time
            
            # Update Prometheus gauges
            self.system_cpu_percent.set(cpu_percent)
            self.system_memory_percent.set(memory_percent)
            self.system_disk_percent.set(disk_usage_percent)
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                uptime_seconds=uptime_seconds,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                uptime_seconds=0.0,
                timestamp=datetime.now().isoformat()
            )
    
    def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics."""
        with self._lock:
            total_requests = sum(self.request_counts.values())
            failed_requests = sum(self.error_counts.values())
            successful_requests = total_requests - failed_requests
            
            # Calculate average response time
            avg_response_time = 0.0
            if self.request_times:
                avg_response_time = sum(self.request_times) / len(self.request_times)
            
            return ApplicationMetrics(
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                avg_response_time=avg_response_time,
                active_connections=0,  # Would need to be tracked separately
                queue_size=0,  # Would be updated by queue manager
                knowledge_items_processed=self.knowledge_items_count,
                pii_detections=self.pii_detection_count,
                cache_hits=self.cache_stats["hits"],
                cache_misses=self.cache_stats["misses"],
                timestamp=datetime.now().isoformat()
            )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        system_metrics = self.get_system_metrics()
        app_metrics = self.get_application_metrics()
        
        return {
            "system": asdict(system_metrics),
            "application": asdict(app_metrics),
            "health_status": self._get_health_status(system_metrics, app_metrics),
            "collection_timestamp": datetime.now().isoformat()
        }
    
    def _get_health_status(self, system: SystemMetrics, app: ApplicationMetrics) -> str:
        """Determine overall health status."""
        # Check system resources
        if system.cpu_percent > 90 or system.memory_percent > 90:
            return "critical"
        
        if system.cpu_percent > 70 or system.memory_percent > 70:
            return "warning"
        
        # Check error rate
        if app.total_requests > 0:
            error_rate = app.failed_requests / app.total_requests
            if error_rate > 0.1:  # More than 10% errors
                return "warning"
            if error_rate > 0.2:  # More than 20% errors
                return "critical"
        
        # Check response time
        if app.avg_response_time > 5.0:  # More than 5 seconds
            return "warning"
        if app.avg_response_time > 10.0:  # More than 10 seconds
            return "critical"
        
        return "healthy"
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        # This would typically be handled by the prometheus_client library
        # but we can provide a custom export if needed
        metrics = self.get_metrics_summary()
        
        lines = []
        lines.append("# LinkedIn Knowledge Management System Metrics")
        lines.append(f"# Generated at {datetime.now().isoformat()}")
        lines.append("")
        
        # System metrics
        sys_metrics = metrics["system"]
        lines.append(f"system_cpu_percent {sys_metrics['cpu_percent']}")
        lines.append(f"system_memory_percent {sys_metrics['memory_percent']}")
        lines.append(f"system_disk_percent {sys_metrics['disk_usage_percent']}")
        lines.append(f"system_uptime_seconds {sys_metrics['uptime_seconds']}")
        lines.append("")
        
        # Application metrics
        app_metrics = metrics["application"]
        lines.append(f"http_requests_total {app_metrics['total_requests']}")
        lines.append(f"http_requests_successful {app_metrics['successful_requests']}")
        lines.append(f"http_requests_failed {app_metrics['failed_requests']}")
        lines.append(f"http_response_time_avg {app_metrics['avg_response_time']}")
        lines.append(f"knowledge_items_processed {app_metrics['knowledge_items_processed']}")
        lines.append(f"pii_detections_total {app_metrics['pii_detections']}")
        lines.append(f"cache_hits_total {app_metrics['cache_hits']}")
        lines.append(f"cache_misses_total {app_metrics['cache_misses']}")
        
        return "\n".join(lines)
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.request_times.clear()
            self.request_counts.clear()
            self.error_counts.clear()
            self.pii_detection_count = 0
            self.knowledge_items_count = 0
            self.cache_stats = {"hits": 0, "misses": 0}
            
            self.logger.info("Metrics reset")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def initialize_metrics(config: Config) -> MetricsCollector:
    """Initialize the global metrics collector."""
    global _metrics_collector
    _metrics_collector = MetricsCollector(config)
    return _metrics_collector


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector instance."""
    return _metrics_collector


# Convenience functions
def record_request_metric(method: str, endpoint: str, status_code: int, response_time: float):
    """Record a request metric."""
    if _metrics_collector:
        _metrics_collector.record_request(method, endpoint, status_code, response_time)


def record_pii_detection_metric(count: int = 1):
    """Record PII detection metric."""
    if _metrics_collector:
        _metrics_collector.record_pii_detection(count)


def record_knowledge_item_metric(count: int = 1):
    """Record knowledge item processing metric."""
    if _metrics_collector:
        _metrics_collector.record_knowledge_item_processed(count)


def record_cache_metric(operation: str):
    """Record cache operation metric."""
    if _metrics_collector:
        _metrics_collector.record_cache_operation(operation)


def update_queue_size_metric(size: int):
    """Update queue size metric."""
    if _metrics_collector:
        _metrics_collector.update_queue_size(size)