"""LinkedIn URL parsing and validation utilities."""

import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass

from ..models.exceptions import ValidationError
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LinkedInPostInfo:
    """Information extracted from a LinkedIn post URL."""
    url: str
    post_type: str  # 'activity', 'pulse', 'posts'
    post_id: str
    author_id: Optional[str] = None
    normalized_url: str = None
    
    def __post_init__(self):
        if self.normalized_url is None:
            self.normalized_url = self.url


class LinkedInURLParser:
    """Parser and validator for LinkedIn URLs."""
    
    # LinkedIn post URL patterns with named groups
    URL_PATTERNS = {
        'activity': r'https?://(?:www\.)?linkedin\.com/feed/update/urn:li:activity:(?P<post_id>\d+)',
        'posts': r'https?://(?:www\.)?linkedin\.com/posts/(?P<author_id>[^/]+)_(?P<post_id>[^/?]+)',
        'pulse': r'https?://(?:www\.)?linkedin\.com/pulse/(?P<post_id>[^/?]+)',
        'company_posts': r'https?://(?:www\.)?linkedin\.com/company/[^/]+/posts/(?P<post_id>[^/?]+)',
    }
    
    # Tracking parameters to remove during normalization
    TRACKING_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
        'trackingId', 'lipi', 'licu', 'trk', 'trkInfo', 'originalSubdomain'
    }
    
    @classmethod
    def parse_url(cls, url: str) -> LinkedInPostInfo:
        """Parse a LinkedIn URL and extract post information."""
        if not url or not isinstance(url, str):
            raise ValidationError("URL must be a non-empty string", field="url", value=str(url))
        
        # Clean and normalize the URL first
        cleaned_url = cls._clean_url(url)
        
        # Try to match against known patterns
        for post_type, pattern in cls.URL_PATTERNS.items():
            match = re.match(pattern, cleaned_url, re.IGNORECASE)
            if match:
                groups = match.groupdict()
                
                post_info = LinkedInPostInfo(
                    url=url,
                    post_type=post_type,
                    post_id=groups['post_id'],
                    author_id=groups.get('author_id'),
                    normalized_url=cleaned_url
                )
                
                logger.debug(f"Parsed LinkedIn URL: {post_type} post {post_info.post_id}")
                return post_info
        
        # If no pattern matches, raise validation error
        raise ValidationError(
            f"Invalid LinkedIn post URL format: {url}",
            field="url",
            value=url
        )
    
    @classmethod
    def is_valid_linkedin_url(cls, url: str) -> bool:
        """Check if URL is a valid LinkedIn post URL."""
        try:
            cls.parse_url(url)
            return True
        except ValidationError:
            return False
    
    @classmethod
    def _clean_url(cls, url: str) -> str:
        """Clean and normalize LinkedIn URL."""
        # Basic URL validation
        try:
            parsed = urlparse(url.strip())
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {e}", field="url", value=url)
        
        if not parsed.scheme:
            # Add https if no scheme provided
            url = f"https://{url}"
            parsed = urlparse(url)
        
        if not parsed.netloc:
            raise ValidationError("URL must have a valid domain", field="url", value=url)
        
        # Ensure it's a LinkedIn domain
        if not cls._is_linkedin_domain(parsed.netloc):
            raise ValidationError(
                f"URL must be from LinkedIn domain, got: {parsed.netloc}",
                field="url",
                value=url
            )
        
        # Remove tracking parameters
        if parsed.query:
            query_params = parse_qs(parsed.query)
            # Filter out tracking parameters
            clean_params = {
                key: value for key, value in query_params.items()
                if key not in cls.TRACKING_PARAMS
            }
            
            # Reconstruct query string
            if clean_params:
                query_parts = []
                for key, values in clean_params.items():
                    for value in values:
                        query_parts.append(f"{key}={value}")
                clean_query = "&".join(query_parts)
            else:
                clean_query = ""
        else:
            clean_query = ""
        
        # Reconstruct clean URL
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_query:
            clean_url += f"?{clean_query}"
        
        # Remove trailing slash if present
        if clean_url.endswith('/'):
            clean_url = clean_url[:-1]
        
        return clean_url
    
    @classmethod
    def _is_linkedin_domain(cls, domain: str) -> bool:
        """Check if domain is a valid LinkedIn domain."""
        linkedin_domains = [
            'linkedin.com',
            'www.linkedin.com',
            'm.linkedin.com',
            'mobile.linkedin.com'
        ]
        return domain.lower() in linkedin_domains
    
    @classmethod
    def extract_post_metadata(cls, url: str) -> Dict[str, str]:
        """Extract additional metadata from LinkedIn URL."""
        post_info = cls.parse_url(url)
        
        metadata = {
            'post_type': post_info.post_type,
            'post_id': post_info.post_id,
            'normalized_url': post_info.normalized_url
        }
        
        if post_info.author_id:
            metadata['author_id'] = post_info.author_id
        
        # Extract additional info based on post type
        if post_info.post_type == 'posts' and post_info.author_id:
            # Try to extract author name from author_id (often contains name)
            author_parts = post_info.author_id.replace('-', ' ').replace('_', ' ')
            metadata['author_hint'] = author_parts
        
        return metadata
    
    @classmethod
    def generate_cache_key(cls, url: str) -> str:
        """Generate a consistent cache key for a LinkedIn URL."""
        try:
            post_info = cls.parse_url(url)
            return f"{post_info.post_type}:{post_info.post_id}"
        except ValidationError:
            # Fallback to URL hash if parsing fails
            import hashlib
            return f"url:{hashlib.md5(url.encode()).hexdigest()}"
    
    @classmethod
    def get_post_web_url(cls, post_info: LinkedInPostInfo) -> str:
        """Get the web-accessible URL for a post (for scraping)."""
        # Some LinkedIn URLs might need conversion for web scraping
        if post_info.post_type == 'activity':
            # Activity URLs are already web-accessible
            return post_info.normalized_url
        elif post_info.post_type == 'posts':
            # Posts URLs are already web-accessible
            return post_info.normalized_url
        elif post_info.post_type == 'pulse':
            # Pulse articles are already web-accessible
            return post_info.normalized_url
        else:
            # Default to normalized URL
            return post_info.normalized_url
    
    @classmethod
    def validate_batch_urls(cls, urls: list) -> Tuple[list, list]:
        """Validate a batch of URLs and return valid/invalid lists."""
        valid_urls = []
        invalid_urls = []
        
        for url in urls:
            try:
                post_info = cls.parse_url(url)
                valid_urls.append({
                    'original_url': url,
                    'post_info': post_info
                })
            except ValidationError as e:
                invalid_urls.append({
                    'url': url,
                    'error': str(e)
                })
        
        logger.info(f"URL validation: {len(valid_urls)} valid, {len(invalid_urls)} invalid")
        return valid_urls, invalid_urls