#!/usr/bin/env python3
"""
Configuration Management CLI for LinkedIn Knowledge Management System.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from linkedin_scraper.utils.config import Config
    from linkedin_scraper.utils.config_validator import ConfigValidator, validate_environment_file
    from linkedin_scraper.models.exceptions import ConfigurationError
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory.")
    sys.exit(1)


def print_colored(text: str, color: str = "white") -> None:
    """Print colored text to console."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "purple": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")


def print_validation_result(result: Dict[str, Any]) -> None:
    """Print configuration validation results."""
    print("\n" + "=" * 60)
    print_colored("CONFIGURATION VALIDATION RESULTS", "cyan")
    print("=" * 60)
    
    if result.get("exists", True):
        if result["valid"]:
            print_colored("✅ Configuration is VALID", "green")
        else:
            print_colored("❌ Configuration is INVALID", "red")
    else:
        print_colored("❌ Configuration file not found", "red")
        return
    
    # Print errors
    if result.get("errors"):
        print_colored("\n🚨 ERRORS:", "red")
        for error in result["errors"]:
            print(f"  • {error}")
    
    # Print security issues
    if result.get("security_issues"):
        print_colored("\n⚠️  SECURITY ISSUES:", "yellow")
        for issue in result["security_issues"]:
            print(f"  • {issue}")
    
    # Print permission issues
    if result.get("permission_issues"):
        print_colored("\n🔒 PERMISSION ISSUES:", "red")
        for issue in result["permission_issues"]:
            print(f"  • {issue}")
    
    # Print warnings
    if result.get("warnings"):
        print_colored("\n⚠️  WARNINGS:", "yellow")
        for warning in result["warnings"]:
            print(f"  • {warning}")
    
    # Print recommendations
    if result.get("recommendations"):
        print_colored("\n💡 RECOMMENDATIONS:", "blue")
        for rec in result["recommendations"]:
            print(f"  • {rec}")


def validate_config(args) -> None:
    """Validate configuration."""
    env_file = args.env_file or ".env"
    
    print_colored(f"🔍 Validating configuration from: {env_file}", "cyan")
    
    result = validate_environment_file(env_file)
    print_validation_result(result)
    
    if not result.get("valid", False):
        sys.exit(1)


def create_config(args) -> None:
    """Create a new configuration file."""
    output_file = args.output or ".env"
    
    if Path(output_file).exists() and not args.force:
        print_colored(f"❌ File {output_file} already exists. Use --force to overwrite.", "red")
        sys.exit(1)
    
    print_colored(f"🔧 Creating secure configuration file: {output_file}", "cyan")
    
    try:
        ConfigValidator.create_secure_env_file(output_file)
        print_colored(f"✅ Configuration file created successfully!", "green")
        print_colored(f"📝 Please edit {output_file} and add your Gemini API key.", "yellow")
        
        # Show generated keys
        print_colored("\n🔑 Generated secure keys:", "blue")
        print("  • API Secret Key: [Generated]")
        print("  • Encryption Key: [Generated]")
        print("  • JWT Secret: [Generated]")
        
    except Exception as e:
        print_colored(f"❌ Failed to create configuration: {e}", "red")
        sys.exit(1)


def show_info(args) -> None:
    """Show configuration information."""
    env_file = args.env_file or ".env"
    
    try:
        config = Config.from_env(env_file)
        env_info = config.get_environment_info()
        
        print_colored("📊 CONFIGURATION INFORMATION", "cyan")
        print("=" * 50)
        
        print_colored("\n🌍 Environment:", "blue")
        print(f"  Environment: {env_info['environment']}")
        print(f"  Development Mode: {env_info['development_mode']}")
        print(f"  Debug Logging: {env_info['debug_logging']}")
        
        print_colored("\n🔒 Security:", "blue")
        print(f"  PII Detection: {env_info['pii_detection']}")
        print(f"  Content Sanitization: {env_info['content_sanitization']}")
        print(f"  API Authentication: {env_info['api_authentication']}")
        print(f"  Content Encryption: {env_info['content_encryption']}")
        
        print_colored("\n🚨 Alerts:", "blue")
        print(f"  Email Alerts: {env_info['email_alerts']}")
        print(f"  Webhook Alerts: {env_info['webhook_alerts']}")
        
        print_colored("\n📈 Monitoring:", "blue")
        print(f"  Metrics Collection: {env_info['metrics_collection']}")
        print(f"  Auto Backup: {env_info['auto_backup']}")
        
        print_colored("\n🌐 Server:", "blue")
        print(f"  Host: {env_info['server_host']}")
        print(f"  Port: {env_info['server_port']}")
        print(f"  Gemini Model: {env_info['gemini_model']}")
        
        print_colored("\n⏱️  Rate Limits:", "blue")
        for key, value in env_info['rate_limits'].items():
            print(f"  {key.upper()}: {value}")
        
    except Exception as e:
        print_colored(f"❌ Failed to load configuration: {e}", "red")
        sys.exit(1)


def test_config(args) -> None:
    """Test configuration by loading and validating."""
    env_file = args.env_file or ".env"
    
    print_colored(f"🧪 Testing configuration from: {env_file}", "cyan")
    
    try:
        # Load configuration
        config = Config.from_env(env_file)
        print_colored("✅ Configuration loaded successfully", "green")
        
        # Validate configuration
        config.validate()
        print_colored("✅ Configuration validation passed", "green")
        
        # Create directories
        config.create_directories()
        print_colored("✅ Directories created successfully", "green")
        
        # Run comprehensive validation
        result = ConfigValidator.validate_full_configuration(config)
        
        if result["valid"]:
            print_colored("✅ All tests passed!", "green")
        else:
            print_colored("⚠️  Some issues found:", "yellow")
            print_validation_result(result)
        
    except Exception as e:
        print_colored(f"❌ Configuration test failed: {e}", "red")
        sys.exit(1)


def generate_keys(args) -> None:
    """Generate secure keys for configuration."""
    print_colored("🔑 Generating secure keys...", "cyan")
    
    keys = ConfigValidator.generate_secure_keys()
    
    print_colored("\n🔐 Generated Keys:", "green")
    print("=" * 50)
    
    for key_name, key_value in keys.items():
        print_colored(f"\n{key_name.upper()}:", "blue")
        print(f"{key_value}")
    
    print_colored("\n💡 Usage:", "yellow")
    print("Add these keys to your .env file:")
    for key_name, key_value in keys.items():
        env_var = key_name.upper()
        print(f"{env_var}={key_value}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LinkedIn Knowledge Management System - Configuration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python config_manager.py validate                    # Validate .env file
  python config_manager.py create                      # Create new .env file
  python config_manager.py create --force              # Overwrite existing .env
  python config_manager.py info                        # Show config info
  python config_manager.py test                        # Test configuration
  python config_manager.py generate-keys               # Generate secure keys
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('--env-file', help='Path to .env file (default: .env)')
    validate_parser.set_defaults(func=validate_config)
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new configuration file')
    create_parser.add_argument('--output', '-o', help='Output file path (default: .env)')
    create_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing file')
    create_parser.set_defaults(func=create_config)
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show configuration information')
    info_parser.add_argument('--env-file', help='Path to .env file (default: .env)')
    info_parser.set_defaults(func=show_info)
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test configuration')
    test_parser.add_argument('--env-file', help='Path to .env file (default: .env)')
    test_parser.set_defaults(func=test_config)
    
    # Generate keys command
    keys_parser = subparsers.add_parser('generate-keys', help='Generate secure keys')
    keys_parser.set_defaults(func=generate_keys)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print_colored("\n👋 Operation cancelled by user", "yellow")
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n❌ Unexpected error: {e}", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()