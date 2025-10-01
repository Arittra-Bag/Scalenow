"""Configuration management for the LinkedIn Knowledge Management System."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from ..models.exceptions import ConfigurationError


@dataclass
class Config:
    """Configuration settings for the LinkedIn KMS."""
    
    # API Configuration
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_rate_limit_rpm: int = 15
    gemini_rate_limit_rpd: int = 1500
    gemini_max_tokens_per_day: int = 1000000
    
    # Storage Configuration
    knowledge_repo_path: str = "./knowledge_repository"
    cache_db_path: str = "./cache/knowledge_cache.db"
    max_cache_size_mb: int = 100
    
    # Scraping Configuration
    scraping_delay_seconds: float = 2.0
    max_retries: int = 3
    request_timeout_seconds: int = 30
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Processing Configuration
    batch_size: int = 10
    max_concurrent_requests: int = 5
    enable_image_download: bool = True
    max_image_size_mb: int = 10
    
    # File Management
    excel_filename_template: str = "Knowledge_Resources_v{version}.xlsx"
    word_filename_template: str = "Knowledge_Resources_v{version}.docx"
    enable_version_control: bool = True
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file_path: str = "./logs/linkedin_kms.log"
    enable_file_logging: bool = True
    max_log_file_size_mb: int = 10
    
    # Security Configuration
    enable_pii_detection: bool = True
    sanitize_content: bool = True
    enable_content_encryption: bool = False
    encryption_key: Optional[str] = None
    
    # API Security
    api_rate_limit_requests_per_minute: int = 60
    api_rate_limit_requests_per_hour: int = 1000
    enable_api_authentication: bool = False
    api_secret_key: Optional[str] = None
    jwt_expiration_hours: int = 24
    
    # Web Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_reload: bool = False
    server_debug: bool = False
    cors_allow_origins: str = "*"
    cors_allow_credentials: bool = True
    
    # Database Configuration
    db_connection_timeout: int = 30
    db_max_connections: int = 10
    db_enable_wal_mode: bool = True
    
    # Monitoring Configuration
    enable_metrics_collection: bool = True
    metrics_export_interval_seconds: int = 60
    
    # Alert Configuration
    enable_email_alerts: bool = False
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    alert_email_to: Optional[str] = None
    enable_webhook_alerts: bool = False
    webhook_url: Optional[str] = None
    
    # Environment Configuration
    environment: str = "development"
    development_mode: bool = False
    enable_debug_logging: bool = False
    mock_api_responses: bool = False
    
    # Health Check Configuration
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 5
    
    # Backup Configuration
    enable_auto_backup: bool = False
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    backup_path: str = "./backups"
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> 'Config':
        """Load configuration from environment variables and .env file."""
        
        # Load .env file if specified or if default exists
        if env_file:
            load_dotenv(env_file)
        elif Path('.env').exists():
            load_dotenv('.env')
        
        # Get required API key
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        return cls(
            # API Configuration
            gemini_api_key=gemini_api_key,
            gemini_model=os.getenv('GEMINI_MODEL', cls.gemini_model),
            gemini_rate_limit_rpm=int(os.getenv('GEMINI_RATE_LIMIT_RPM', cls.gemini_rate_limit_rpm)),
            gemini_rate_limit_rpd=int(os.getenv('GEMINI_RATE_LIMIT_RPD', cls.gemini_rate_limit_rpd)),
            gemini_max_tokens_per_day=int(os.getenv('GEMINI_MAX_TOKENS_PER_DAY', cls.gemini_max_tokens_per_day)),
            
            # Storage Configuration
            knowledge_repo_path=os.getenv('KNOWLEDGE_REPO_PATH', cls.knowledge_repo_path),
            cache_db_path=os.getenv('CACHE_DB_PATH', cls.cache_db_path),
            max_cache_size_mb=int(os.getenv('MAX_CACHE_SIZE_MB', cls.max_cache_size_mb)),
            
            # Scraping Configuration
            scraping_delay_seconds=float(os.getenv('SCRAPING_DELAY_SECONDS', cls.scraping_delay_seconds)),
            max_retries=int(os.getenv('MAX_RETRIES', cls.max_retries)),
            request_timeout_seconds=int(os.getenv('REQUEST_TIMEOUT_SECONDS', cls.request_timeout_seconds)),
            user_agent=os.getenv('USER_AGENT', cls.user_agent),
            
            # Processing Configuration
            batch_size=int(os.getenv('BATCH_SIZE', cls.batch_size)),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', cls.max_concurrent_requests)),
            enable_image_download=os.getenv('ENABLE_IMAGE_DOWNLOAD', 'true').lower() == 'true',
            max_image_size_mb=int(os.getenv('MAX_IMAGE_SIZE_MB', cls.max_image_size_mb)),
            
            # File Management
            excel_filename_template=os.getenv('EXCEL_FILENAME_TEMPLATE', cls.excel_filename_template),
            word_filename_template=os.getenv('WORD_FILENAME_TEMPLATE', cls.word_filename_template),
            enable_version_control=os.getenv('ENABLE_VERSION_CONTROL', 'true').lower() == 'true',
            
            # Logging Configuration
            log_level=os.getenv('LOG_LEVEL', cls.log_level),
            log_file_path=os.getenv('LOG_FILE_PATH', cls.log_file_path),
            enable_file_logging=os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true',
            max_log_file_size_mb=int(os.getenv('MAX_LOG_FILE_SIZE_MB', cls.max_log_file_size_mb)),
            
            # Security Configuration
            enable_pii_detection=os.getenv('ENABLE_PII_DETECTION', 'true').lower() == 'true',
            sanitize_content=os.getenv('SANITIZE_CONTENT', 'true').lower() == 'true',
            enable_content_encryption=os.getenv('ENABLE_CONTENT_ENCRYPTION', 'false').lower() == 'true',
            encryption_key=os.getenv('ENCRYPTION_KEY'),
            
            # API Security
            api_rate_limit_requests_per_minute=int(os.getenv('API_RATE_LIMIT_REQUESTS_PER_MINUTE', cls.api_rate_limit_requests_per_minute)),
            api_rate_limit_requests_per_hour=int(os.getenv('API_RATE_LIMIT_REQUESTS_PER_HOUR', cls.api_rate_limit_requests_per_hour)),
            enable_api_authentication=os.getenv('ENABLE_API_AUTHENTICATION', 'false').lower() == 'true',
            api_secret_key=os.getenv('API_SECRET_KEY'),
            jwt_expiration_hours=int(os.getenv('JWT_EXPIRATION_HOURS', cls.jwt_expiration_hours)),
            
            # Web Server Configuration
            server_host=os.getenv('SERVER_HOST', cls.server_host),
            server_port=int(os.getenv('SERVER_PORT', cls.server_port)),
            server_reload=os.getenv('SERVER_RELOAD', 'false').lower() == 'true',
            server_debug=os.getenv('SERVER_DEBUG', 'false').lower() == 'true',
            cors_allow_origins=os.getenv('CORS_ALLOW_ORIGINS', cls.cors_allow_origins),
            cors_allow_credentials=os.getenv('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true',
            
            # Database Configuration
            db_connection_timeout=int(os.getenv('DB_CONNECTION_TIMEOUT', cls.db_connection_timeout)),
            db_max_connections=int(os.getenv('DB_MAX_CONNECTIONS', cls.db_max_connections)),
            db_enable_wal_mode=os.getenv('DB_ENABLE_WAL_MODE', 'true').lower() == 'true',
            
            # Monitoring Configuration
            enable_metrics_collection=os.getenv('ENABLE_METRICS_COLLECTION', 'true').lower() == 'true',
            metrics_export_interval_seconds=int(os.getenv('METRICS_EXPORT_INTERVAL_SECONDS', cls.metrics_export_interval_seconds)),
            
            # Alert Configuration
            enable_email_alerts=os.getenv('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true',
            smtp_server=os.getenv('SMTP_SERVER'),
            smtp_port=int(os.getenv('SMTP_PORT', cls.smtp_port)),
            smtp_username=os.getenv('SMTP_USERNAME'),
            smtp_password=os.getenv('SMTP_PASSWORD'),
            alert_email_to=os.getenv('ALERT_EMAIL_TO'),
            enable_webhook_alerts=os.getenv('ENABLE_WEBHOOK_ALERTS', 'false').lower() == 'true',
            webhook_url=os.getenv('WEBHOOK_URL'),
            
            # Environment Configuration
            environment=os.getenv('ENVIRONMENT', cls.environment),
            development_mode=os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true',
            enable_debug_logging=os.getenv('ENABLE_DEBUG_LOGGING', 'false').lower() == 'true',
            mock_api_responses=os.getenv('MOCK_API_RESPONSES', 'false').lower() == 'true',
            
            # Health Check Configuration
            health_check_interval_seconds=int(os.getenv('HEALTH_CHECK_INTERVAL_SECONDS', cls.health_check_interval_seconds)),
            health_check_timeout_seconds=int(os.getenv('HEALTH_CHECK_TIMEOUT_SECONDS', cls.health_check_timeout_seconds)),
            
            # Backup Configuration
            enable_auto_backup=os.getenv('ENABLE_AUTO_BACKUP', 'false').lower() == 'true',
            backup_interval_hours=int(os.getenv('BACKUP_INTERVAL_HOURS', cls.backup_interval_hours)),
            backup_retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', cls.backup_retention_days)),
            backup_path=os.getenv('BACKUP_PATH', cls.backup_path),
        )
    
    def validate(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Validate API configuration
        if not self.gemini_api_key:
            errors.append("Gemini API key is required")
        
        if self.gemini_rate_limit_rpm <= 0:
            errors.append("Gemini rate limit RPM must be positive")
        
        if self.gemini_rate_limit_rpd <= 0:
            errors.append("Gemini rate limit RPD must be positive")
        
        # Validate paths
        try:
            Path(self.knowledge_repo_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create knowledge repository path: {e}")
        
        try:
            Path(self.cache_db_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create cache directory: {e}")
        
        # Validate numeric settings
        if self.batch_size <= 0:
            errors.append("Batch size must be positive")
        
        if self.max_concurrent_requests <= 0:
            errors.append("Max concurrent requests must be positive")
        
        if self.scraping_delay_seconds < 0:
            errors.append("Scraping delay cannot be negative")
        
        # Validate security settings
        if self.enable_content_encryption and not self.encryption_key:
            errors.append("Encryption key is required when content encryption is enabled")
        
        if self.enable_api_authentication and not self.api_secret_key:
            errors.append("API secret key is required when authentication is enabled")
        
        if self.api_secret_key and len(self.api_secret_key) < 32:
            errors.append("API secret key must be at least 32 characters long")
        
        # Validate rate limiting
        if self.api_rate_limit_requests_per_minute <= 0:
            errors.append("API rate limit per minute must be positive")
        
        if self.api_rate_limit_requests_per_hour <= 0:
            errors.append("API rate limit per hour must be positive")
        
        # Validate server configuration
        if not (1 <= self.server_port <= 65535):
            errors.append("Server port must be between 1 and 65535")
        
        # Validate email alert configuration
        if self.enable_email_alerts:
            if not self.smtp_server:
                errors.append("SMTP server is required when email alerts are enabled")
            if not self.smtp_username:
                errors.append("SMTP username is required when email alerts are enabled")
            if not self.smtp_password:
                errors.append("SMTP password is required when email alerts are enabled")
            if not self.alert_email_to:
                errors.append("Alert email recipient is required when email alerts are enabled")
        
        # Validate webhook alerts
        if self.enable_webhook_alerts and not self.webhook_url:
            errors.append("Webhook URL is required when webhook alerts are enabled")
        
        # Validate environment
        valid_environments = ['development', 'staging', 'production']
        if self.environment not in valid_environments:
            errors.append(f"Environment must be one of: {', '.join(valid_environments)}")
        
        # Production environment validations
        if self.environment == 'production':
            if self.server_debug:
                errors.append("Debug mode should be disabled in production")
            if self.development_mode:
                errors.append("Development mode should be disabled in production")
            if not self.enable_pii_detection:
                errors.append("PII detection should be enabled in production")
            if not self.sanitize_content:
                errors.append("Content sanitization should be enabled in production")
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def create_directories(self) -> None:
        """Create necessary directories for the application."""
        directories = [
            self.knowledge_repo_path,
            f"{self.knowledge_repo_path}/docs",
            f"{self.knowledge_repo_path}/excels", 
            f"{self.knowledge_repo_path}/infographics",
            Path(self.cache_db_path).parent,
            Path(self.log_file_path).parent,
        ]
        
        # Add backup directory if auto backup is enabled
        if self.enable_auto_backup:
            directories.append(self.backup_path)
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_environment_info(self) -> dict:
        """Get environment information for debugging and monitoring."""
        return {
            "environment": self.environment,
            "development_mode": self.development_mode,
            "debug_logging": self.enable_debug_logging,
            "pii_detection": self.enable_pii_detection,
            "content_sanitization": self.sanitize_content,
            "api_authentication": self.enable_api_authentication,
            "content_encryption": self.enable_content_encryption,
            "email_alerts": self.enable_email_alerts,
            "webhook_alerts": self.enable_webhook_alerts,
            "metrics_collection": self.enable_metrics_collection,
            "auto_backup": self.enable_auto_backup,
            "server_host": self.server_host,
            "server_port": self.server_port,
            "gemini_model": self.gemini_model,
            "rate_limits": {
                "gemini_rpm": self.gemini_rate_limit_rpm,
                "gemini_rpd": self.gemini_rate_limit_rpd,
                "api_rpm": self.api_rate_limit_requests_per_minute,
                "api_rph": self.api_rate_limit_requests_per_hour
            }
        }
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == 'development' or self.development_mode