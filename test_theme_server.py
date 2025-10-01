#!/usr/bin/env python3
"""
Test server to verify theme functionality works correctly.
"""

import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime

def create_test_app():
    """Create a test FastAPI app for theme testing."""
    
    app = FastAPI(
        title="LinkedIn Knowledge AI - Theme Test",
        description="Test server for theme functionality",
        version="1.0.0-test"
    )
    
    # Setup static files
    static_dir = Path("linkedin_scraper/api/static")
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Setup templates
    templates_dir = Path("linkedin_scraper/api/templates")
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # Mock data for testing
    MOCK_DATA = {
        "queue_status": {
            "total_tasks": 15,
            "queued_tasks": 3,
            "completed_tasks": 10,
            "failed_tasks": 2,
            "is_processing": False,
            "status_distribution": {
                "queued": 3,
                "processing": 0,
                "completed": 10,
                "failed": 2
            },
            "stats": {
                "total_tasks": 15,
                "completed_tasks": 10,
                "failed_tasks": 2,
                "retried_tasks": 1,
                "success_rate": 83.3
            }
        },
        "cache_stats": {
            "total_urls_cached": 50,
            "total_knowledge_cached": 42,
            "cache_hit_rate": 87.5,
            "database_size_mb": 15.7
        }
    }
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "queue_status": MOCK_DATA["queue_status"],
            "cache_stats": MOCK_DATA["cache_stats"],
            "title": "Dashboard - Theme Test",
            "datetime": datetime
        })
    
    @app.get("/test", response_class=HTMLResponse)
    async def test_page(request: Request):
        return templates.TemplateResponse("base.html", {
            "request": request,
            "title": "Theme Test Page"
        })
    
    return app

def main():
    """Run the theme test server."""
    print("🎨 Starting LinkedIn Knowledge AI - Theme Test Server")
    print("=" * 60)
    
    # Check if templates exist
    templates_dir = Path("linkedin_scraper/api/templates")
    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        print("Please run from the project root directory.")
        sys.exit(1)
    
    # Create the app
    app = create_test_app()
    
    print("🎯 Test Pages:")
    print("   • Dashboard:     http://localhost:8000/")
    print("   • Base Template: http://localhost:8000/test")
    print()
    print("🎨 Theme Testing:")
    print("   • Click the theme toggle button (moon/sun icon) in the navbar")
    print("   • Verify text contrast in both light and dark modes")
    print("   • Check that all elements are properly visible")
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
        print("\n👋 Theme test server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)