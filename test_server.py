#!/usr/bin/env python3
"""
Test server for the LinkedIn Knowledge Management System web interface.
"""

import sys
import uvicorn
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from linkedin_scraper.api.app import create_app
    from linkedin_scraper.utils.config import Config
    
    def main():
        """Run the test server."""
        print("Starting LinkedIn Knowledge Management System test server...")
        
        # Create configuration
        config = Config.from_env()
        
        # Create the FastAPI app
        app = create_app(config)
        
        # Run the server
        print("Server will be available at: http://localhost:8000")
        print("API documentation at: http://localhost:8000/api/docs")
        print("Press Ctrl+C to stop the server")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install fastapi uvicorn jinja2")
    sys.exit(1)
except Exception as e:
    print(f"Error starting server: {e}")
    sys.exit(1)