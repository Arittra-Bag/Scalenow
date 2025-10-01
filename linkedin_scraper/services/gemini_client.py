"""Gemini API client with rate limiting and error handling."""

import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    genai = None
    HarmCategory = None
    HarmBlockThreshold = None

from ..models.exceptions import APIError, ConfigurationError
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int, requests_per_day: int):
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        
        # Track requests
        self.minute_requests = []
        self.daily_requests = []
        
        # Token tracking
        self.daily_tokens = 0
        self.daily_token_reset = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    async def wait_if_needed(self) -> None:
        """Wait if rate limits would be exceeded."""
        now = datetime.now()
        
        # Clean old requests
        self._clean_old_requests(now)
        
        # Check minute limit
        if len(self.minute_requests) >= self.requests_per_minute:
            wait_time = 60 - (now - self.minute_requests[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s for minute limit")
                await asyncio.sleep(wait_time)
                self._clean_old_requests(datetime.now())
        
        # Check daily limit
        if len(self.daily_requests) >= self.requests_per_day:
            # Wait until next day
            wait_time = (now.replace(hour=23, minute=59, second=59) - now).total_seconds() + 1
            logger.warning(f"Daily rate limit reached, waiting {wait_time/3600:.1f} hours")
            await asyncio.sleep(wait_time)
            self._clean_old_requests(datetime.now())
    
    def record_request(self, tokens_used: int = 0) -> None:
        """Record a successful request."""
        now = datetime.now()
        self.minute_requests.append(now)
        self.daily_requests.append(now)
        
        # Track tokens
        if now >= self.daily_token_reset:
            self.daily_tokens = 0
            self.daily_token_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        self.daily_tokens += tokens_used
    
    def _clean_old_requests(self, now: datetime) -> None:
        """Remove old requests from tracking."""
        # Remove requests older than 1 minute
        minute_ago = now - timedelta(minutes=1)
        self.minute_requests = [req for req in self.minute_requests if req > minute_ago]
        
        # Remove requests older than 1 day
        day_ago = now - timedelta(days=1)
        self.daily_requests = [req for req in self.daily_requests if req > day_ago]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        now = datetime.now()
        self._clean_old_requests(now)
        
        return {
            'requests_this_minute': len(self.minute_requests),
            'requests_per_minute_limit': self.requests_per_minute,
            'requests_today': len(self.daily_requests),
            'requests_per_day_limit': self.requests_per_day,
            'tokens_today': self.daily_tokens,
            'token_reset_time': self.daily_token_reset.isoformat()
        }


class GeminiClient:
    """Client for Google Gemini API with rate limiting and error handling."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the Gemini client."""
        self.config = config or Config.from_env()
        
        if genai is None:
            raise ConfigurationError(
                "Google Generative AI library not installed. "
                "Please install it with: pip install google-generativeai"
            )
        
        # Configure the API
        genai.configure(api_key=self.config.gemini_api_key)
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.config.gemini_rate_limit_rpm,
            requests_per_day=self.config.gemini_rate_limit_rpd
        )
        
        # Initialize model
        self.model = None
        self._initialize_model()
        
        logger.info(f"Gemini client initialized with model: {self.config.gemini_model}")
    
    def _initialize_model(self) -> None:
        """Initialize the Gemini model with safety settings."""
        try:
            # Configure safety settings to be less restrictive for business content
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Generation configuration
            generation_config = {
                "temperature": 0.3,  # Lower temperature for more consistent results
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            self.model = genai.GenerativeModel(
                model_name=self.config.gemini_model,
                safety_settings=safety_settings,
                generation_config=generation_config
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize Gemini model: {e}")
    
    async def generate_content(
        self,
        prompt: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> str:
        """Generate content using Gemini API with retries."""
        
        for attempt in range(max_retries):
            try:
                # Wait for rate limiting
                await self.rate_limiter.wait_if_needed()
                
                # Make the API call
                logger.debug(f"Making Gemini API call (attempt {attempt + 1})")
                response = await self._make_api_call(prompt)
                
                # Record successful request
                self.rate_limiter.record_request(tokens_used=len(prompt.split()) + len(response.split()))
                
                logger.debug(f"Gemini API call successful, response length: {len(response)}")
                return response
                
            except Exception as e:
                logger.warning(f"Gemini API call failed (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise APIError(
                        f"Gemini API failed after {max_retries} attempts: {e}",
                        api_name="Gemini",
                        error_code=str(type(e).__name__)
                    )
    
    async def _make_api_call(self, prompt: str) -> str:
        """Make the actual API call to Gemini."""
        try:
            # Use asyncio to run the synchronous API call
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            
            # Check if response was blocked
            if not response.text:
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    feedback = response.prompt_feedback
                    raise APIError(
                        f"Content generation blocked: {feedback.block_reason}",
                        api_name="Gemini",
                        error_code="CONTENT_BLOCKED"
                    )
                else:
                    raise APIError(
                        "Empty response from Gemini API",
                        api_name="Gemini",
                        error_code="EMPTY_RESPONSE"
                    )
            
            return response.text.strip()
            
        except Exception as e:
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                raise APIError(
                    f"Gemini API quota/rate limit exceeded: {e}",
                    api_name="Gemini",
                    error_code="QUOTA_EXCEEDED"
                )
            elif "safety" in str(e).lower():
                raise APIError(
                    f"Content blocked by safety filters: {e}",
                    api_name="Gemini",
                    error_code="SAFETY_BLOCKED"
                )
            else:
                raise APIError(
                    f"Gemini API error: {e}",
                    api_name="Gemini",
                    error_code="API_ERROR"
                )
    
    async def batch_generate(
        self,
        prompts: List[str],
        batch_delay: float = 1.0
    ) -> List[str]:
        """Generate content for multiple prompts with delays between requests."""
        results = []
        
        for i, prompt in enumerate(prompts):
            try:
                result = await self.generate_content(prompt)
                results.append(result)
                
                # Add delay between batch requests (except for the last one)
                if i < len(prompts) - 1:
                    await asyncio.sleep(batch_delay)
                    
            except Exception as e:
                logger.error(f"Failed to process prompt {i + 1}: {e}")
                results.append("")  # Add empty result to maintain order
        
        return results
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return self.rate_limiter.get_status()
    
    async def test_connection(self) -> bool:
        """Test the connection to Gemini API."""
        try:
            test_prompt = "Hello, please respond with 'Connection successful'"
            response = await self.generate_content(test_prompt)
            
            if "successful" in response.lower() or "hello" in response.lower():
                logger.info("Gemini API connection test successful")
                return True
            else:
                logger.warning(f"Unexpected test response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False
    
    def create_prompt_template(self, template_name: str) -> str:
        """Get predefined prompt templates for different tasks."""
        templates = {
            "knowledge_extraction": """
You are an expert content analyst. Extract valuable knowledge and insights from the following LinkedIn post content, filtering out marketing language and promotional content.

Content to analyze:
{content}

Please provide:
1. Key knowledge insights (factual information, strategies, best practices)
2. Main topic/domain (AI, SaaS, Marketing, Leadership, Technology, etc.)
3. Any course or educational references mentioned
4. Summary of actionable takeaways

Focus only on educational and informational content. Ignore calls-to-action, promotional language, and engagement requests.

Response format:
KNOWLEDGE: [extracted knowledge content]
TOPIC: [main topic/domain]
COURSES: [any educational references]
SUMMARY: [brief summary of key takeaways]
""",
            
            "content_categorization": """
Categorize the following content into one of these categories:
- AI & Machine Learning
- SaaS & Business  
- Marketing & Sales
- Leadership & Management
- Technology Trends
- Course Content
- Other

Content: {content}

Respond with only the category name.
""",
            
            "insight_extraction": """
Extract the top 3-5 key insights from this content that would be valuable for business professionals:

Content: {content}

Format each insight as a bullet point, focusing on actionable information, statistics, strategies, or important concepts.
""",
            
            "course_detection": """
Identify any courses, training programs, certifications, or educational content mentioned in this text:

Content: {content}

List only the specific course/program names mentioned. If none are found, respond with "None".
"""
        }
        
        return templates.get(template_name, "")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check of the Gemini client."""
        health_status = {
            "status": "unknown",
            "api_connection": False,
            "rate_limits": self.get_rate_limit_status(),
            "model": self.config.gemini_model,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test API connection
            health_status["api_connection"] = await self.test_connection()
            
            if health_status["api_connection"]:
                health_status["status"] = "healthy"
            else:
                health_status["status"] = "degraded"
                
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status