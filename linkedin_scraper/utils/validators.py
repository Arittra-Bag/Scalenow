"""Validation utilities for URLs and content."""

import re
from typing import Optional
from urllib.parse import urlparse

from ..models.exceptions import ValidationError


class URLValidator:
    """Validator for LinkedIn URLs and other content validation."""
    
    # LinkedIn URL patterns
    LINKEDIN_POST_PATTERNS = [
        r'https?://(?:www\.)?linkedin\.com/posts/[^/]+_[^/]+',
        r'https?://(?:www\.)?linkedin\.com/feed/update/urn:li:activity:\d+',
        r'https?://(?:www\.)?linkedin\.com/pulse/[^/]+',
    ]
    
    # PII detection patterns
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    @classmethod
    def is_valid_linkedin_url(cls, url: str) -> bool:
        """Check if URL is a valid LinkedIn post URL."""
        if not url or not isinstance(url, str):
            return False
        
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except Exception:
            return False
        
        # Check against LinkedIn patterns
        for pattern in cls.LINKEDIN_POST_PATTERNS:
            if re.match(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def validate_linkedin_url(cls, url: str) -> str:
        """Validate and normalize LinkedIn URL."""
        if not cls.is_valid_linkedin_url(url):
            raise ValidationError(
                f"Invalid LinkedIn URL format: {url}",
                field="url",
                value=url
            )
        
        # Normalize URL (remove tracking parameters, etc.)
        return cls._normalize_url(url)
    
    @classmethod
    def _normalize_url(cls, url: str) -> str:
        """Normalize LinkedIn URL by removing tracking parameters."""
        # Remove common tracking parameters
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
        
        parsed = urlparse(url)
        if parsed.query:
            # Filter out tracking parameters
            query_parts = []
            for part in parsed.query.split('&'):
                if '=' in part:
                    key, _ = part.split('=', 1)
                    if key not in tracking_params:
                        query_parts.append(part)
            
            # Reconstruct URL
            new_query = '&'.join(query_parts)
            url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if new_query:
                url += f"?{new_query}"
        
        return url
    
    @classmethod
    def extract_post_id(cls, url: str) -> Optional[str]:
        """Extract post ID from LinkedIn URL."""
        if not cls.is_valid_linkedin_url(url):
            return None
        
        # Try to extract activity ID from different URL formats
        patterns = [
            r'urn:li:activity:(\d+)',
            r'/posts/[^/]+_([^/?]+)',
            r'/pulse/([^/?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @classmethod
    def detect_pii(cls, text: str) -> dict:
        """Detect potential PII in text content."""
        if not text:
            return {'emails': [], 'phones': []}
        
        emails = re.findall(cls.EMAIL_PATTERN, text)
        phones = re.findall(cls.PHONE_PATTERN, text)
        
        return {
            'emails': emails,
            'phones': phones
        }
    
    @classmethod
    def sanitize_pii(cls, text: str) -> str:
        """Remove or mask PII from text content."""
        if not text:
            return text
        
        # Mask emails
        text = re.sub(cls.EMAIL_PATTERN, '[EMAIL_REDACTED]', text)
        
        # Mask phone numbers
        text = re.sub(cls.PHONE_PATTERN, '[PHONE_REDACTED]', text)
        
        return text
    
    @classmethod
    def validate_content_length(cls, content: str, max_length: int = 10000) -> None:
        """Validate content length."""
        if not content:
            raise ValidationError("Content cannot be empty", field="content")
        
        if len(content) > max_length:
            raise ValidationError(
                f"Content too long: {len(content)} characters (max: {max_length})",
                field="content",
                value=str(len(content))
            )
    
    @classmethod
    def is_valid_filename(cls, filename: str) -> bool:
        """Check if filename is valid for file system."""
        if not filename:
            return False
        
        # Check for invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, filename):
            return False
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        if filename.upper() in reserved_names:
            return False
        
        return True
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for file system compatibility."""
        if not filename:
            return "untitled"
        
        # Replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        # Ensure it's not a reserved name
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        if filename.upper() in reserved_names:
            filename = f"file_{filename}"
        
        return filename