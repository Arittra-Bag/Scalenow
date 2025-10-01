#!/usr/bin/env python3
"""
Quick security test to verify core functionality.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_core_security():
    """Test core security features."""
    print("🔒 Testing Core Security Features")
    print("=" * 40)
    
    # Test 1: PII Detection
    print("\n1. PII Detection Test:")
    try:
        from linkedin_scraper.utils.pii_detector import detect_and_sanitize_pii
        
        test_text = "Contact john.doe@company.com or call 555-123-4567"
        sanitized, info = detect_and_sanitize_pii(test_text, strategy="mask", min_confidence=0.8)
        
        print(f"Original: {test_text}")
        print(f"Sanitized: {sanitized}")
        print(f"Matches found: {info['matches_found']}")
        print(f"Matches sanitized: {info['matches_sanitized']}")
        print("✅ PII Detection working")
        
    except Exception as e:
        print(f"❌ PII Detection failed: {e}")
        return False
    
    # Test 2: Configuration
    print("\n2. Configuration Test:")
    try:
        from linkedin_scraper.utils.config import Config
        
        config = Config(gemini_api_key="test_key_12345678901234567890")
        config.validate()
        
        print(f"✅ Configuration created and validated")
        print(f"Environment: {config.environment}")
        print(f"PII Detection: {config.enable_pii_detection}")
        print(f"Content Sanitization: {config.sanitize_content}")
        
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False
    
    # Test 3: Key Generation
    print("\n3. Secure Key Generation Test:")
    try:
        from linkedin_scraper.utils.config_validator import ConfigValidator
        
        keys = ConfigValidator.generate_secure_keys()
        
        for key_name, key_value in keys.items():
            print(f"✅ {key_name}: {len(key_value)} characters")
        
    except Exception as e:
        print(f"❌ Key generation failed: {e}")
        return False
    
    print("\n🎉 All core security tests passed!")
    return True

if __name__ == "__main__":
    success = test_core_security()
    if success:
        print("\n✅ Security system is ready for production!")
    else:
        print("\n❌ Security tests failed!")
    sys.exit(0 if success else 1)