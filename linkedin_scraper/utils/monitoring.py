"""
Monitoring and alerting system for the LinkedIn Knowledge Management System.
"""

import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
import time

from .config import Config
from .privacy_logger import get_privacy_logger
from .metrics import MetricsCollector, SystemMetrics, ApplicationMetrics


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    timestamp: datetime
    source: str
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_privacy_logger(__name__, config)
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._lock = threading.Lock()
    
    def create_alert(self, alert_id: str, title: str, description: str, 
                    severity: AlertSeverity, source: str = "system",
                    metadata: Dict[str, Any] = None) -> Alert:
        """Create a new alert."""
        alert = Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=severity,
            timestamp=datetime.now(),
            source=source,
            metadata=metadata or {}
        )
        
        with self._lock:
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
        
        # Send notifications
        self._send_notifications(alert)
        
        self.logger.warning(
            f"Alert created: {title}",
            extra_data={
                "alert_id": alert_id,
                "severity": severity.value,
                "source": source,
                "description": description
            }
        )
        
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = datetime.now()
                del self.active_alerts[alert_id]
                
                self.logger.info(
                    f"Alert resolved: {alert.title}",
                    extra_data={"alert_id": alert_id}
                )
                
                return True
        
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        with self._lock:
            return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                alert for alert in self.alert_history
                if alert.timestamp >= cutoff_time
            ]
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications via configured channels."""
        # Email notifications
        if self.config.enable_email_alerts:
            self._send_email_alert(alert)
        
        # Webhook notifications
        if self.config.enable_webhook_alerts:
            self._send_webhook_alert(alert)
    
    def _send_email_alert(self, alert: Alert):
        """Send email alert notification."""
        try:
            if not all([
                self.config.smtp_server,
                self.config.smtp_username,
                self.config.smtp_password,
                self.config.alert_email_to
            ]):
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_username
            msg['To'] = self.config.alert_email_to
            msg['Subject'] = f"[{alert.severity.value.upper()}] LinkedIn KMS Alert: {alert.title}"
            
            # Email body
            body = f"""
LinkedIn Knowledge Management System Alert

Alert ID: {alert.id}
Severity: {alert.severity.value.upper()}
Source: {alert.source}
Timestamp: {alert.timestamp.isoformat()}

Description:
{alert.description}

Metadata:
{json.dumps(alert.metadata, indent=2)}

---
This is an automated alert from the LinkedIn Knowledge Management System.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)
            
            self.logger.info(f"Email alert sent for {alert.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_alert(self, alert: Alert):
        """Send webhook alert notification."""
        try:
            if not self.config.webhook_url:
                return
            
            payload = {
                "alert_id": alert.id,
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity.value,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata
            }
            
            response = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            response.raise_for_status()
            self.logger.info(f"Webhook alert sent for {alert.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")


class HealthMonitor:
    """Monitors system health and triggers alerts."""
    
    def __init__(self, config: Config, metrics_collector: MetricsCollector, 
                 alert_manager: AlertManager):
        self.config = config
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        self.logger = get_privacy_logger(__name__, config)
        
        # Monitoring thresholds
        self.thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 90.0,
            "memory_warning": 70.0,
            "memory_critical": 90.0,
            "disk_warning": 80.0,
            "disk_critical": 95.0,
            "response_time_warning": 2.0,
            "response_time_critical": 5.0,
            "error_rate_warning": 0.05,  # 5%
            "error_rate_critical": 0.15,  # 15%
            "pii_detection_rate_warning": 10,  # per hour
            "queue_size_warning": 50,
            "queue_size_critical": 100
        }
        
        # Tracking for rate-based alerts
        self.last_check_time = datetime.now()
        self.last_pii_count = 0
        
        # Monitoring thread
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
    
    def start_monitoring(self):
        """Start the health monitoring thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        self.logger.info("Health monitoring started")
    
    def stop_monitoring_thread(self):
        """Stop the health monitoring thread."""
        self.stop_monitoring.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self.stop_monitoring.wait(self.config.health_check_interval_seconds):
            try:
                self.check_system_health()
                self.check_application_health()
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
    
    def check_system_health(self):
        """Check system resource health."""
        try:
            system_metrics = self.metrics_collector.get_system_metrics()
            
            # CPU usage alerts
            self._check_threshold_alert(
                "cpu_usage",
                system_metrics.cpu_percent,
                self.thresholds["cpu_warning"],
                self.thresholds["cpu_critical"],
                "High CPU Usage",
                f"CPU usage is {system_metrics.cpu_percent:.1f}%"
            )
            
            # Memory usage alerts
            self._check_threshold_alert(
                "memory_usage",
                system_metrics.memory_percent,
                self.thresholds["memory_warning"],
                self.thresholds["memory_critical"],
                "High Memory Usage",
                f"Memory usage is {system_metrics.memory_percent:.1f}% ({system_metrics.memory_used_mb:.1f}MB)"
            )
            
            # Disk usage alerts
            self._check_threshold_alert(
                "disk_usage",
                system_metrics.disk_usage_percent,
                self.thresholds["disk_warning"],
                self.thresholds["disk_critical"],
                "High Disk Usage",
                f"Disk usage is {system_metrics.disk_usage_percent:.1f}% ({system_metrics.disk_free_gb:.1f}GB free)"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to check system health: {e}")
    
    def check_application_health(self):
        """Check application-specific health."""
        try:
            app_metrics = self.metrics_collector.get_application_metrics()
            
            # Response time alerts
            if app_metrics.avg_response_time > 0:
                self._check_threshold_alert(
                    "response_time",
                    app_metrics.avg_response_time,
                    self.thresholds["response_time_warning"],
                    self.thresholds["response_time_critical"],
                    "High Response Time",
                    f"Average response time is {app_metrics.avg_response_time:.2f} seconds"
                )
            
            # Error rate alerts
            if app_metrics.total_requests > 0:
                error_rate = app_metrics.failed_requests / app_metrics.total_requests
                self._check_threshold_alert(
                    "error_rate",
                    error_rate,
                    self.thresholds["error_rate_warning"],
                    self.thresholds["error_rate_critical"],
                    "High Error Rate",
                    f"Error rate is {error_rate:.1%} ({app_metrics.failed_requests}/{app_metrics.total_requests})"
                )
            
            # PII detection rate alerts
            self._check_pii_detection_rate(app_metrics.pii_detections)
            
            # Queue size alerts (if available)
            if hasattr(app_metrics, 'queue_size') and app_metrics.queue_size > 0:
                self._check_threshold_alert(
                    "queue_size",
                    app_metrics.queue_size,
                    self.thresholds["queue_size_warning"],
                    self.thresholds["queue_size_critical"],
                    "Large Processing Queue",
                    f"Processing queue has {app_metrics.queue_size} items"
                )
            
        except Exception as e:
            self.logger.error(f"Failed to check application health: {e}")
    
    def _check_threshold_alert(self, alert_type: str, current_value: float,
                             warning_threshold: float, critical_threshold: float,
                             title: str, description: str):
        """Check threshold-based alerts."""
        alert_id = f"{alert_type}_alert"
        
        if current_value >= critical_threshold:
            if alert_id not in self.alert_manager.active_alerts:
                self.alert_manager.create_alert(
                    alert_id,
                    title,
                    description,
                    AlertSeverity.CRITICAL,
                    "health_monitor",
                    {"current_value": current_value, "threshold": critical_threshold}
                )
        elif current_value >= warning_threshold:
            if alert_id not in self.alert_manager.active_alerts:
                self.alert_manager.create_alert(
                    alert_id,
                    title,
                    description,
                    AlertSeverity.WARNING,
                    "health_monitor",
                    {"current_value": current_value, "threshold": warning_threshold}
                )
        else:
            # Resolve alert if it exists
            self.alert_manager.resolve_alert(alert_id)
    
    def _check_pii_detection_rate(self, current_pii_count: int):
        """Check PII detection rate alerts."""
        now = datetime.now()
        time_diff = (now - self.last_check_time).total_seconds() / 3600  # hours
        
        if time_diff > 0:
            pii_rate = (current_pii_count - self.last_pii_count) / time_diff
            
            if pii_rate >= self.thresholds["pii_detection_rate_warning"]:
                alert_id = "high_pii_detection_rate"
                if alert_id not in self.alert_manager.active_alerts:
                    self.alert_manager.create_alert(
                        alert_id,
                        "High PII Detection Rate",
                        f"PII detection rate is {pii_rate:.1f} detections per hour",
                        AlertSeverity.WARNING,
                        "health_monitor",
                        {"pii_rate_per_hour": pii_rate}
                    )
            else:
                self.alert_manager.resolve_alert("high_pii_detection_rate")
        
        self.last_check_time = now
        self.last_pii_count = current_pii_count
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        system_metrics = self.metrics_collector.get_system_metrics()
        app_metrics = self.metrics_collector.get_application_metrics()
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Determine overall status
        if any(alert.severity == AlertSeverity.CRITICAL for alert in active_alerts):
            overall_status = "critical"
        elif any(alert.severity == AlertSeverity.WARNING for alert in active_alerts):
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "overall_status": overall_status,
            "system_metrics": {
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "disk_usage_percent": system_metrics.disk_usage_percent,
                "uptime_seconds": system_metrics.uptime_seconds
            },
            "application_metrics": {
                "total_requests": app_metrics.total_requests,
                "error_rate": app_metrics.failed_requests / max(app_metrics.total_requests, 1),
                "avg_response_time": app_metrics.avg_response_time,
                "knowledge_items_processed": app_metrics.knowledge_items_processed,
                "pii_detections": app_metrics.pii_detections
            },
            "active_alerts": [
                {
                    "id": alert.id,
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in active_alerts
            ],
            "timestamp": datetime.now().isoformat()
        }


# Global instances
_alert_manager: Optional[AlertManager] = None
_health_monitor: Optional[HealthMonitor] = None


def initialize_monitoring(config: Config, metrics_collector: MetricsCollector):
    """Initialize monitoring system."""
    global _alert_manager, _health_monitor
    
    _alert_manager = AlertManager(config)
    _health_monitor = HealthMonitor(config, metrics_collector, _alert_manager)
    
    # Start monitoring if enabled
    if config.enable_metrics_collection:
        _health_monitor.start_monitoring()
    
    return _alert_manager, _health_monitor


def get_alert_manager() -> Optional[AlertManager]:
    """Get the global alert manager instance."""
    return _alert_manager


def get_health_monitor() -> Optional[HealthMonitor]:
    """Get the global health monitor instance."""
    return _health_monitor


# Convenience functions
def create_alert(alert_id: str, title: str, description: str, severity: AlertSeverity):
    """Create an alert."""
    if _alert_manager:
        return _alert_manager.create_alert(alert_id, title, description, severity)


def resolve_alert(alert_id: str) -> bool:
    """Resolve an alert."""
    if _alert_manager:
        return _alert_manager.resolve_alert(alert_id)
    return False


def get_health_status() -> Dict[str, Any]:
    """Get current health status."""
    if _health_monitor:
        return _health_monitor.get_health_status()
    return {"overall_status": "unknown", "timestamp": datetime.now().isoformat()}