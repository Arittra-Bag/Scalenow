"""
Main entry point for the LinkedIn Knowledge Management System.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from linkedin_scraper.utils.config import Config
from linkedin_scraper.utils.logger import setup_logger
from linkedin_scraper.models.exceptions import ConfigurationError


def main():
    """Main application entry point."""
    try:
        # Load configuration
        config = Config.from_env()
        config.validate()
        config.create_directories()
        
        # Set up logging
        logger = setup_logger(config=config)
        logger.info("LinkedIn Knowledge Management System starting...")
        logger.info(f"Knowledge repository: {config.knowledge_repo_path}")
        logger.info(f"Cache database: {config.cache_db_path}")
        
        # TODO: Initialize and start the application
        logger.info("Application initialized successfully")
        
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file and ensure all required settings are provided.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()