"""
Main application entry point for LinkedIn Knowledge Scraper.
Wires together all components and provides the primary interface.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from linkedin_scraper.utils.config import Config, ConfigurationError
from linkedin_scraper.utils.logger import setup_logging
from linkedin_scraper.services.web_scraper import WebScraper
from linkedin_scraper.services.content_processor import ContentProcessor
from linkedin_scraper.services.gemini_client import GeminiClient
from linkedin_scraper.storage.repository_manager import RepositoryManager
from linkedin_scraper.storage.cache_manager import CacheManager
from linkedin_scraper.models.knowledge_item import KnowledgeItem
from linkedin_scraper.utils.metrics import MetricsCollector
from linkedin_scraper.utils.monitoring import AlertManager
from linkedin_scraper.utils.pii_detector import detect_and_sanitize_pii
from linkedin_scraper.utils.error_handler import (
    ErrorHandler, ErrorContext, ErrorSeverity, 
    NetworkError, APIError, DataProcessingError, StorageError,
    retry_with_backoff
)


class LinkedInKnowledgeScraper:
    """Main application class that orchestrates all components."""
    
    def __init__(self, config: Config):
        """Initialize the scraper with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.web_scraper: Optional[WebScraper] = None
        self.content_processor: Optional[ContentProcessor] = None
        self.gemini_client: Optional[GeminiClient] = None
        self.repository_manager: Optional[RepositoryManager] = None
        self.cache_manager: Optional[CacheManager] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.alert_manager: Optional[AlertManager] = None
        self.error_handler: Optional[ErrorHandler] = None
        
        # Application state
        self.is_initialized = False
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None
        }
    
    async def initialize(self) -> None:
        """Initialize all components and dependencies."""
        try:
            self.logger.info("Initializing LinkedIn Knowledge Scraper...")
            
            # Validate configuration
            self.config.validate()
            
            # Create necessary directories
            self.config.create_directories()
            
            # Initialize components in dependency order
            self.cache_manager = CacheManager(self.config)
            await self.cache_manager.initialize()
            
            self.repository_manager = RepositoryManager(self.config)
            await self.repository_manager.initialize()
            
            self.gemini_client = GeminiClient(self.config)
            await self.gemini_client.initialize()
            
            self.content_processor = ContentProcessor(self.config)
            self.web_scraper = WebScraper(self.config)
            
            self.metrics_collector = MetricsCollector(self.config)
            self.alert_manager = AlertManager(self.config)
            self.error_handler = ErrorHandler(self.config)
            
            # Test connections
            await self._test_connections()
            
            self.is_initialized = True
            self.processing_stats["start_time"] = datetime.now()
            
            self.logger.info("LinkedIn Knowledge Scraper initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {e}")
            await self.cleanup()
            raise
    
    async def _test_connections(self) -> None:
        """Test all external connections and dependencies."""
        self.logger.info("Testing component connections...")
        
        # Test Gemini API connection
        if self.gemini_client:
            await self.gemini_client.test_connection()
        
        # Test cache database
        if self.cache_manager:
            await self.cache_manager.health_check()
        
        # Test repository access
        if self.repository_manager:
            self.repository_manager.validate_repository_structure()
        
        self.logger.info("All component connections tested successfully")
    
    async def process_linkedin_url(self, url: str) -> Optional[KnowledgeItem]:
        """
        Process a single LinkedIn URL through the complete pipeline.
        
        Args:
            url: LinkedIn post URL to process
            
        Returns:
            KnowledgeItem if successful, None if failed
        """
        if not self.is_initialized:
            raise RuntimeError("Scraper not initialized. Call initialize() first.")   
     
        try:
            self.logger.info(f"Processing LinkedIn URL: {url}")
            
            # Check cache first
            cached_item = await self.cache_manager.get_cached_knowledge(url)
            if cached_item:
                self.logger.info(f"Found cached knowledge for URL: {url}")
                self.processing_stats["skipped"] += 1
                return cached_item
            
            # Step 1: Scrape content from LinkedIn
            self.logger.debug("Scraping LinkedIn content...")
            scraped_content = await self.web_scraper.scrape_linkedin_post(url)
            
            if not scraped_content:
                self.logger.warning(f"Failed to scrape content from URL: {url}")
                self.processing_stats["failed"] += 1
                return None
            
            # Step 2: Sanitize content for PII
            if self.config.enable_pii_detection:
                self.logger.debug("Sanitizing content for PII...")
                sanitized_content = detect_and_sanitize_pii(
                    scraped_content.get("content", ""),
                    sanitize=self.config.sanitize_content
                )
                scraped_content["content"] = sanitized_content["sanitized_text"]
            
            # Step 3: Process content with Gemini AI
            self.logger.debug("Processing content with Gemini AI...")
            knowledge_data = await self.gemini_client.extract_knowledge(scraped_content)
            
            if not knowledge_data:
                self.logger.warning(f"Failed to extract knowledge from URL: {url}")
                self.processing_stats["failed"] += 1
                return None
            
            # Step 4: Create knowledge item
            knowledge_item = KnowledgeItem.from_scraped_data(
                scraped_content=scraped_content,
                knowledge_data=knowledge_data,
                source_url=url
            )
            
            # Step 5: Store in repository
            self.logger.debug("Storing knowledge item...")
            await self.repository_manager.store_knowledge_item(knowledge_item)
            
            # Step 6: Cache the result
            await self.cache_manager.cache_knowledge_item(knowledge_item)
            
            # Update metrics
            self.metrics_collector.record_processing_success(knowledge_item)
            self.processing_stats["successful"] += 1
            self.processing_stats["total_processed"] += 1
            
            self.logger.info(f"Successfully processed URL: {url}")
            return knowledge_item
            
        except Exception as e:
            self.logger.error(f"Error processing URL {url}: {e}")
            self.metrics_collector.record_processing_error(url, str(e))
            self.processing_stats["failed"] += 1
            self.processing_stats["total_processed"] += 1
            
            # Send alert for critical errors
            if self.alert_manager:
                await self.alert_manager.send_error_alert(
                    f"Failed to process LinkedIn URL: {url}",
                    str(e)
                )
            
            return None
    
    async def process_multiple_urls(self, urls: List[str], max_concurrent: int = 3) -> List[KnowledgeItem]:
        """
        Process multiple LinkedIn URLs concurrently.
        
        Args:
            urls: List of LinkedIn URLs to process
            max_concurrent: Maximum number of concurrent processing tasks
            
        Returns:
            List of successfully processed KnowledgeItems
        """
        if not self.is_initialized:
            raise RuntimeError("Scraper not initialized. Call initialize() first.")
        
        self.logger.info(f"Processing {len(urls)} URLs with max concurrency: {max_concurrent}")
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(url: str) -> Optional[KnowledgeItem]:
            async with semaphore:
                return await self.process_linkedin_url(url)
        
        # Process all URLs concurrently
        tasks = [process_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        knowledge_items = []
        for result in results:
            if isinstance(result, KnowledgeItem):
                knowledge_items.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Task failed with exception: {result}")
        
        self.logger.info(f"Completed processing. Success: {len(knowledge_items)}/{len(urls)}")
        return knowledge_items
    
    async def search_knowledge(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[KnowledgeItem]:
        """
        Search stored knowledge items.
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List of matching KnowledgeItems
        """
        if not self.is_initialized:
            raise RuntimeError("Scraper not initialized. Call initialize() first.")
        
        return await self.repository_manager.search_knowledge_items(
            query=query,
            category=category,
            limit=limit
        )
    
    async def get_knowledge_by_category(self, category: str, limit: int = 50) -> List[KnowledgeItem]:
        """
        Get knowledge items by category.
        
        Args:
            category: Category to filter by
            limit: Maximum number of results
            
        Returns:
            List of KnowledgeItems in the category
        """
        if not self.is_initialized:
            raise RuntimeError("Scraper not initialized. Call initialize() first.")
        
        return await self.repository_manager.get_knowledge_by_category(category, limit)
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        stats = self.processing_stats.copy()
        
        if stats["start_time"]:
            stats["runtime_seconds"] = (datetime.now() - stats["start_time"]).total_seconds()
        
        # Add component health status
        stats["component_health"] = {
            "cache_manager": await self.cache_manager.health_check() if self.cache_manager else False,
            "repository_manager": self.repository_manager.is_healthy() if self.repository_manager else False,
            "gemini_client": await self.gemini_client.health_check() if self.gemini_client else False
        }
        
        return stats
    
    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        self.logger.info("Cleaning up LinkedIn Knowledge Scraper...")
        
        try:
            if self.cache_manager:
                await self.cache_manager.close()
            
            if self.gemini_client:
                await self.gemini_client.close()
            
            if self.repository_manager:
                await self.repository_manager.close()
            
            if self.metrics_collector:
                await self.metrics_collector.flush_metrics()
            
            self.is_initialized = False
            self.logger.info("Cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


async def create_scraper_from_config(config_path: Optional[str] = None) -> LinkedInKnowledgeScraper:
    """
    Create and initialize a scraper instance from configuration.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Initialized LinkedInKnowledgeScraper instance
    """
    try:
        # Load configuration
        if config_path:
            config = Config.from_env(config_path)
        else:
            config = Config.from_environment()
        
        # Set up logging
        setup_logging(config)
        
        # Create and initialize scraper
        scraper = LinkedInKnowledgeScraper(config)
        await scraper.initialize()
        
        return scraper
        
    except Exception as e:
        logging.error(f"Failed to create scraper: {e}")
        raise


async def main():
    """Main entry point for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LinkedIn Knowledge Scraper")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--url", help="Single LinkedIn URL to process")
    parser.add_argument("--urls-file", help="File containing LinkedIn URLs (one per line)")
    parser.add_argument("--search", help="Search existing knowledge")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--max-concurrent", type=int, default=3, help="Max concurrent processing")
    
    args = parser.parse_args()
    
    try:
        # Create scraper
        scraper = await create_scraper_from_config(args.config)
        
        try:
            if args.url:
                # Process single URL
                result = await scraper.process_linkedin_url(args.url)
                if result:
                    print(f"Successfully processed: {result.post_title}")
                    print(f"Category: {result.category.value}")
                    print(f"Topic: {result.topic}")
                else:
                    print("Failed to process URL")
                    sys.exit(1)
            
            elif args.urls_file:
                # Process multiple URLs from file
                with open(args.urls_file, 'r') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                results = await scraper.process_multiple_urls(urls, args.max_concurrent)
                print(f"Processed {len(results)}/{len(urls)} URLs successfully")
                
                for item in results:
                    print(f"- {item.post_title} ({item.category.value})")
            
            elif args.search:
                # Search existing knowledge
                results = await scraper.search_knowledge(args.search, args.category)
                print(f"Found {len(results)} matching items:")
                
                for item in results:
                    print(f"- {item.post_title}")
                    print(f"  Category: {item.category.value}")
                    print(f"  Topic: {item.topic}")
                    print()
            
            else:
                # Show stats
                stats = await scraper.get_processing_stats()
                print("LinkedIn Knowledge Scraper Status:")
                print(f"- Total processed: {stats['total_processed']}")
                print(f"- Successful: {stats['successful']}")
                print(f"- Failed: {stats['failed']}")
                print(f"- Skipped (cached): {stats['skipped']}")
                
                if stats.get('runtime_seconds'):
                    print(f"- Runtime: {stats['runtime_seconds']:.1f} seconds")
        
        finally:
            await scraper.cleanup()
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())