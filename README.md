# LinkedIn Knowledge Scraper

A comprehensive system for extracting, processing, and managing knowledge from LinkedIn posts using AI-powered content analysis.

## Overview

The LinkedIn Knowledge Scraper is designed to help professionals and organizations systematically capture and organize valuable insights from LinkedIn content. It uses advanced AI processing to extract key knowledge, categorize content, and build a searchable repository of business intelligence.

## Features

- **Intelligent Content Extraction**: Uses Google's Gemini AI to extract meaningful knowledge from LinkedIn posts
- **Automated Categorization**: Classifies content into business-relevant categories (AI/ML, SaaS, Marketing, etc.)
- **PII Protection**: Automatically detects and sanitizes personally identifiable information
- **Caching System**: Efficient caching to avoid reprocessing the same content
- **Repository Management**: Organized storage with Git-based version control
- **Web Interface**: User-friendly interface for browsing and searching knowledge
- **Rate Limiting**: Respects API limits and implements intelligent backoff strategies
- **Comprehensive Monitoring**: Built-in metrics, alerts, and error handling

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Google Gemini API key
- Git (for repository management)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd linkedin-knowledge-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the system:
```bash
python -m linkedin_scraper.main --help
```

### Basic Usage

#### Process a single LinkedIn URL:
```bash
python -m linkedin_scraper.main --url "https://linkedin.com/posts/user/post-id"
```

#### Process multiple URLs from a file:
```bash
python -m linkedin_scraper.main --urls-file urls.txt --max-concurrent 3
```

#### Search existing knowledge:
```bash
python -m linkedin_scraper.main --search "artificial intelligence" --category "AI & Machine Learning"
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional - Paths
KNOWLEDGE_REPO_PATH=./knowledge_repository
CACHE_DB_PATH=./cache/knowledge_cache.db
LOG_FILE_PATH=./logs/scraper.log

# Optional - Behavior
ENVIRONMENT=development
ENABLE_PII_DETECTION=true
SANITIZE_CONTENT=true
LOG_LEVEL=INFO

# Optional - Rate Limiting
GEMINI_RATE_LIMIT_RPM=60
GEMINI_RATE_LIMIT_RPD=1000

# Optional - Web Interface
WEB_SERVER_HOST=localhost
WEB_SERVER_PORT=8000
WEB_SERVER_DEBUG=false

# Optional - Monitoring
ENABLE_METRICS=true
METRICS_EXPORT_INTERVAL=300
ALERT_WEBHOOK_URL=https://hooks.slack.com/your/webhook/url
```

### Configuration File

Alternatively, you can use a configuration file:

```python
from linkedin_scraper.utils.config import Config

config = Config(
    gemini_api_key="your_api_key",
    knowledge_repo_path="./knowledge",
    enable_pii_detection=True,
    sanitize_content=True
)
```

## Architecture

### Core Components

1. **Web Scraper** (`linkedin_scraper.services.web_scraper`)
   - Extracts content from LinkedIn posts
   - Handles rate limiting and retries
   - Supports multiple content formats

2. **Content Processor** (`linkedin_scraper.services.content_processor`)
   - Processes scraped content
   - Integrates with AI services
   - Handles content validation

3. **Gemini Client** (`linkedin_scraper.services.gemini_client`)
   - Interfaces with Google's Gemini AI
   - Extracts structured knowledge from content
   - Manages API rate limits

4. **Repository Manager** (`linkedin_scraper.storage.repository_manager`)
   - Manages knowledge storage
   - Provides search and retrieval
   - Handles Git-based versioning

5. **Cache Manager** (`linkedin_scraper.storage.cache_manager`)
   - Caches processed content
   - Prevents duplicate processing
   - Manages cache lifecycle

### Data Flow

```
LinkedIn URL → Web Scraper → PII Detection → Gemini AI → Knowledge Item → Repository + Cache
```

## API Reference

### Main Application Class

```python
from linkedin_scraper.main import LinkedInKnowledgeScraper

# Initialize
scraper = LinkedInKnowledgeScraper(config)
await scraper.initialize()

# Process content
knowledge_item = await scraper.process_linkedin_url(url)

# Search knowledge
results = await scraper.search_knowledge("AI trends")

# Cleanup
await scraper.cleanup()
```

### Knowledge Item Model

```python
from linkedin_scraper.models.knowledge_item import KnowledgeItem, Category

item = KnowledgeItem(
    post_title="AI in Business Operations",
    key_knowledge_content="AI transforms business through automation...",
    topic="Artificial Intelligence",
    category=Category.AI_MACHINE_LEARNING,
    source_url="https://linkedin.com/posts/...",
    course_references=["AI for Business", "ML Fundamentals"]
)
```

## Web Interface

The system includes a web interface for browsing and managing knowledge:

### Starting the Web Server

```bash
python -m linkedin_scraper.web.app
```

### Features

- **Browse Knowledge**: View all stored knowledge items
- **Search**: Full-text search across all content
- **Filter**: Filter by category, date, or topic
- **Export**: Export knowledge in various formats
- **Analytics**: View processing statistics and trends

### API Endpoints

- `GET /api/knowledge` - List knowledge items
- `GET /api/knowledge/search?q=query` - Search knowledge
- `POST /api/process` - Process new LinkedIn URL
- `GET /api/stats` - Get processing statistics

## Deployment

### Local Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Start development server
python -m linkedin_scraper.web.app --debug
```

### Production Deployment

#### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "linkedin_scraper.web.app"]
```

#### Using Render

1. Connect your GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy as a Web Service

#### Using Google Cloud Platform

```bash
# Deploy to Cloud Run
gcloud run deploy linkedin-scraper \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## Monitoring and Maintenance

### Health Checks

The system provides health check endpoints:

```bash
curl http://localhost:8000/health
```

### Metrics

Built-in metrics tracking:
- Processing success/failure rates
- API response times
- Cache hit rates
- Error frequencies

### Alerts

Configure alerts for:
- High error rates
- API quota exhaustion
- Storage issues
- Performance degradation

### Logs

Structured logging with configurable levels:
- DEBUG: Detailed processing information
- INFO: General operational messages
- WARNING: Non-critical issues
- ERROR: Processing failures
- CRITICAL: System-level problems

## Troubleshooting

### Common Issues

#### "Invalid API Key" Error
- Verify your Gemini API key is correct
- Check API key permissions and quotas
- Ensure the key is properly set in environment variables

#### "Rate Limit Exceeded"
- The system automatically handles rate limits
- Consider reducing concurrent processing
- Check your API quota limits

#### "PII Detection Errors"
- Ensure PII detection is properly configured
- Check content for unusual formatting
- Review sanitization settings

#### "Storage Issues"
- Verify write permissions for repository path
- Check available disk space
- Ensure Git is properly configured

### Debug Mode

Enable debug mode for detailed logging:

```bash
export LOG_LEVEL=DEBUG
python -m linkedin_scraper.main --url "your-url"
```

### Performance Optimization

- Adjust `max_concurrent` based on your system capabilities
- Use caching effectively to avoid reprocessing
- Monitor memory usage with large datasets
- Consider database indexing for large repositories

## Contributing

### Development Setup

1. Fork the repository
2. Create a virtual environment
3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Run tests:
   ```bash
   pytest tests/
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write comprehensive docstrings
- Add tests for new features

### Submitting Changes

1. Create a feature branch
2. Make your changes
3. Add tests
4. Update documentation
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting guide
- Review the API documentation

## Changelog

### Version 1.0.0
- Initial release
- Core scraping and processing functionality
- Web interface
- Comprehensive error handling
- PII detection and sanitization
- Caching system
- Repository management