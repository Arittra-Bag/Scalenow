# API Reference

This document provides comprehensive API documentation for the LinkedIn Knowledge Scraper.

## Core Classes

### LinkedInKnowledgeScraper

Main application class that orchestrates all components.

```python
from linkedin_scraper.main import LinkedInKnowledgeScraper
from linkedin_scraper.utils.config import Config

config = Config(gemini_api_key="your_key")
scraper = LinkedInKnowledgeScraper(config)
```

#### Methods

##### `async initialize() -> None`

Initialize all components and dependencies.

```python
await scraper.initialize()
```

**Raises:**
- `ConfigurationError`: If configuration is invalid
- `ConnectionError`: If external services are unavailable

##### `async process_linkedin_url(url: str) -> Optional[KnowledgeItem]`

Process a single LinkedIn URL through the complete pipeline.

**Parameters:**
- `url` (str): LinkedIn post URL to process

**Returns:**
- `KnowledgeItem`: Processed knowledge item, or None if processing failed

**Example:**
```python
item = await scraper.process_linkedin_url("https://linkedin.com/posts/user/post-id")
if item:
    print(f"Processed: {item.post_title}")
```

##### `async process_multiple_urls(urls: List[str], max_concurrent: int = 3) -> List[KnowledgeItem]`

Process multiple LinkedIn URLs concurrently.

**Parameters:**
- `urls` (List[str]): List of LinkedIn URLs to process
- `max_concurrent` (int): Maximum number of concurrent processing tasks

**Returns:**
- `List[KnowledgeItem]`: List of successfully processed items

**Example:**
```python
urls = ["https://linkedin.com/posts/user1/post1", "https://linkedin.com/posts/user2/post2"]
results = await scraper.process_multiple_urls(urls, max_concurrent=2)
print(f"Processed {len(results)} items")
```

##### `async search_knowledge(query: str, category: Optional[str] = None, limit: int = 10) -> List[KnowledgeItem]`

Search stored knowledge items.

**Parameters:**
- `query` (str): Search query
- `category` (Optional[str]): Category filter
- `limit` (int): Maximum number of results

**Returns:**
- `List[KnowledgeItem]`: Matching knowledge items

**Example:**
```python
results = await scraper.search_knowledge("artificial intelligence", category="AI & Machine Learning")
```

##### `async get_knowledge_by_category(category: str, limit: int = 50) -> List[KnowledgeItem]`

Get knowledge items by category.

**Parameters:**
- `category` (str): Category to filter by
- `limit` (int): Maximum number of results

**Returns:**
- `List[KnowledgeItem]`: Knowledge items in the category

##### `async get_processing_stats() -> Dict[str, Any]`

Get current processing statistics.

**Returns:**
- `Dict[str, Any]`: Statistics including success/failure counts and component health

**Example:**
```python
stats = await scraper.get_processing_stats()
print(f"Total processed: {stats['total_processed']}")
print(f"Success rate: {stats['successful']}/{stats['total_processed']}")
```

##### `async cleanup() -> None`

Clean up resources and close connections.

```python
await scraper.cleanup()
```

## Configuration

### Config Class

```python
from linkedin_scraper.utils.config import Config

config = Config(
    gemini_api_key="your_api_key",
    knowledge_repo_path="./knowledge",
    cache_db_path="./cache.db",
    enable_pii_detection=True,
    sanitize_content=True
)
```

#### Parameters

##### Required
- `gemini_api_key` (str): Google Gemini API key

##### Optional - Paths
- `knowledge_repo_path` (str): Path to knowledge repository (default: "./knowledge_repository")
- `cache_db_path` (str): Path to cache database (default: "./cache/knowledge_cache.db")
- `log_file_path` (str): Path to log file (default: "./logs/scraper.log")

##### Optional - Behavior
- `environment` (str): Environment mode ("development", "production", "test")
- `enable_pii_detection` (bool): Enable PII detection (default: True)
- `sanitize_content` (bool): Sanitize detected PII (default: True)
- `log_level` (str): Logging level ("DEBUG", "INFO", "WARNING", "ERROR")

##### Optional - Rate Limiting
- `gemini_rate_limit_rpm` (int): Requests per minute limit (default: 60)
- `gemini_rate_limit_rpd` (int): Requests per day limit (default: 1000)

##### Optional - Web Interface
- `web_server_host` (str): Web server host (default: "localhost")
- `web_server_port` (int): Web server port (default: 8000)
- `web_server_debug` (bool): Enable debug mode (default: False)

#### Methods

##### `validate() -> None`

Validate configuration parameters.

**Raises:**
- `ConfigurationError`: If configuration is invalid

##### `create_directories() -> None`

Create necessary directories for the application.

##### `from_env(env_file: str) -> Config`

Create configuration from environment file.

**Parameters:**
- `env_file` (str): Path to environment file

**Returns:**
- `Config`: Configuration instance

##### `from_environment() -> Config`

Create configuration from environment variables.

**Returns:**
- `Config`: Configuration instance

## Data Models

### KnowledgeItem

Represents a processed knowledge item.

```python
from linkedin_scraper.models.knowledge_item import KnowledgeItem, Category

item = KnowledgeItem(
    post_title="AI in Business Operations",
    key_knowledge_content="AI transforms business operations...",
    topic="Artificial Intelligence",
    category=Category.AI_MACHINE_LEARNING,
    source_url="https://linkedin.com/posts/user/post",
    course_references=["AI for Business", "ML Fundamentals"]
)
```

#### Attributes

- `post_title` (str): Title of the LinkedIn post
- `key_knowledge_content` (str): Extracted key knowledge
- `topic` (str): Main topic of the content
- `category` (Category): Content category
- `source_url` (str): Original LinkedIn URL
- `course_references` (List[str]): Related course references
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp

#### Methods

##### `from_scraped_data(scraped_content: Dict, knowledge_data: Dict, source_url: str) -> KnowledgeItem`

Create KnowledgeItem from scraped and processed data.

**Parameters:**
- `scraped_content` (Dict): Raw scraped content
- `knowledge_data` (Dict): Processed knowledge data
- `source_url` (str): Source URL

**Returns:**
- `KnowledgeItem`: New knowledge item instance

##### `to_dict() -> Dict[str, Any]`

Convert to dictionary representation.

##### `to_markdown() -> str`

Convert to Markdown format.

### Category Enum

Content categories for classification.

```python
from linkedin_scraper.models.knowledge_item import Category

# Available categories
Category.AI_MACHINE_LEARNING
Category.SAAS_BUSINESS
Category.MARKETING_SALES
Category.LEADERSHIP_MANAGEMENT
Category.ENTREPRENEURSHIP
Category.TECHNOLOGY_TRENDS
Category.BUSINESS_STRATEGY
Category.PERSONAL_DEVELOPMENT
Category.INDUSTRY_INSIGHTS
Category.OTHER
```

## Services

### WebScraper

Handles LinkedIn content scraping.

```python
from linkedin_scraper.services.web_scraper import WebScraper

scraper = WebScraper(config)
content = await scraper.scrape_linkedin_post(url)
```

#### Methods

##### `async scrape_linkedin_post(url: str) -> Optional[Dict[str, Any]]`

Scrape content from LinkedIn post.

**Parameters:**
- `url` (str): LinkedIn post URL

**Returns:**
- `Optional[Dict]`: Scraped content or None if failed

### GeminiClient

Interfaces with Google's Gemini AI.

```python
from linkedin_scraper.services.gemini_client import GeminiClient

client = GeminiClient(config)
await client.initialize()
knowledge = await client.extract_knowledge(content)
```

#### Methods

##### `async initialize() -> None`

Initialize the Gemini client.

##### `async extract_knowledge(content: Dict[str, Any]) -> Optional[Dict[str, Any]]`

Extract knowledge from content using Gemini AI.

**Parameters:**
- `content` (Dict): Scraped content

**Returns:**
- `Optional[Dict]`: Extracted knowledge data

##### `async test_connection() -> bool`

Test connection to Gemini API.

##### `async health_check() -> bool`

Check client health status.

### ContentProcessor

Processes and validates content.

```python
from linkedin_scraper.services.content_processor import ContentProcessor

processor = ContentProcessor(config)
processed = await processor.process_content(raw_content)
```

## Storage

### RepositoryManager

Manages knowledge storage and retrieval.

```python
from linkedin_scraper.storage.repository_manager import RepositoryManager

repo = RepositoryManager(config)
await repo.initialize()
await repo.store_knowledge_item(item)
```

#### Methods

##### `async initialize() -> None`

Initialize repository structure.

##### `async store_knowledge_item(item: KnowledgeItem) -> None`

Store knowledge item in repository.

##### `async search_knowledge_items(query: str, category: Optional[str] = None, limit: int = 10) -> List[KnowledgeItem]`

Search knowledge items.

##### `async get_knowledge_by_category(category: str, limit: int = 50) -> List[KnowledgeItem]`

Get items by category.

### CacheManager

Manages content caching.

```python
from linkedin_scraper.storage.cache_manager import CacheManager

cache = CacheManager(config)
await cache.initialize()
cached_item = await cache.get_cached_knowledge(url)
```

#### Methods

##### `async initialize() -> None`

Initialize cache database.

##### `async get_cached_knowledge(url: str) -> Optional[KnowledgeItem]`

Get cached knowledge for URL.

##### `async cache_knowledge_item(item: KnowledgeItem) -> None`

Cache knowledge item.

##### `async health_check() -> bool`

Check cache health.

## Utilities

### PII Detection

```python
from linkedin_scraper.utils.pii_detector import detect_and_sanitize_pii

result = detect_and_sanitize_pii(content, sanitize=True)
clean_content = result["sanitized_text"]
detected_pii = result["detected_pii"]
```

### Error Handling

```python
from linkedin_scraper.utils.error_handler import (
    ErrorHandler, ErrorContext, retry_with_backoff
)

# Create error context
context = ErrorContext(
    component="web_scraper",
    operation="scrape_post",
    url="https://linkedin.com/posts/user/post"
)

# Retry with backoff
result = await retry_with_backoff(
    operation=some_async_function,
    context=context,
    max_retries=3,
    arg1="value1"
)
```

### Metrics Collection

```python
from linkedin_scraper.utils.metrics import MetricsCollector

metrics = MetricsCollector(config)
metrics.record_processing_success(knowledge_item)
metrics.record_processing_error(url, error_message)
```

## Web API Endpoints

### Knowledge Endpoints

#### GET /api/knowledge

List knowledge items with optional filtering.

**Query Parameters:**
- `category` (str): Filter by category
- `limit` (int): Maximum results (default: 50)
- `offset` (int): Pagination offset (default: 0)

**Response:**
```json
{
  "items": [...],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

#### GET /api/knowledge/search

Search knowledge items.

**Query Parameters:**
- `q` (str): Search query (required)
- `category` (str): Filter by category
- `limit` (int): Maximum results (default: 10)

**Response:**
```json
{
  "items": [...],
  "query": "artificial intelligence",
  "total_matches": 25
}
```

#### GET /api/knowledge/{id}

Get specific knowledge item.

**Response:**
```json
{
  "id": "item_id",
  "post_title": "...",
  "key_knowledge_content": "...",
  "topic": "...",
  "category": "...",
  "source_url": "...",
  "course_references": [...],
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Processing Endpoints

#### POST /api/process

Process new LinkedIn URL.

**Request Body:**
```json
{
  "url": "https://linkedin.com/posts/user/post-id",
  "force_refresh": false
}
```

**Response:**
```json
{
  "success": true,
  "item": {...},
  "cached": false,
  "processing_time": 2.5
}
```

#### POST /api/process/batch

Process multiple URLs.

**Request Body:**
```json
{
  "urls": ["url1", "url2", "url3"],
  "max_concurrent": 3
}
```

**Response:**
```json
{
  "success": true,
  "processed": 3,
  "failed": 0,
  "items": [...],
  "processing_time": 8.2
}
```

### System Endpoints

#### GET /api/stats

Get processing statistics.

**Response:**
```json
{
  "total_processed": 1250,
  "successful": 1200,
  "failed": 50,
  "cache_hit_rate": 0.75,
  "avg_processing_time": 2.3,
  "component_health": {
    "cache_manager": true,
    "repository_manager": true,
    "gemini_client": true
  }
}
```

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "components": {
    "database": "healthy",
    "cache": "healthy",
    "ai_service": "healthy"
  }
}
```

## Error Responses

All API endpoints return consistent error responses:

```json
{
  "error": true,
  "message": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "details": {
    "additional": "context"
  }
}
```

### Common Error Codes

- `INVALID_URL`: Invalid LinkedIn URL format
- `PROCESSING_FAILED`: Content processing failed
- `RATE_LIMIT_EXCEEDED`: API rate limit exceeded
- `CONFIGURATION_ERROR`: System configuration issue
- `STORAGE_ERROR`: Database or file system error
- `NETWORK_ERROR`: Network connectivity issue

## Rate Limiting

The API implements rate limiting to protect system resources:

- **Processing endpoints**: 10 requests per minute per IP
- **Search endpoints**: 60 requests per minute per IP
- **Stats endpoints**: 30 requests per minute per IP

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp