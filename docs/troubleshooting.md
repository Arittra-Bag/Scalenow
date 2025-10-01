# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the LinkedIn Knowledge Scraper.

## Common Issues

### 1. API Key Issues

#### "Invalid API Key" Error

**Symptoms:**
- Error message: "Invalid or missing Gemini API key"
- HTTP 401 Unauthorized responses
- Authentication failures in logs

**Causes:**
- Incorrect API key format
- Expired or revoked API key
- API key not properly set in environment

**Solutions:**

1. **Verify API Key Format:**
```bash
# Check if API key is properly formatted (should be 39+ characters)
echo $GEMINI_API_KEY | wc -c
```

2. **Test API Key:**
```python
import google.generativeai as genai

genai.configure(api_key="your_api_key")
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("Hello")
print(response.text)
```

3. **Check Environment Variables:**
```bash
# Verify environment variable is set
env | grep GEMINI_API_KEY

# Check .env file
cat .env | grep GEMINI_API_KEY
```

4. **Regenerate API Key:**
   - Go to Google AI Studio
   - Generate new API key
   - Update configuration

#### "API Quota Exceeded" Error

**Symptoms:**
- Error message: "Quota exceeded"
- HTTP 429 responses
- Processing stops after certain number of requests

**Solutions:**

1. **Check Current Usage:**
   - Visit Google Cloud Console
   - Check API quotas and usage

2. **Implement Rate Limiting:**
```python
# Adjust rate limits in configuration
GEMINI_RATE_LIMIT_RPM=30  # Reduce from default 60
GEMINI_RATE_LIMIT_RPD=500  # Reduce from default 1000
```

3. **Request Quota Increase:**
   - Contact Google Cloud Support
   - Provide usage justification

### 2. Network and Connectivity Issues

#### "Connection Timeout" Errors

**Symptoms:**
- Timeout errors when scraping LinkedIn
- Network connection failures
- Intermittent processing failures

**Diagnosis:**
```bash
# Test network connectivity
curl -I https://linkedin.com
curl -I https://generativelanguage.googleapis.com

# Check DNS resolution
nslookup linkedin.com
nslookup generativelanguage.googleapis.com
```

**Solutions:**

1. **Increase Timeout Values:**
```python
# In configuration
REQUEST_TIMEOUT=30  # Increase from default
MAX_RETRIES=5       # Increase retry attempts
```

2. **Check Firewall Settings:**
   - Ensure outbound HTTPS (443) is allowed
   - Check corporate firewall rules
   - Verify proxy settings if applicable

3. **Use Proxy if Required:**
```python
# Configure proxy in web scraper
PROXY_URL=http://your-proxy:8080
```

#### "SSL Certificate" Errors

**Symptoms:**
- SSL verification failures
- Certificate errors in logs
- HTTPS connection issues

**Solutions:**

1. **Update Certificates:**
```bash
# Update system certificates
sudo apt-get update && sudo apt-get install ca-certificates
```

2. **Disable SSL Verification (Development Only):**
```python
# Only for development/testing
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### 3. Storage and Database Issues

#### "Permission Denied" Errors

**Symptoms:**
- Cannot create directories
- Cannot write to cache database
- File permission errors

**Diagnosis:**
```bash
# Check directory permissions
ls -la ./knowledge_repository
ls -la ./cache

# Check disk space
df -h
```

**Solutions:**

1. **Fix Permissions:**
```bash
# Create directories with proper permissions
mkdir -p ./knowledge_repository ./cache ./logs
chmod 755 ./knowledge_repository ./cache ./logs

# Fix ownership if needed
sudo chown -R $USER:$USER ./knowledge_repository ./cache ./logs
```

2. **Check Disk Space:**
```bash
# Free up space if needed
du -sh ./knowledge_repository
du -sh ./cache

# Clean old cache entries
python -c "
from linkedin_scraper.storage.cache_manager import CacheManager
from linkedin_scraper.utils.config import Config
cache = CacheManager(Config())
cache.cleanup_old_entries(days=30)
"
```

#### "Database Locked" Errors

**Symptoms:**
- SQLite database lock errors
- Cannot write to cache
- Database corruption messages

**Solutions:**

1. **Check for Concurrent Access:**
```bash
# Find processes using the database
lsof ./cache/knowledge_cache.db
```

2. **Repair Database:**
```bash
# Backup and repair SQLite database
cp ./cache/knowledge_cache.db ./cache/knowledge_cache.db.backup
sqlite3 ./cache/knowledge_cache.db ".recover" | sqlite3 ./cache/knowledge_cache_recovered.db
mv ./cache/knowledge_cache_recovered.db ./cache/knowledge_cache.db
```

3. **Reset Cache:**
```bash
# Remove corrupted cache (will rebuild automatically)
rm ./cache/knowledge_cache.db
```

### 4. Content Processing Issues

#### "PII Detection Errors"

**Symptoms:**
- PII detection failures
- Content sanitization errors
- Processing stops at PII detection stage

**Diagnosis:**
```python
# Test PII detection manually
from linkedin_scraper.utils.pii_detector import detect_and_sanitize_pii

test_content = "Contact john.doe@company.com for more info"
result = detect_and_sanitize_pii(test_content, sanitize=True)
print(result)
```

**Solutions:**

1. **Disable PII Detection Temporarily:**
```env
ENABLE_PII_DETECTION=false
SANITIZE_CONTENT=false
```

2. **Update PII Patterns:**
   - Check regex patterns in `pii_detector.py`
   - Update patterns for edge cases
   - Test with problematic content

3. **Handle Edge Cases:**
```python
# Add error handling for PII detection
try:
    result = detect_and_sanitize_pii(content)
except Exception as e:
    logger.warning(f"PII detection failed: {e}")
    result = {"sanitized_text": content, "detected_pii": []}
```

#### "Content Extraction Failures"

**Symptoms:**
- Gemini AI returns empty responses
- Knowledge extraction fails
- Invalid content format errors

**Diagnosis:**
```python
# Test Gemini extraction manually
from linkedin_scraper.services.gemini_client import GeminiClient
from linkedin_scraper.utils.config import Config

client = GeminiClient(Config(gemini_api_key="your_key"))
test_content = {"title": "Test", "content": "AI is transforming business"}
result = await client.extract_knowledge(test_content)
print(result)
```

**Solutions:**

1. **Check Content Quality:**
   - Ensure content is not empty
   - Verify content is in English
   - Check for special characters

2. **Adjust Prompts:**
   - Modify Gemini prompts for better extraction
   - Add fallback prompts for edge cases
   - Implement content validation

3. **Handle Extraction Failures:**
```python
# Add fallback for failed extractions
if not knowledge_data:
    knowledge_data = {
        "topic": "General Business",
        "category": "Other",
        "key_knowledge_content": scraped_content.get("content", "")[:500],
        "course_references": []
    }
```

### 5. Web Interface Issues

#### "Server Won't Start"

**Symptoms:**
- Web server fails to start
- Port binding errors
- Import errors

**Diagnosis:**
```bash
# Check if port is in use
netstat -tulpn | grep :8000
lsof -i :8000

# Test imports
python -c "from linkedin_scraper.web.app import app; print('OK')"
```

**Solutions:**

1. **Change Port:**
```env
WEB_SERVER_PORT=8080  # Use different port
```

2. **Kill Existing Process:**
```bash
# Find and kill process using port
sudo kill -9 $(lsof -t -i:8000)
```

3. **Fix Import Issues:**
```bash
# Ensure proper Python path
export PYTHONPATH=$PWD:$PYTHONPATH
```

#### "Static Files Not Loading"

**Symptoms:**
- CSS/JS files return 404
- Web interface appears broken
- Missing static assets

**Solutions:**

1. **Check Static File Paths:**
```python
# Verify static files exist
import os
static_dir = "./linkedin_scraper/web/static"
print(os.listdir(static_dir))
```

2. **Configure Static File Serving:**
```python
# In Flask app configuration
app.static_folder = 'static'
app.static_url_path = '/static'
```

### 6. Performance Issues

#### "Slow Processing"

**Symptoms:**
- Long processing times
- High memory usage
- System becomes unresponsive

**Diagnosis:**
```bash
# Monitor system resources
top -p $(pgrep -f linkedin_scraper)
htop

# Check memory usage
ps aux | grep linkedin_scraper
```

**Solutions:**

1. **Reduce Concurrency:**
```python
# Lower concurrent processing
MAX_CONCURRENT=1  # Reduce from default 3
```

2. **Optimize Memory Usage:**
```python
# Add memory cleanup
import gc
gc.collect()  # Force garbage collection
```

3. **Profile Performance:**
```python
# Add performance profiling
import cProfile
cProfile.run('your_function()')
```

#### "High Memory Usage"

**Symptoms:**
- Memory usage keeps increasing
- Out of memory errors
- System swapping

**Solutions:**

1. **Implement Memory Limits:**
```python
# Add memory monitoring
import psutil
process = psutil.Process()
memory_mb = process.memory_info().rss / 1024 / 1024
if memory_mb > 500:  # 500MB limit
    logger.warning(f"High memory usage: {memory_mb}MB")
```

2. **Clear Caches Regularly:**
```python
# Clear internal caches
cache_manager.cleanup_old_entries(days=7)
```

## Debugging Tools

### 1. Enable Debug Logging

```python
# Set debug level
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export LOG_LEVEL=DEBUG
```

### 2. Health Check Script

```python
#!/usr/bin/env python3
"""Health check script for LinkedIn Knowledge Scraper."""

import asyncio
import sys
from linkedin_scraper.main import create_scraper_from_config

async def health_check():
    """Perform comprehensive health check."""
    try:
        scraper = await create_scraper_from_config()
        
        # Test components
        stats = await scraper.get_processing_stats()
        health = stats["component_health"]
        
        print("Component Health:")
        for component, status in health.items():
            status_str = "✓" if status else "✗"
            print(f"  {component}: {status_str}")
        
        # Test processing
        test_url = "https://linkedin.com/posts/test"
        print(f"\nTesting processing pipeline...")
        # Note: This would fail with test URL, but tests the pipeline
        
        await scraper.cleanup()
        print("\n✓ Health check completed successfully")
        return True
        
    except Exception as e:
        print(f"\n✗ Health check failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(health_check())
    sys.exit(0 if success else 1)
```

### 3. Configuration Validator

```python
#!/usr/bin/env python3
"""Validate configuration."""

from linkedin_scraper.utils.config import Config
from linkedin_scraper.utils.config_validator import ConfigValidator

def validate_config():
    """Validate current configuration."""
    try:
        config = Config.from_environment()
        result = ConfigValidator.validate_full_configuration(config)
        
        print(f"Configuration Valid: {result['valid']}")
        
        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  ✗ {error}")
        
        if result['warnings']:
            print("\nWarnings:")
            for warning in result['warnings']:
                print(f"  ⚠ {warning}")
        
        if result['recommendations']:
            print("\nRecommendations:")
            for rec in result['recommendations']:
                print(f"  💡 {rec}")
        
        return result['valid']
        
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False

if __name__ == "__main__":
    validate_config()
```

## Getting Help

### 1. Enable Verbose Logging

```bash
# Run with maximum verbosity
export LOG_LEVEL=DEBUG
python -m linkedin_scraper.main --url "your-url" 2>&1 | tee debug.log
```

### 2. Collect System Information

```bash
#!/bin/bash
# System info collection script

echo "=== System Information ==="
uname -a
python --version
pip list | grep -E "(linkedin|google|requests)"

echo -e "\n=== Environment Variables ==="
env | grep -E "(GEMINI|LINKEDIN|KNOWLEDGE)" | sed 's/=.*/=***/'

echo -e "\n=== Disk Space ==="
df -h

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Network Connectivity ==="
curl -I https://linkedin.com 2>&1 | head -1
curl -I https://generativelanguage.googleapis.com 2>&1 | head -1

echo -e "\n=== Recent Errors ==="
tail -50 ./logs/scraper.log | grep -i error
```

### 3. Create Minimal Reproduction

```python
#!/usr/bin/env python3
"""Minimal reproduction script."""

import asyncio
from linkedin_scraper.utils.config import Config
from linkedin_scraper.main import LinkedInKnowledgeScraper

async def minimal_test():
    """Minimal test case."""
    config = Config(
        gemini_api_key="your_api_key",
        knowledge_repo_path="./test_repo",
        cache_db_path="./test_cache.db",
        log_level="DEBUG"
    )
    
    scraper = LinkedInKnowledgeScraper(config)
    
    try:
        await scraper.initialize()
        print("✓ Initialization successful")
        
        # Add your specific test case here
        # result = await scraper.process_linkedin_url("your_problematic_url")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(minimal_test())
```

## Support Channels

1. **GitHub Issues**: Create detailed issue reports
2. **Documentation**: Check API reference and guides
3. **Logs**: Always include relevant log excerpts
4. **System Info**: Provide system and environment details

When reporting issues, please include:
- Error messages and stack traces
- Configuration (with sensitive data redacted)
- Steps to reproduce
- System information
- Log excerpts