#!/usr/bin/env python3
"""
Simple test server for the LinkedIn Knowledge Management System web interface.
"""

import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_simple_app():
    """Create a simple FastAPI app for testing templates."""
    
    app = FastAPI(
        title="LinkedIn Knowledge Management System - Test",
        description="Test server for web interface",
        version="1.0.0-test",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup static files
    static_dir = Path("linkedin_scraper/api/static")
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Import and include the simplified routes
    try:
        from linkedin_scraper.api.simple_routes import api_router, web_router
        app.include_router(api_router, prefix="/api/v1", tags=["API"])
        app.include_router(web_router, tags=["Web"])
        print("✅ Routes loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load routes: {e}")
        return None
    

    
    return app

def main():
    """Run the simple test server."""
    print("🚀 Starting LinkedIn Knowledge Management System - Test Server")
    print("=" * 60)
    
    # Check if templates exist
    templates_dir = Path("linkedin_scraper/api/templates")
    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        print("Please run from the project root directory.")
        sys.exit(1)
    
    # Create the app
    app = create_simple_app()
    
    if app is None:
        print("❌ Failed to create app")
        sys.exit(1)
    
    print("📋 Available pages:")
    print("   • Dashboard:    http://localhost:8000/")
    print("   • Upload URLs:  http://localhost:8000/upload")
    print("   • Queue:        http://localhost:8000/queue")
    print("   • Knowledge:    http://localhost:8000/knowledge")
    print("   • Analytics:    http://localhost:8000/analytics")
    print("   • API Docs:     http://localhost:8000/api/docs")
    print("   • API Health:   http://localhost:8000/api/v1/health")
    print()
    print("🌐 Server starting at: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)