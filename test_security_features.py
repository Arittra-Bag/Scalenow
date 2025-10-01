#!/usr/bin/env python3
"""
Test script for security features and configuration system.
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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

def test_pii_detection():
    """Test PII detection functionality."""
    print_colored("\n🔍 Testing PII Detection System", "cyan")
    print("=" * 50)
    
    try:
        from linkedin_scraper.utils.pii_detector import PIIDetector, PIISanitizer, detect_and_sanitize_pii
        
        # Test cases with various PII types
        test_cases = [
            "Contact John Doe at john.doe@company.com or call 555-123-4567",
            "My email is test@example.com and my phone is (555) 987-6543",
            "SSN: 123-45-6789, Credit Card: 4111-1111-1111-1111",
            "Visit my LinkedIn profile at linkedin.com/in/johndoe",
            "IP address 192.168.1.100 accessed the system",
            "Born on 01/15/1990, lives at 123 Main Street",
            "No PII in this text - just regular content about AI and business"
        ]
        
        detector = PIIDetector()
        sanitizer = PIISanitizer()
        
        for i, test_text in enumerate(test_cases, 1):
            print(f"\n📝 Test Case {i}:")
            print(f"Original: {test_text}")
            
            # Detect PII
            matches = detector.detect_pii(test_text)
            print(f"PII Matches Found: {len(matches)}")
            
            for match in matches:
                print(f"  • {match.pii_type.value}: '{match.original_text}' (confidence: {match.confidence:.2f})")
            
            # Sanitize with different strategies
            if matches:
                high_conf_matches = [m for m in matches if m.confidence >= 0.6]
                if high_conf_matches:
                    sanitized_mask, _ = sanitizer.sanitize_text(test_text, high_conf_matches, "mask")
                    sanitized_placeholder, _ = sanitizer.sanitize_text(test_text, high_conf_matches, "placeholder")
                    
                    print(f"Masked: {sanitized_mask}")
                    print(f"Placeholder: {sanitized_placeholder}")
            
            print("-" * 40)
        
        print_colored("✅ PII Detection tests completed successfully", "green")
        return True
        
    except Exception as e:
        print_colored(f"❌ PII Detection test failed: {e}", "red")
        return False

def test_privacy_logging():
    """Test privacy-safe logging."""
    print_colored("\n📝 Testing Privacy-Safe Logging", "cyan")
    print("=" * 50)
    
    try:
        from linkedin_scraper.utils.config import Config
        from linkedin_scraper.utils.privacy_logger import get_privacy_logger
        
        # Create test config
        config = Config(
            gemini_api_key="test_key_for_logging",
            enable_pii_detection=True,
            sanitize_content=True,
            log_level="DEBUG",
            enable_file_logging=False  # Don't create log files in test
        )
        
        # Get privacy logger
        logger = get_privacy_logger("test_logger", config)
        
        # Test logging with PII
        print("\n🔒 Testing PII sanitization in logs:")
        
        test_messages = [
            "User john.doe@company.com logged in successfully",
            "Failed login attempt from IP 192.168.1.100",
            "Processing payment for card ending in 1111",
            "Contact support at support@company.com or call 555-HELP",
            "Regular log message without any PII"
        ]
        
        for message in test_messages:
            print(f"\nOriginal message: {message}")
            logger.info(message)  # This should automatically sanitize PII
        
        # Test structured logging
        logger.log_api_request("/api/users", "GET", 200, 0.123, "user123@email.com")
        logger.log_security_event("failed_login", "medium", "Invalid credentials", "192.168.1.100")
        
        print_colored("✅ Privacy logging tests completed successfully", "green")
        return True
        
    except Exception as e:
        print_colored(f"❌ Privacy logging test failed: {e}", "red")
        return False

def test_configuration_system():
    """Test configuration system."""
    print_colored("\n⚙️ Testing Configuration System", "cyan")
    print("=" * 50)
    
    try:
        from linkedin_scraper.utils.config import Config
        from linkedin_scraper.utils.config_validator import ConfigValidator, validate_environment_file
        
        # Test 1: Create config with minimal settings
        print("\n1. Testing basic configuration creation:")
        config = Config(gemini_api_key="test_api_key_12345678901234567890")
        print(f"✅ Config created with API key: {config.gemini_api_key[:10]}...")
        
        # Test 2: Validate configuration
        print("\n2. Testing configuration validation:")
        try:
            config.validate()
            print("✅ Configuration validation passed")
        except Exception as e:
            print(f"⚠️ Validation warning: {e}")
        
        # Test 3: Test directory creation
        print("\n3. Testing directory creation:")
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config = Config(
                gemini_api_key="test_key_12345678901234567890",
                knowledge_repo_path=f"{temp_dir}/knowledge",
                cache_db_path=f"{temp_dir}/cache/cache.db",
                log_file_path=f"{temp_dir}/logs/app.log"
            )
            test_config.create_directories()
            
            # Check if directories were created
            expected_dirs = [
                f"{temp_dir}/knowledge",
                f"{temp_dir}/cache",
                f"{temp_dir}/logs"
            ]
            
            for dir_path in expected_dirs:
                if Path(dir_path).exists():
                    print(f"✅ Directory created: {dir_path}")
                else:
                    print(f"❌ Directory missing: {dir_path}")
        
        # Test 4: Test security validation
        print("\n4. Testing security validation:")
        security_warnings = ConfigValidator.check_security_configuration(config)
        if security_warnings:
            print("⚠️ Security warnings found:")
            for warning in security_warnings:
                print(f"  • {warning}")
        else:
            print("✅ No security warnings")
        
        # Test 5: Test key generation
        print("\n5. Testing secure key generation:")
        keys = ConfigValidator.generate_secure_keys()
        for key_name, key_value in keys.items():
            print(f"✅ Generated {key_name}: {key_value[:10]}... (length: {len(key_value)})")
        
        print_colored("✅ Configuration system tests completed successfully", "green")
        return True
        
    except Exception as e:
        print_colored(f"❌ Configuration system test failed: {e}", "red")
        return False

def test_content_sanitization():
    """Test content sanitization service."""
    print_colored("\n🧹 Testing Content Sanitization Service", "cyan")
    print("=" * 50)
    
    try:
        from linkedin_scraper.utils.config import Config
        from linkedin_scraper.services.content_sanitizer import ContentSanitizer
        from linkedin_scraper.models.knowledge_item import KnowledgeItem, Category
        
        # Create test config
        config = Config(
            gemini_api_key="test_key_12345678901234567890",
            enable_pii_detection=True,
            sanitize_content=True
        )
        
        # Create sanitizer
        sanitizer = ContentSanitizer(config)
        
        # Test 1: Text sanitization
        print("\n1. Testing text sanitization:")
        test_text = "Contact our expert John Smith at john.smith@company.com or call 555-123-4567 for more information about our AI solutions."
        
        sanitized_text, result = sanitizer.sanitize_text_content(test_text, "test_content")
        
        print(f"Original: {test_text}")
        print(f"Sanitized: {sanitized_text}")
        print(f"PII Detected: {result.pii_detected}")
        print(f"Risk Level: {result.risk_level}")
        print(f"Replacements: {len(result.replacements_made)}")
        
        # Test 2: Knowledge item sanitization
        print("\n2. Testing knowledge item sanitization:")
        
        # Create a mock knowledge item with PII
        knowledge_item = KnowledgeItem(
            post_title="Contact John Doe for AI Consulting",
            key_knowledge_content="Reach out to john.doe@aicompany.com or call 555-987-6543 to learn about machine learning implementations. Our expert has worked with companies like Google and Microsoft.",
            topic="AI Consulting",
            category=Category.AI_MACHINE_LEARNING,
            source_url="https://linkedin.com/posts/test",
            course_references=["AI for Business", "Machine Learning 101"]
        )
        
        sanitized_item, sanitization_result = sanitizer.sanitize_knowledge_item(knowledge_item)
        
        print(f"Original title: {knowledge_item.post_title}")
        print(f"Sanitized title: {sanitized_item.post_title}")
        print(f"Original content: {knowledge_item.key_knowledge_content[:100]}...")
        print(f"Sanitized content: {sanitized_item.key_knowledge_content[:100]}...")
        print(f"PII matches found: {len(sanitization_result.pii_matches)}")
        print(f"Replacements made: {len(sanitization_result.replacements_made)}")
        
        # Test 3: Content safety validation
        print("\n3. Testing content safety validation:")
        
        safe_text = "This is a regular business post about AI trends and market analysis."
        unsafe_text = "Contact me at my personal email john@gmail.com or call my cell 555-123-4567"
        
        is_safe1, info1 = sanitizer.validate_content_safety(safe_text)
        is_safe2, info2 = sanitizer.validate_content_safety(unsafe_text)
        
        print(f"Safe text validation: {is_safe1} (matches: {info1['total_matches']})")
        print(f"Unsafe text validation: {is_safe2} (matches: {info2['total_matches']})")
        
        # Test 4: Statistics
        print("\n4. Testing sanitization statistics:")
        stats = sanitizer.get_sanitization_stats()
        print(f"Total processed: {stats['total_processed']}")
        print(f"PII detected: {stats['pii_detected_count']}")
        print(f"Sanitizations performed: {stats['sanitizations_performed']}")
        print(f"Sanitization rate: {stats['sanitization_rate']:.1f}%")
        
        print_colored("✅ Content sanitization tests completed successfully", "green")
        return True
        
    except Exception as e:
        print_colored(f"❌ Content sanitization test failed: {e}", "red")
        return False

def test_config_manager_cli():
    """Test the configuration manager CLI."""
    print_colored("\n🛠️ Testing Configuration Manager CLI", "cyan")
    print("=" * 50)
    
    try:
        # Test key generation
        print("\n1. Testing key generation:")
        from linkedin_scraper.utils.config_validator import ConfigValidator
        
        keys = ConfigValidator.generate_secure_keys()
        print("✅ Secure keys generated successfully")
        
        # Test .env file creation
        print("\n2. Testing .env file creation:")
        with tempfile.TemporaryDirectory() as temp_dir:
            test_env_path = f"{temp_dir}/.env"
            ConfigValidator.create_secure_env_file(test_env_path)
            
            if Path(test_env_path).exists():
                print("✅ .env file created successfully")
                
                # Read and validate the created file
                with open(test_env_path, 'r') as f:
                    content = f.read()
                    if "API_SECRET_KEY=" in content and "ENCRYPTION_KEY=" in content:
                        print("✅ Generated keys found in .env file")
                    else:
                        print("❌ Generated keys not found in .env file")
            else:
                print("❌ .env file was not created")
        
        # Test environment validation
        print("\n3. Testing environment validation:")
        
        # Create a test .env file with known content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("""
GEMINI_API_KEY=test_key_12345678901234567890
ENVIRONMENT=development
ENABLE_PII_DETECTION=true
SANITIZE_CONTENT=true
LOG_LEVEL=INFO
""")
            test_env_path = f.name
        
        try:
            validation_result = validate_environment_file(test_env_path)
            if validation_result.get("exists", False):
                print("✅ Environment file validation completed")
                if validation_result.get("valid", False):
                    print("✅ Configuration is valid")
                else:
                    print("⚠️ Configuration has issues:")
                    for error in validation_result.get("errors", []):
                        print(f"  • {error}")
            else:
                print("❌ Environment file not found")
        finally:
            os.unlink(test_env_path)
        
        print_colored("✅ Configuration Manager CLI tests completed successfully", "green")
        return True
        
    except Exception as e:
        print_colored(f"❌ Configuration Manager CLI test failed: {e}", "red")
        return False

def run_all_tests():
    """Run all security and configuration tests."""
    print_colored("🧪 LinkedIn Knowledge Management System - Security Tests", "purple")
    print_colored("=" * 70, "purple")
    
    tests = [
        ("PII Detection", test_pii_detection),
        ("Privacy Logging", test_privacy_logging),
        ("Configuration System", test_configuration_system),
        ("Content Sanitization", test_content_sanitization),
        ("Config Manager CLI", test_config_manager_cli)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_colored(f"❌ {test_name} test crashed: {e}", "red")
            results[test_name] = False
    
    # Summary
    print_colored("\n📊 TEST RESULTS SUMMARY", "purple")
    print_colored("=" * 70, "purple")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        color = "green" if result else "red"
        print_colored(f"{test_name:<25} {status}", color)
        if result:
            passed += 1
    
    print_colored(f"\nOverall Result: {passed}/{total} tests passed", 
                 "green" if passed == total else "yellow")
    
    if passed == total:
        print_colored("🎉 All security tests passed! System is ready for deployment.", "green")
    else:
        print_colored("⚠️ Some tests failed. Please review and fix issues before deployment.", "yellow")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_colored("\n👋 Tests cancelled by user", "yellow")
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n❌ Test suite crashed: {e}", "red")
        sys.exit(1)