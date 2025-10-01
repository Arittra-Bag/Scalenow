"""
Main application integration module for the LinkedIn Knowledge Management System.
Wires all components together and provides the main application interface.
"""

import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import signal
import sys

from ..utils.config import Config
from ..utils.privacy_logger import get_privacy_logger, setup_privacy_logging
from ..utils.metrics import initialize_metrics, get_metrics_collector
from ..utils.monitoring import initialize_monitoring, get_health_monitor, get_alert_manager
from ..utils.structured_logging import setup_structured_logging

from ..scrapers.web_scraper import WebScraper
from ..services.content_processor import ContentProcessor
from ..services.content_sanitizer import ContentSanitizer
from ..services.batch_processor import BatchProcessor
from ..services.content_cache_service import ContentCacheService
from ..services.error_handler import ErrorHandler

from ..storage.cache_manager import CacheManager
from ..storage.repository_models import RepositoryManager
from ..storage.excel_generator import ExcelGenerator
from ..storage.word_generator import WordGenerator
from ..storage.file_organizer import FileOrganizer

from ..models.exceptions import ConfigurationError, ProcessingError
from ..models.knowledge_item import KnowledgeItem


class LinkedInKnowledgeManagementSystem:
    """
    Main application class that integrates all components of the LinkedIn KMS.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = None
        self.is_initialized = False
        self.is_running = False
        
        # Core components
        self.web_scraper = None
        self.content_processor = None
        self.content_sanitizer = None
        self.batch_processor = None
        self.cache_service = None
        self.error_handler = None
        
        # Storage components
        self.cache_manager = None
        self.repository_manager = None
        self.excel_generator = None
        self.word_generator = None
        self.file_organizer = None
        
        # Monitoring components
        self.metrics_collector = None
        self.health_monitor = None
        self.alert_manager = None
        
        # Shutdown handling
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    async def initialize(self) -> None:
        """Initialize all application components."""
        if self.is_initialized:
            return
        
        try:
            # 1. Setup logging first
            setup_privacy_logging(self.config)
            setup_structured_logging(self.config)
            self.logger = get_privacy_logger(__name__, self.config)
            
            self.logger.info("Initializing LinkedIn Knowledge Management System")
            
            # 2. Validate configuration
            self.config.validate()
            self.config.create_directories()
            
            # 3. Initialize monitoring and metrics
            self.metrics_collector = initialize_metrics(self.config)
            self.alert_manager, self.health_monitor = initialize_monitoring(
                self.config, self.metrics_collector
            )
            
            # 4. Initialize storage components
            await self._initialize_storage_components()
            
            # 5. Initialize processing components
            await self._initialize_processing_components()
            
            # 6. Initialize web scraping components
            await self._initialize_scraping_components()
            
            # 7. Wire components together
            await self._wire_components()
            
            # 8. Perform health checks
            await self._perform_startup_health_checks()
            
            self.is_initialized = True
            self.logger.info("LinkedIn Knowledge Management System initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}", exc_info=True)
            raise ConfigurationError(f"Application initialization failed: {e}")
    
    async def _initialize_storage_components(self):
        """Initialize storage-related components."""
        self.logger.info("Initializing storage components")
        
        # Cache manager
        self.cache_manager = CacheManager(self.config)
        await self.cache_manager.initialize()
        
        # Repository manager
        self.repository_manager = RepositoryManager(self.config.knowledge_repo_path)
        
        # File organizer
        self.file_organizer = FileOrganizer(self.config)
        
        # Document generators
        self.excel_generator = ExcelGenerator(self.config)
        self.word_generator = WordGenerator(self.config)
        
        self.logger.info("Storage components initialized")
    
    async def _initialize_processing_components(self):
        """Initialize content processing components."""
        self.logger.info("Initializing processing components")
        
        # Error handler
        self.error_handler = ErrorHandler(self.config)
        
        # Content sanitizer
        self.content_sanitizer = ContentSanitizer(self.config)
        
        # Content processor
        self.content_processor = ContentProcessor(self.config)
        
        # Cache service
        self.cache_service = ContentCacheService(self.config)
        
        # Batch processor
        self.batch_processor = BatchProcessor(self.config)
        
        self.logger.info("Processing components initialized")
    
    async def _initialize_scraping_components(self):
        """Initialize web scraping components."""
        self.logger.info("Initializing scraping components")
        
        # Web scraper
        self.web_scraper = WebScraper(self.config)
        await self.web_scraper.initialize()
        
        self.logger.info("Scraping components initialized")
    
    async def _wire_components(self):
        """Wire all components together."""
        self.logger.info("Wiring components together")
        
        # Connect batch processor to content processor
        self.batch_processor.set_content_processor(self.content_processor)
        self.batch_processor.set_cache_service(self.cache_service)
        self.batch_processor.set_error_handler(self.error_handler)
        
        # Connect content processor to sanitizer and storage
        self.content_processor.set_content_sanitizer(self.content_sanitizer)
        self.content_processor.set_repository_manager(self.repository_manager)
        self.content_processor.set_cache_manager(self.cache_manager)
        
        # Connect web scraper to content processor
        self.web_scraper.set_content_processor(self.content_processor)
        
        # Connect cache service to repository
        self.cache_service.set_repository_manager(self.repository_manager)
        
        # Connect error handler to monitoring
        if self.alert_manager:
            self.error_handler.set_alert_manager(self.alert_manager)
        
        self.logger.info("Components wired successfully")
    
    async def _perform_startup_health_checks(self):
        """Perform startup health checks."""
        self.logger.info("Performing startup health checks")
        
        health_issues = []
        
        # Check database connectivity
        try:
            await self.cache_manager.health_check()
        except Exception as e:
            health_issues.append(f"Cache database: {e}")
        
        # Check file system access
        try:
            self.config.create_directories()
        except Exception as e:
            health_issues.append(f"File system: {e}")
        
        # Check AI service connectivity
        try:
            await self.content_processor.health_check()
        except Exception as e:
            health_issues.append(f"AI service: {e}")
        
        # Check web scraper
        try:
            await self.web_scraper.health_check()
        except Exception as e:
            health_issues.append(f"Web scraper: {e}")
        
        if health_issues:
            error_msg = "Startup health checks failed: " + "; ".join(health_issues)
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        self.logger.info("All startup health checks passed")
    
    async def start(self) -> None:
        """Start the application."""
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_running:
            return
        
        self.logger.info("Starting LinkedIn Knowledge Management System")
        
        try:
            # Start background services
            if self.health_monitor:
                self.health_monitor.start_monitoring()
            
            # Start batch processor if configured
            if self.config.enable_auto_backup:
                await self.batch_processor.start_background_processing()
            
            self.is_running = True
            self.logger.info("LinkedIn Knowledge Management System started successfully")
            
            # Log system information
            self._log_system_info()
            
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}", exc_info=True)
            raise ProcessingError(f"Application startup failed: {e}")
    
    async def stop(self) -> None:
        """Stop the application gracefully."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping LinkedIn Knowledge Management System")
        
        try:
            # Stop background services
            if self.health_monitor:
                self.health_monitor.stop_monitoring_thread()
            
            if self.batch_processor:
                await self.batch_processor.stop_background_processing()
            
            # Close connections
            if self.web_scraper:
                await self.web_scraper.cleanup()
            
            if self.cache_manager:
                await self.cache_manager.close()
            
            self.is_running = False
            self.logger.info("LinkedIn Knowledge Management System stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    async def process_url(self, url: str, priority: int = 3) -> Dict[str, Any]:
        """Process a single LinkedIn URL."""
        if not self.is_running:
            raise ProcessingError("Application is not running")
        
        self.logger.info(f"Processing URL: {url}")
        
        try:
            # Add to batch processor
            task_id = self.batch_processor.add_url(url, priority)
            
            if not task_id:
                # URL already processed or in cache
                cached_result = await self.cache_service.get_cached_content(url)
                if cached_result:
                    return {
                        "success": True,
                        "message": "URL already processed (from cache)",
                        "cached": True,
                        "knowledge_item": cached_result
                    }
                else:
                    return {
                        "success": False,
                        "message": "URL already in processing queue",
                        "cached": False
                    }
            
            # Process immediately if not in batch mode
            result = await self.batch_processor.process_single_task(task_id)
            
            return {
                "success": result.get("success", False),
                "message": result.get("message", "Processing completed"),
                "task_id": task_id,
                "knowledge_item": result.get("knowledge_item"),
                "processing_time": result.get("processing_time", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process URL {url}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Processing failed: {str(e)}",
                "error": str(e)
            }
    
    async def process_urls_batch(self, urls: List[str], priority: int = 3) -> Dict[str, Any]:
        """Process multiple LinkedIn URLs."""
        if not self.is_running:
            raise ProcessingError("Application is not running")
        
        self.logger.info(f"Processing batch of {len(urls)} URLs")
        
        try:
            # Add URLs to batch processor
            task_ids = self.batch_processor.add_urls_batch(urls, priority)
            
            # Start batch processing
            results = await self.batch_processor.process_batch(task_ids)
            
            return {
                "success": True,
                "message": f"Batch processing completed for {len(urls)} URLs",
                "task_ids": task_ids,
                "results": results,
                "total_urls": len(urls),
                "successful": len([r for r in results if r.get("success", False)]),
                "failed": len([r for r in results if not r.get("success", False)])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process URL batch: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Batch processing failed: {str(e)}",
                "error": str(e)
            }
    
    async def get_knowledge_repository(self) -> Dict[str, Any]:
        """Get the current knowledge repository."""
        try:
            repository = self.repository_manager.load_repository()
            
            return {
                "success": True,
                "total_items": len(repository.items),
                "items": [item.to_dict() for item in repository.items],
                "categories": repository.get_category_distribution(),
                "topics": repository.get_topic_distribution()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge repository: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to load repository: {str(e)}",
                "error": str(e)
            }
    
    async def export_knowledge(self, format_type: str = "excel") -> Dict[str, Any]:
        """Export knowledge repository to specified format."""
        try:
            repository = self.repository_manager.load_repository()
            
            if format_type.lower() == "excel":
                file_path = await self.excel_generator.generate_excel_file(repository)
            elif format_type.lower() == "word":
                file_path = await self.word_generator.generate_word_document(repository)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            return {
                "success": True,
                "message": f"Knowledge exported to {format_type}",
                "file_path": str(file_path),
                "total_items": len(repository.items)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export knowledge: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Export failed: {str(e)}",
                "error": str(e)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            status = {
                "system": {
                    "initialized": self.is_initialized,
                    "running": self.is_running,
                    "environment": self.config.environment,
                    "version": "1.0.0"
                },
                "components": {
                    "web_scraper": self.web_scraper is not None,
                    "content_processor": self.content_processor is not None,
                    "batch_processor": self.batch_processor is not None,
                    "cache_service": self.cache_service is not None,
                    "repository_manager": self.repository_manager is not None
                },
                "monitoring": {
                    "metrics_enabled": self.metrics_collector is not None,
                    "health_monitoring": self.health_monitor is not None,
                    "alerts_enabled": self.alert_manager is not None
                }
            }
            
            # Add health status if available
            if self.health_monitor:
                health_status = self.health_monitor.get_health_status()
                status["health"] = health_status
            
            # Add metrics if available
            if self.metrics_collector:
                metrics = self.metrics_collector.get_metrics_summary()
                status["metrics"] = metrics
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}", exc_info=True)
            return {
                "system": {
                    "initialized": self.is_initialized,
                    "running": self.is_running,
                    "error": str(e)
                }
            }
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self.stop())
            self._shutdown_event.set()
        
        # Setup signal handlers (Unix only)
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except AttributeError:
            # Windows doesn't have these signals
            pass
    
    def _log_system_info(self):
        """Log system information at startup."""
        env_info = self.config.get_environment_info()
        
        self.logger.info(
            "System started",
            extra_data={
                "environment": env_info["environment"],
                "pii_detection": env_info["pii_detection"],
                "content_sanitization": env_info["content_sanitization"],
                "api_authentication": env_info["api_authentication"],
                "metrics_collection": env_info["metrics_collection"],
                "rate_limits": env_info["rate_limits"]
            }
        )
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()


# Global application instance
_app_instance: Optional[LinkedInKnowledgeManagementSystem] = None


def create_application(config: Config) -> LinkedInKnowledgeManagementSystem:
    """Create the main application instance."""
    global _app_instance
    _app_instance = LinkedInKnowledgeManagementSystem(config)
    return _app_instance


def get_application() -> Optional[LinkedInKnowledgeManagementSystem]:
    """Get the global application instance."""
    return _app_instance


async def run_application(config: Config) -> None:
    """Run the application with proper lifecycle management."""
    app = create_application(config)
    
    try:
        await app.initialize()
        await app.start()
        
        # Keep running until shutdown signal
        await app.wait_for_shutdown()
        
    except KeyboardInterrupt:
        print("\nReceived interrupt signal")
    except Exception as e:
        print(f"Application error: {e}")
        raise
    finally:
        await app.stop()


if __name__ == "__main__":
    # Allow running the application directly
    import asyncio
    from ..utils.config import Config
    
    config = Config.from_env()
    asyncio.run(run_application(config))