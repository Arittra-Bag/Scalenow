"""LinkedIn web scraper using Playwright for content extraction."""

import asyncio
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
import requests
from urllib.parse import urljoin, urlparse

try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
except ImportError:
    # Fallback message if Playwright is not installed
    async_playwright = None
    Browser = None
    Page = None
    PlaywrightTimeoutError = Exception

from ..models.post_content import PostContent, ImageData, EngagementData
from ..models.exceptions import ScrapingError
from ..utils.config import Config
from ..utils.logger import get_logger
from .url_parser import LinkedInURLParser, LinkedInPostInfo

logger = get_logger(__name__)


class LinkedInScraper:
    """Web scraper for LinkedIn posts using Playwright."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the LinkedIn scraper."""
        self.config = config or Config.from_env()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # CSS selectors for LinkedIn elements
        self.selectors = {
            'post_content': '[data-id*="urn:li:activity"] .feed-shared-update-v2__description',
            'post_text': '.feed-shared-text__text-view',
            'post_author': '.feed-shared-actor__name',
            'post_date': '.feed-shared-actor__sub-description time',
            'post_images': '.feed-shared-image img, .feed-shared-carousel img',
            'engagement_likes': '[data-test-id="social-counts-likes"]',
            'engagement_comments': '[data-test-id="social-counts-comments"]',
            'engagement_shares': '[data-test-id="social-counts-shares"]',
            'article_title': 'h1.article-title, h1[data-test-id="article-title"]',
            'article_content': '.article-content, [data-test-id="article-content"]',
            'article_author': '.article-author, [data-test-id="article-author"]'
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_browser()
    
    async def start_browser(self) -> None:
        """Start the Playwright browser."""
        if async_playwright is None:
            raise ScrapingError("Playwright is not installed. Please install it with: pip install playwright")
        
        try:
            playwright = await async_playwright().start()
            
            # Launch browser with appropriate settings
            self.browser = await playwright.chromium.launch(
                headless=True,  # Set to False for debugging
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create a new page with realistic settings
            self.page = await self.browser.new_page(
                user_agent=self.config.user_agent,
                viewport={'width': 1920, 'height': 1080}
            )
            
            # Set additional headers to appear more like a real browser
            await self.page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            logger.info("Browser started successfully")
            
        except Exception as e:
            raise ScrapingError(f"Failed to start browser: {e}")
    
    async def close_browser(self) -> None:
        """Close the browser and cleanup."""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
    
    async def scrape_post(self, url: str) -> PostContent:
        """Scrape a LinkedIn post and return structured content."""
        if not self.browser or not self.page:
            raise ScrapingError("Browser not initialized. Use async context manager or call start_browser()")
        
        # Parse and validate URL
        try:
            post_info = LinkedInURLParser.parse_url(url)
            scraping_url = LinkedInURLParser.get_post_web_url(post_info)
        except Exception as e:
            raise ScrapingError(f"Invalid LinkedIn URL: {e}", url=url)
        
        logger.info(f"Scraping LinkedIn post: {scraping_url}")
        
        try:
            # Navigate to the post
            await self.page.goto(scraping_url, wait_until='networkidle', timeout=30000)
            
            # Wait for content to load
            await asyncio.sleep(self.config.scraping_delay_seconds)
            
            # Extract content based on post type
            if post_info.post_type == 'pulse':
                return await self._scrape_pulse_article(url, post_info)
            else:
                return await self._scrape_feed_post(url, post_info)
                
        except PlaywrightTimeoutError:
            raise ScrapingError("Page load timeout", url=url, status_code=408)
        except Exception as e:
            raise ScrapingError(f"Failed to scrape post: {e}", url=url)
    
    async def _scrape_feed_post(self, original_url: str, post_info: LinkedInPostInfo) -> PostContent:
        """Scrape a regular LinkedIn feed post."""
        try:
            # Extract post text
            post_text = await self._extract_text_content()
            
            # Extract author information
            author = await self._extract_author()
            
            # Extract post date
            post_date = await self._extract_post_date()
            
            # Extract images
            images = await self._extract_images()
            
            # Extract engagement metrics
            engagement = await self._extract_engagement_metrics()
            
            # Generate title from post content
            title = self._generate_title_from_content(post_text)
            
            return PostContent(
                url=original_url,
                title=title,
                body_text=post_text,
                author=author,
                post_date=post_date,
                images=images,
                engagement_metrics=engagement
            )
            
        except Exception as e:
            raise ScrapingError(f"Failed to extract feed post content: {e}", url=original_url)
    
    async def _scrape_pulse_article(self, original_url: str, post_info: LinkedInPostInfo) -> PostContent:
        """Scrape a LinkedIn Pulse article."""
        try:
            # Extract article title
            title_element = await self.page.query_selector(self.selectors['article_title'])
            title = await title_element.inner_text() if title_element else "LinkedIn Article"
            
            # Extract article content
            content_element = await self.page.query_selector(self.selectors['article_content'])
            content = await content_element.inner_text() if content_element else ""
            
            # Extract author
            author_element = await self.page.query_selector(self.selectors['article_author'])
            author = await author_element.inner_text() if author_element else "Unknown Author"
            
            # Extract images from article
            images = await self._extract_images()
            
            # For articles, we don't typically have engagement metrics in the same format
            engagement = EngagementData()
            
            # Use current time as post date (articles don't always show clear dates)
            from datetime import datetime
            post_date = datetime.now()
            
            return PostContent(
                url=original_url,
                title=title.strip(),
                body_text=content.strip(),
                author=author.strip(),
                post_date=post_date,
                images=images,
                engagement_metrics=engagement
            )
            
        except Exception as e:
            raise ScrapingError(f"Failed to extract article content: {e}", url=original_url)
    
    async def _extract_text_content(self) -> str:
        """Extract the main text content from a post."""
        try:
            # Try multiple selectors for post content
            selectors_to_try = [
                self.selectors['post_text'],
                self.selectors['post_content'],
                '.feed-shared-update-v2__description-wrapper',
                '[data-test-id="main-feed-activity-card"] .break-words'
            ]
            
            for selector in selectors_to_try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    texts = []
                    for element in elements:
                        text = await element.inner_text()
                        if text.strip():
                            texts.append(text.strip())
                    
                    if texts:
                        return '\n\n'.join(texts)
            
            # Fallback: get any text content from the page
            logger.warning("Could not find post content with standard selectors, using fallback")
            body_text = await self.page.inner_text('body')
            return body_text[:1000] if body_text else ""  # Limit fallback text
            
        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return ""
    
    async def _extract_author(self) -> str:
        """Extract the author name from a post."""
        try:
            author_element = await self.page.query_selector(self.selectors['post_author'])
            if author_element:
                author = await author_element.inner_text()
                return author.strip()
            
            # Fallback selectors
            fallback_selectors = [
                '.feed-shared-actor__name a',
                '[data-test-id="actor-name"]',
                '.article-author-name'
            ]
            
            for selector in fallback_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    author = await element.inner_text()
                    if author.strip():
                        return author.strip()
            
            return "Unknown Author"
            
        except Exception as e:
            logger.error(f"Error extracting author: {e}")
            return "Unknown Author"
    
    async def _extract_post_date(self):
        """Extract the post date."""
        try:
            from datetime import datetime
            
            date_element = await self.page.query_selector(self.selectors['post_date'])
            if date_element:
                # Try to get datetime attribute first
                datetime_attr = await date_element.get_attribute('datetime')
                if datetime_attr:
                    return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                
                # Fallback to text content
                date_text = await date_element.inner_text()
                # This would need more sophisticated date parsing
                # For now, return current time
                return datetime.now()
            
            return datetime.now()
            
        except Exception as e:
            logger.error(f"Error extracting post date: {e}")
            from datetime import datetime
            return datetime.now()
    
    async def _extract_images(self) -> List[ImageData]:
        """Extract images from a post."""
        images = []
        
        try:
            img_elements = await self.page.query_selector_all(self.selectors['post_images'])
            
            for i, img_element in enumerate(img_elements):
                try:
                    src = await img_element.get_attribute('src')
                    alt = await img_element.get_attribute('alt') or ""
                    
                    if src and self._is_valid_image_url(src):
                        # Generate filename
                        filename = f"linkedin_image_{i+1}.jpg"
                        
                        image_data = ImageData(
                            url=src,
                            filename=filename,
                            alt_text=alt,
                            description=f"Image {i+1} from LinkedIn post"
                        )
                        images.append(image_data)
                        
                except Exception as e:
                    logger.warning(f"Error processing image {i}: {e}")
                    continue
            
            logger.info(f"Extracted {len(images)} images from post")
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return []
    
    async def _extract_engagement_metrics(self) -> EngagementData:
        """Extract engagement metrics (likes, comments, shares)."""
        try:
            engagement = EngagementData()
            
            # Extract likes
            likes_element = await self.page.query_selector(self.selectors['engagement_likes'])
            if likes_element:
                likes_text = await likes_element.inner_text()
                engagement.likes = self._parse_engagement_number(likes_text)
            
            # Extract comments
            comments_element = await self.page.query_selector(self.selectors['engagement_comments'])
            if comments_element:
                comments_text = await comments_element.inner_text()
                engagement.comments = self._parse_engagement_number(comments_text)
            
            # Extract shares
            shares_element = await self.page.query_selector(self.selectors['engagement_shares'])
            if shares_element:
                shares_text = await shares_element.inner_text()
                engagement.shares = self._parse_engagement_number(shares_text)
            
            return engagement
            
        except Exception as e:
            logger.error(f"Error extracting engagement metrics: {e}")
            return EngagementData()
    
    def _parse_engagement_number(self, text: str) -> int:
        """Parse engagement number from text (e.g., '1.2K' -> 1200)."""
        if not text:
            return 0
        
        # Remove non-numeric characters except K, M, B
        import re
        clean_text = re.sub(r'[^\d.KMB]', '', text.upper())
        
        if not clean_text:
            return 0
        
        try:
            if 'K' in clean_text:
                return int(float(clean_text.replace('K', '')) * 1000)
            elif 'M' in clean_text:
                return int(float(clean_text.replace('M', '')) * 1000000)
            elif 'B' in clean_text:
                return int(float(clean_text.replace('B', '')) * 1000000000)
            else:
                return int(float(clean_text))
        except (ValueError, TypeError):
            return 0
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image URL."""
        if not url:
            return False
        
        # Skip data URLs, SVGs, and very small images
        if url.startswith('data:') or 'svg' in url.lower():
            return False
        
        # Check for common image extensions or LinkedIn image patterns
        image_patterns = [
            r'\.jpg', r'\.jpeg', r'\.png', r'\.gif', r'\.webp',
            r'media\.licdn\.com', r'cdn\.lynda\.com'
        ]
        
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in image_patterns)
    
    def _generate_title_from_content(self, content: str) -> str:
        """Generate a title from post content."""
        if not content:
            return "LinkedIn Post"
        
        # Take first sentence or first 100 characters
        sentences = content.split('.')
        if sentences and len(sentences[0]) > 10:
            title = sentences[0].strip()
            if len(title) > 100:
                title = title[:97] + "..."
            return title
        
        # Fallback to first 100 characters
        if len(content) > 100:
            return content[:97] + "..."
        
        return content.strip()
    
    async def download_image(self, image_data: ImageData, save_path: Path) -> bool:
        """Download an image and save it to the specified path."""
        if not self.config.enable_image_download:
            logger.info("Image download is disabled in configuration")
            return False
        
        try:
            # Create directory if it doesn't exist
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download image
            response = requests.get(
                image_data.url,
                headers={'User-Agent': self.config.user_agent},
                timeout=self.config.request_timeout_seconds,
                stream=True
            )
            response.raise_for_status()
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.config.max_image_size_mb * 1024 * 1024:
                logger.warning(f"Image too large: {content_length} bytes")
                return False
            
            # Save image
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Update image data with local path
            image_data.local_path = str(save_path)
            
            logger.info(f"Downloaded image: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download image {image_data.url}: {e}")
            return False