"""Configuration validation utilities for the LinkedIn Knowledge Management System."""

import re
import os
import secrets
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from .config import Config
from ..models.exceptions import ConfigurationError


class ConfigValidator:
    """Advanced configuration validation and security checks."""
    
    @staticmethod
    def validate_api_key_format(api_key: str, key_type: str = "Gemini") -> bool:
        """Validate API key format and strength."""
        if not api_key:
            return False
        
        # Basic length check
        if len(api_key) < 20:
            return False
        
        # Check for placeholder values
        placeholder_patterns = [
            r'your_.*_key_here',
            r'replace_with_.*',
            r'enter_your_.*',
            r'api_key_here',
            r'xxx+',
            r'test_key'
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, api_key, re.IGNORECASE):
                return False
        
        return True
    
    @staticmethod
    def validate_encryption_key(key: Optional[str]) -> bool:
        """Validate encryption key strength."""
        if not key:
            return False
        
        # Must be at least 32 characters (256 bits)
        if len(key) < 32:
            return False
        
        # Should contain mix of characters
        has_upper = any(c.isupper() for c in key)
        has_lower = any(c.islower() for c in key)
        has_digit = any(c.isdigit() for c in key)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in key)
        
        return sum([has_upper, has_lower, has_digit, has_special]) >= 3
    
    @staticmethod
    def validate_webhook_url(url: Optional[str]) -> bool:
        """Validate webhook URL format and security."""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            
            # Must use HTTPS in production
            if parsed.scheme != 'https':
                return False
            
            # Must have valid hostname
            if not parsed.hostname:
                return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_email_address(email: Optional[str]) -> bool:
        """Validate email address format."""
        if not email:
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    @staticmethod
    def check_file_permissions(config: Config) -> List[str]:
        """Check file and directory permissions."""
        issues = []
        
        # Check if directories are writable
        directories_to_check = [
            config.knowledge_repo_path,
            Path(config.cache_db_path).parent,
            Path(config.log_file_path).parent,
        ]
        
        if config.enable_auto_backup:
            directories_to_check.append(config.backup_path)
        
        for directory in directories_to_check:
            dir_path = Path(directory)
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                
                # Test write permissions
                test_file = dir_path / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
                
            except PermissionError:
                issues.append(f"No write permission for directory: {directory}")
            except Exception as e:
                issues.append(f"Cannot access directory {directory}: {e}")
        
        return issues
    
    @staticmethod
    def check_security_configuration(config: Config) -> List[str]:
        """Check security configuration for potential issues."""
        warnings = []
        
        # Check API key
        if not ConfigValidator.validate_api_key_format(config.gemini_api_key):
            warnings.append("Gemini API key appears to be invalid or placeholder")
        
        # Check encryption settings
        if config.enable_content_encryption:
            if not ConfigValidator.validate_encryption_key(config.encryption_key):
                warnings.append("Encryption key is weak or invalid")
        
        # Check authentication settings
        if config.enable_api_authentication:
            if not config.api_secret_key or len(config.api_secret_key) < 32:
                warnings.append("API secret key is too short (minimum 32 characters)")
        
        # Check production settings
        if config.is_production():
            if config.server_debug:
                warnings.append("Debug mode should be disabled in production")
            
            if not config.enable_pii_detection:
                warnings.append("PII detection should be enabled in production")
            
            if not config.sanitize_content:
                warnings.append("Content sanitization should be enabled in production")
            
            if config.cors_allow_origins == "*":
                warnings.append("CORS should be restricted in production (not '*')")
        
        # Check alert configurations
        if config.enable_email_alerts:
            if not ConfigValidator.validate_email_address(config.alert_email_to):
                warnings.append("Invalid alert email address")
        
        if config.enable_webhook_alerts:
            if not ConfigValidator.validate_webhook_url(config.webhook_url):
                warnings.append("Invalid or insecure webhook URL")
        
        return warnings
    
    @staticmethod
    def generate_secure_keys() -> Dict[str, str]:
        """Generate secure keys for configuration."""
        return {
            "api_secret_key": secrets.token_urlsafe(32),
            "encryption_key": secrets.token_urlsafe(32),
            "jwt_secret": secrets.token_urlsafe(32)
        }
    
    @staticmethod
    def create_secure_env_file(output_path: str = ".env") -> None:
        """Create a secure .env file with generated keys."""
        keys = ConfigValidator.generate_secure_keys()
        
        env_content = f"""# LinkedIn Knowledge Management System - Secure Configuration
# Generated on: {os.popen('date').read().strip()}

# =============================================================================
# API CONFIGURATION (REQUIRED)
# =============================================================================
GEMINI_API_KEY=your_gemini_api_key_here

# =============================================================================
# SECURITY CONFIGURATION (AUTO-GENERATED)
# =============================================================================
API_SECRET_KEY={keys['api_secret_key']}
ENCRYPTION_KEY={keys['encryption_key']}
JWT_SECRET={keys['jwt_secret']}

# =============================================================================
# ENVIRONMENT SETTINGS
# =============================================================================
ENVIRONMENT=development
ENABLE_PII_DETECTION=true
SANITIZE_CONTENT=true
ENABLE_API_AUTHENTICATION=false
ENABLE_CONTENT_ENCRYPTION=false

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
SERVER_DEBUG=false
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:8000

# =============================================================================
# RATE LIMITING
# =============================================================================
GEMINI_RATE_LIMIT_RPM=15
API_RATE_LIMIT_REQUESTS_PER_MINUTE=60

# =============================================================================
# LOGGING
# =============================================================================
LOG_LEVEL=INFO
ENABLE_FILE_LOGGING=true

# =============================================================================
# ALERTS (OPTIONAL)
# =============================================================================
ENABLE_EMAIL_ALERTS=false
ENABLE_WEBHOOK_ALERTS=false

# =============================================================================
# BACKUP (OPTIONAL)
# =============================================================================
ENABLE_AUTO_BACKUP=false
"""
        
        with open(output_path, 'w') as f:
            f.write(env_content)
        
        # Set restrictive permissions on Unix systems
        try:
            os.chmod(output_path, 0o600)
        except:
            pass  # Windows doesn't support chmod
    
    @staticmethod
    def validate_full_configuration(config: Config) -> Dict[str, Any]:
        """Perform comprehensive configuration validation."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_issues": [],
            "permission_issues": [],
            "recommendations": []
        }
        
        try:
            # Basic validation
            config.validate()
        except ConfigurationError as e:
            result["valid"] = False
            result["errors"].append(str(e))
        
        # Security checks
        security_warnings = ConfigValidator.check_security_configuration(config)
        result["security_issues"].extend(security_warnings)
        
        # Permission checks
        permission_issues = ConfigValidator.check_file_permissions(config)
        result["permission_issues"].extend(permission_issues)
        
        # Recommendations
        if config.is_development():
            result["recommendations"].append("Consider enabling debug logging in development")
            result["recommendations"].append("Test with PII detection enabled")
        
        if config.is_production():
            result["recommendations"].append("Enable auto-backup in production")
            result["recommendations"].append("Configure email or webhook alerts")
            result["recommendations"].append("Enable API authentication")
            result["recommendations"].append("Use HTTPS-only CORS origins")
        
        # Overall validity
        if result["errors"] or result["permission_issues"]:
            result["valid"] = False
        
        return result


def validate_environment_file(env_file_path: str = ".env") -> Dict[str, Any]:
    """Validate an existing .env file."""
    if not Path(env_file_path).exists():
        return {
            "exists": False,
            "error": f"Environment file {env_file_path} not found"
        }
    
    try:
        config = Config.from_env(env_file_path)
        validation_result = ConfigValidator.validate_full_configuration(config)
        validation_result["exists"] = True
        validation_result["file_path"] = env_file_path
        return validation_result
    
    except Exception as e:
        return {
            "exists": True,
            "valid": False,
            "error": f"Failed to load configuration: {e}",
            "file_path": env_file_path
        }