#!/usr/bin/env python3
"""
Simple LinkedIn Knowledge Scraper server that works with demo scraper.
"""

import sys
import asyncio
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import uuid
from contextlib import asynccontextmanager

# Import demo scraper
try:
    from demo_scraper import create_demo_knowledge_item
    DEMO_SCRAPER_AVAILABLE = True
    print("✅ Demo scraper loaded successfully")
except ImportError as e:
    print(f"❌ Demo scraper not available: {e}")
    DEMO_SCRAPER_AVAILABLE = False
    create_demo_knowledge_item = None

# Global state


class AppState:
    def __init__(self):
        self.processing_queue = {}
        self.knowledge_items = []
        self.is_processing = False


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Simple server starting up...")
    if DEMO_SCRAPER_AVAILABLE:
        print("✅ Demo scraper ready for processing")
    else:
        print("⚠️ Demo scraper not available - using basic mock")
    yield
    # Shutdown
    print("👋 Simple server shutting down...")


def create_simple_app():
    """Create a simple FastAPI app with demo scraping."""

    app = FastAPI(
        title="LinkedIn Knowledge AI - Simple Server",
        description="Simple LinkedIn Knowledge Management System with demo scraping",
        version="1.0.0-simple",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan
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

    # Setup templates
    templates_dir = Path("linkedin_scraper/api/templates")
    templates = Jinja2Templates(directory=str(templates_dir))

    def get_queue_data():
        """Get current queue status data."""
        return {
            "total_tasks": len(app_state.processing_queue),
            "queued_tasks": len([t for t in app_state.processing_queue.values() if t["status"] == "queued"]),
            "completed_tasks": len([t for t in app_state.processing_queue.values() if t["status"] == "completed"]),
            "failed_tasks": len([t for t in app_state.processing_queue.values() if t["status"] == "failed"]),
            "is_processing": app_state.is_processing,
            "status_distribution": {
                "queued": len([t for t in app_state.processing_queue.values() if t["status"] == "queued"]),
                "processing": len([t for t in app_state.processing_queue.values() if t["status"] == "processing"]),
                "completed": len([t for t in app_state.processing_queue.values() if t["status"] == "completed"]),
                "failed": len([t for t in app_state.processing_queue.values() if t["status"] == "failed"])
            },
            "stats": {
                "total_tasks": len(app_state.processing_queue),
                "completed_tasks": len([t for t in app_state.processing_queue.values() if t["status"] == "completed"]),
                "failed_tasks": len([t for t in app_state.processing_queue.values() if t["status"] == "failed"]),
                "retried_tasks": 0,
                "success_rate": 85.0 if len(app_state.processing_queue) > 0 else 0
            },
            "tasks": list(app_state.processing_queue.values())
        }

    def get_cache_data():
        """Get cache statistics."""
        return {
            "total_urls_cached": len(app_state.processing_queue),
            "total_knowledge_cached": len(app_state.knowledge_items),
            "cache_hit_rate": 87.5,
            # Rough estimate
            "database_size_mb": len(app_state.knowledge_items) * 0.3
        }

    # Web Routes
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "queue_status": get_queue_data(),
            "cache_stats": get_cache_data(),
            "title": "Dashboard - Simple Server",
            "datetime": datetime
        })

    @app.get("/upload", response_class=HTMLResponse)
    async def upload_page(request: Request):
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "title": "Upload URLs"
        })

    @app.get("/queue", response_class=HTMLResponse)
    async def queue_page(request: Request):
        return templates.TemplateResponse("queue.html", {
            "request": request,
            "queue_status": get_queue_data(),
            "title": "Processing Queue"
        })

    @app.get("/knowledge", response_class=HTMLResponse)
    async def knowledge_page(request: Request):
        return templates.TemplateResponse("knowledge.html", {
            "request": request,
            "recent_items": app_state.knowledge_items,
            "total_items": len(app_state.knowledge_items),
            "title": "Knowledge Repository"
        })

    @app.get("/analytics", response_class=HTMLResponse)
    async def analytics_page(request: Request):
        # Calculate analytics from knowledge items
        categories = {}
        topics = {}
        for item in app_state.knowledge_items:
            cat = item.get("category", "Other")
            topic = item.get("topic", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
            topics[topic] = topics.get(topic, 0) + 1

        analytics = {
            "content_analytics": {
                "category_distribution": categories,
                "top_topics": topics,
                "course_references": {}
            },
            "processing_analytics": {
                "total_processed": len(app_state.processing_queue),
                "success_rate": 85.0,
                "average_processing_time": 2.3,
                "daily_average": 8.5
            }
        }

        return templates.TemplateResponse("analytics.html", {
            "request": request,
            "analytics": analytics,
            "cache_stats": get_cache_data(),
            "title": "Analytics"
        })

    # API Routes
    @app.get("/api/v1/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "LinkedIn Knowledge AI - Simple Server",
            "version": "1.0.0-simple",
            "timestamp": datetime.now().isoformat(),
            "demo_scraper_available": DEMO_SCRAPER_AVAILABLE,
            "total_knowledge_items": len(app_state.knowledge_items),
            "total_tasks": len(app_state.processing_queue)
        }

    @app.post("/api/v1/urls/add")
    async def add_url(request: dict):
        url = request.get("url")
        if not url or "linkedin.com" not in url:
            raise HTTPException(status_code=400, detail="Invalid LinkedIn URL")

        task_id = str(uuid.uuid4())

        # Add to processing queue
        task = {
            "id": task_id,
            "url": url,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "retry_count": 0,
            "error_message": None,
            "result": None,
            "metadata": request.get("metadata", {})
        }

        app_state.processing_queue[task_id] = task

        return {
            "success": True,
            "task_id": task_id,
            "message": "URL added to processing queue"
        }

    @app.post("/api/v1/urls/batch")
    async def add_urls_batch(request: dict):
        urls = request.get("urls", [])
        valid_urls = [url for url in urls if "linkedin.com" in url]
        invalid_urls = [url for url in urls if "linkedin.com" not in url]

        task_ids = []
        for url in valid_urls:
            task_id = str(uuid.uuid4())
            task = {
                "id": task_id,
                "url": url,
                "status": "queued",
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "retry_count": 0,
                "error_message": None,
                "result": None,
                "metadata": request.get("metadata", {})
            }
            app_state.processing_queue[task_id] = task
            task_ids.append(task_id)

        return {
            "success": True,
            "task_ids": task_ids,
            "valid_urls": len(valid_urls),
            "invalid_urls": len(invalid_urls),
            "invalid_url_list": invalid_urls,
            "message": f"Added {len(valid_urls)} URLs to processing queue"
        }

    @app.post("/api/v1/process/start")
    async def start_processing():
        if app_state.is_processing:
            return {"success": False, "message": "Processing already in progress"}

        app_state.is_processing = True

        # Start background processing
        asyncio.create_task(process_queue())

        return {"success": True, "message": "Processing started"}

    @app.post("/api/v1/process/stop")
    async def stop_processing():
        app_state.is_processing = False
        return {"success": True, "message": "Processing stopped"}

    @app.get("/api/v1/queue/status")
    async def get_queue_status():
        return get_queue_data()

    @app.get("/api/v1/knowledge")
    async def get_knowledge_items():
        return {
            "items": app_state.knowledge_items,
            "total": len(app_state.knowledge_items)
        }

    @app.get("/api/v1/analytics/activity")
    async def get_recent_activity():
        # Generate some recent activity based on queue
        activities = []

        # Add recent completed tasks
        completed_tasks = [
            t for t in app_state.processing_queue.values() if t["status"] == "completed"]
        for task in completed_tasks[-5:]:  # Last 5 completed
            activities.append({
                "type": "completed",
                "title": "Task Completed Successfully",
                "description": f"Processed LinkedIn URL: {task['url'][:50]}...",
                "timestamp": task.get("completed_at", datetime.now().isoformat())
            })

        # Add recent knowledge items
        for item in app_state.knowledge_items[-3:]:  # Last 3 items
            activities.append({
                "type": "knowledge",
                "title": "New Knowledge Item Added",
                "description": f"{item['post_title']} - {item['category']}",
                "timestamp": item.get("created_at", datetime.now().isoformat())
            })

        return {"activities": activities}

    async def process_queue():
        """Background task to process queued URLs."""
        print("🔄 Starting background queue processing...")

        while app_state.is_processing:
            # Find queued tasks
            queued_tasks = [
                task for task in app_state.processing_queue.values()
                if task["status"] == "queued"
            ]

            if not queued_tasks:
                await asyncio.sleep(5)  # Wait 5 seconds before checking again
                continue

            # Process first queued task
            task = queued_tasks[0]
            task["status"] = "processing"
            task["started_at"] = datetime.now().isoformat()

            try:
                print(f"🔄 Processing URL: {task['url']}")

                # Use demo scraper if available
                if DEMO_SCRAPER_AVAILABLE and create_demo_knowledge_item:
                    await asyncio.sleep(2)  # Simulate processing time

                    demo_result = create_demo_knowledge_item(task["url"])

                    if demo_result:
                        task["status"] = "completed"
                        task["completed_at"] = datetime.now().isoformat()
                        task["result"] = {
                            "knowledge_item_id": demo_result["id"],
                            "title": demo_result["post_title"],
                            "topic": demo_result["topic"],
                            "category": demo_result["category"],
                            "processing_time": 2.0
                        }

                        # Add to knowledge items
                        app_state.knowledge_items.append(demo_result)

                        print(
                            f"✅ Successfully processed: {demo_result['post_title']}")
                    else:
                        task["status"] = "failed"
                        task["completed_at"] = datetime.now().isoformat()
                        task["error_message"] = "Demo scraper failed to process URL"
                        print(f"❌ Demo scraper failed for: {task['url']}")

                else:
                    # Basic fallback
                    await asyncio.sleep(3)

                    task["status"] = "completed"
                    task["completed_at"] = datetime.now().isoformat()
                    task["result"] = {
                        "knowledge_item_id": str(uuid.uuid4()),
                        "title": "LinkedIn Post Analysis",
                        "topic": "Professional Development",
                        "category": "Business Strategy",
                        "processing_time": 3.0
                    }

                    # Add basic knowledge item
                    app_state.knowledge_items.append({
                        "id": task["result"]["knowledge_item_id"],
                        "post_title": "LinkedIn Post Analysis",
                        "topic": "Professional Development",
                        "category": "Business Strategy",
                        "key_knowledge_content": f"Basic analysis of LinkedIn post from {task['url']}.",
                        "source_url": task["url"],
                        "created_at": datetime.now().isoformat(),
                        "course_references": ["Professional Development", "Business Strategy"]
                    })

                    print(f"✅ Basic processing completed for: {task['url']}")

            except Exception as e:
                # Error occurred
                task["status"] = "failed"
                task["completed_at"] = datetime.now().isoformat()
                task["error_message"] = str(e)
                print(f"❌ Error processing {task['url']}: {e}")

            # Small delay between tasks
            await asyncio.sleep(1)

        print("⏹️ Background processing stopped")

    return app


def main():
    """Run the simple server."""
    print("🚀 Starting LinkedIn Knowledge AI - Simple Server")
    print("=" * 70)

    # Check if templates exist
    templates_dir = Path("linkedin_scraper/api/templates")
    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        print("Please run from the project root directory.")
        sys.exit(1)

    # Create the app
    app = create_simple_app()

    print("📋 Available pages:")
    print("   • Dashboard:    http://localhost:8000/")
    print("   • Upload URLs:  http://localhost:8000/upload")
    print("   • Queue:        http://localhost:8000/queue")
    print("   • Knowledge:    http://localhost:8000/knowledge")
    print("   • Analytics:    http://localhost:8000/analytics")
    print("   • API Docs:     http://localhost:8000/api/docs")
    print("   • API Health:   http://localhost:8000/api/v1/health")
    print()
    print("🔧 Features:")
    print("   • Demo URL processing with smart content generation")
    print("   • Background queue processing")
    print("   • Real-time status updates")
    print("   • Knowledge repository storage")
    print()
    print("🌐 Server starting at: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 70)

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
        print("\n👋 Simple server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
