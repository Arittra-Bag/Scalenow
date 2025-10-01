#!/usr/bin/env python3
"""
Working test server for the LinkedIn Knowledge Management System web interface.
"""

import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import random

def create_working_app():
    """Create a working FastAPI app for testing templates."""
    
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
    
    # Setup templates
    templates_dir = Path("linkedin_scraper/api/templates")
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # Mock data
    MOCK_QUEUE_STATUS = {
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
        },
        "tasks": [
            {
                "id": "task-1",
                "url": "https://linkedin.com/posts/example-1",
                "priority": 3,
                "status": "completed",
                "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "started_at": (datetime.now() - timedelta(hours=1, minutes=58)).isoformat(),
                "completed_at": (datetime.now() - timedelta(hours=1, minutes=56)).isoformat(),
                "retry_count": 0,
                "error_message": None,
                "result": {"knowledge_item_id": "knowledge-1", "processing_time": 2.1},
                "metadata": {"source": "web_interface"}
            },
            {
                "id": "task-2",
                "url": "https://linkedin.com/posts/example-2",
                "priority": 5,
                "status": "queued",
                "created_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "started_at": None,
                "completed_at": None,
                "retry_count": 0,
                "error_message": None,
                "result": None,
                "metadata": {"source": "batch_upload"}
            }
        ]
    }
    
    MOCK_CACHE_STATS = {
        "total_urls_cached": 50,
        "total_knowledge_cached": 42,
        "cache_hit_rate": 87.5,
        "database_size_mb": 15.7
    }
    
    MOCK_KNOWLEDGE_ITEMS = [
        {
            "id": "knowledge-1",
            "post_title": "The Future of AI in Business Operations",
            "topic": "Artificial Intelligence",
            "category": "AI & Machine Learning",
            "key_knowledge_content": "AI is revolutionizing business operations by automating repetitive tasks, improving decision-making through data analysis, and enabling predictive analytics. Companies implementing AI see 20-30% efficiency gains in operational processes.",
            "source_url": "https://linkedin.com/posts/example-1",
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "course_references": ["AI for Business Leaders", "Machine Learning Fundamentals"],
            "images": []
        },
        {
            "id": "knowledge-2",
            "post_title": "SaaS Growth Strategies That Actually Work",
            "topic": "Business Growth",
            "category": "SaaS & Business",
            "key_knowledge_content": "Successful SaaS companies focus on three key areas: customer acquisition cost (CAC) optimization, lifetime value (LTV) maximization, and product-market fit refinement. The best performing SaaS companies maintain a LTV:CAC ratio of 3:1 or higher.",
            "source_url": "https://linkedin.com/posts/example-2",
            "created_at": (datetime.now() - timedelta(hours=5)).isoformat(),
            "course_references": ["SaaS Metrics That Matter", "Growth Hacking for SaaS"],
            "images": []
        }
    ]
    
    MOCK_ANALYTICS = {
        "content_analytics": {
            "category_distribution": {
                "AI & Machine Learning": 15,
                "SaaS & Business": 12,
                "Marketing & Sales": 8,
                "Leadership & Management": 5,
                "Technology Trends": 2
            },
            "top_topics": {
                "Artificial Intelligence": 8,
                "Business Growth": 6,
                "Sales Strategy": 4,
                "Leadership": 3,
                "Product Management": 2
            },
            "course_references": {
                "AI for Business Leaders": 5,
                "SaaS Metrics That Matter": 4,
                "Consultative Selling Mastery": 3
            }
        },
        "processing_analytics": {
            "total_processed": 50,
            "success_rate": 84.0,
            "average_processing_time": 2.3,
            "daily_average": 8.5
        }
    }
    
    # Web Routes
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "queue_status": MOCK_QUEUE_STATUS,
            "cache_stats": MOCK_CACHE_STATS,
            "title": "Dashboard",
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
            "queue_status": MOCK_QUEUE_STATUS,
            "title": "Processing Queue"
        })
    
    @app.get("/knowledge", response_class=HTMLResponse)
    async def knowledge_page(request: Request):
        return templates.TemplateResponse("knowledge.html", {
            "request": request,
            "recent_items": MOCK_KNOWLEDGE_ITEMS,
            "total_items": len(MOCK_KNOWLEDGE_ITEMS),
            "title": "Knowledge Repository"
        })
    
    @app.get("/analytics", response_class=HTMLResponse)
    async def analytics_page(request: Request):
        return templates.TemplateResponse("analytics.html", {
            "request": request,
            "analytics": MOCK_ANALYTICS,
            "cache_stats": MOCK_CACHE_STATS,
            "title": "Analytics"
        })
    
    # API Routes
    @app.get("/api/v1/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "LinkedIn Knowledge Management System",
            "version": "1.0.0-test",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.post("/api/v1/urls/add")
    async def add_url(request: dict):
        url = request.get("url")
        if not url or "linkedin.com" not in url:
            raise HTTPException(status_code=400, detail="Invalid LinkedIn URL")
        
        task_id = f"task-{random.randint(1000, 9999)}"
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
        
        task_ids = [f"task-{random.randint(1000, 9999)}" for _ in valid_urls]
        
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
        MOCK_QUEUE_STATUS["is_processing"] = True
        return {"success": True, "message": "Processing started"}
    
    @app.post("/api/v1/process/stop")
    async def stop_processing():
        MOCK_QUEUE_STATUS["is_processing"] = False
        return {"success": True, "message": "Processing stopped"}
    
    @app.get("/api/v1/process/status")
    async def get_processing_status():
        return {
            "is_processing": MOCK_QUEUE_STATUS["is_processing"],
            "queued_tasks": MOCK_QUEUE_STATUS["queued_tasks"],
            "total_tasks": MOCK_QUEUE_STATUS["total_tasks"]
        }
    
    @app.get("/api/v1/queue/status")
    async def get_queue_status():
        return MOCK_QUEUE_STATUS
    
    @app.get("/api/v1/tasks/{task_id}")
    async def get_task_details(task_id: str):
        task = next((t for t in MOCK_QUEUE_STATUS["tasks"] if t["id"] == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    
    @app.delete("/api/v1/tasks/{task_id}")
    async def cancel_task(task_id: str):
        return {"success": True, "message": "Task cancelled"}
    
    @app.get("/api/v1/knowledge")
    async def get_knowledge_items():
        return {
            "items": MOCK_KNOWLEDGE_ITEMS,
            "total": len(MOCK_KNOWLEDGE_ITEMS)
        }
    
    @app.get("/api/v1/knowledge/{knowledge_id}")
    async def get_knowledge_item(knowledge_id: str):
        item = next((item for item in MOCK_KNOWLEDGE_ITEMS if item["id"] == knowledge_id), None)
        if not item:
            raise HTTPException(status_code=404, detail="Knowledge item not found")
        return item
    
    @app.get("/api/v1/knowledge/search")
    async def search_knowledge(
        q: str = None, 
        category: str = None, 
        topic: str = None,
        course: str = None,
        date_range: str = None,
        content_length: str = None,
        limit: int = 20
    ):
        items = MOCK_KNOWLEDGE_ITEMS.copy()
        
        # Text search
        if q:
            query_lower = q.lower()
            items = [
                item for item in items
                if (query_lower in item["post_title"].lower() or 
                    query_lower in item["topic"].lower() or 
                    query_lower in item["key_knowledge_content"].lower() or
                    any(query_lower in course.lower() for course in item.get("course_references", [])))
            ]
        
        # Category filter
        if category:
            items = [item for item in items if item["category"] == category]
        
        # Topic filter
        if topic:
            items = [item for item in items if item["topic"] == topic]
        
        # Course filter
        if course:
            items = [item for item in items if course in item.get("course_references", [])]
        
        # Content length filter
        if content_length:
            items = [item for item in items if filter_by_content_length(item, content_length)]
        
        # Date range filter (simplified for demo)
        if date_range:
            # In a real implementation, this would filter by actual dates
            pass
        
        return {
            "items": items[:limit],
            "total_results": len(items),
            "query": q,
            "filters": {
                "category": category,
                "topic": topic,
                "course": course,
                "date_range": date_range,
                "content_length": content_length
            }
        }
    
    def filter_by_content_length(item, length_filter):
        content_length = len(item.get("key_knowledge_content", ""))
        if length_filter == "short":
            return content_length < 200
        elif length_filter == "medium":
            return 200 <= content_length <= 500
        elif length_filter == "long":
            return content_length > 500
        return True
    
    @app.get("/api/v1/knowledge/{knowledge_id}/related")
    async def get_related_knowledge(knowledge_id: str):
        source_item = next((item for item in MOCK_KNOWLEDGE_ITEMS if item["id"] == knowledge_id), None)
        if not source_item:
            raise HTTPException(status_code=404, detail="Knowledge item not found")
        
        related_items = [
            item for item in MOCK_KNOWLEDGE_ITEMS 
            if item["id"] != knowledge_id and item["category"] == source_item["category"]
        ]
        
        return {"items": related_items}
    
    @app.get("/api/v1/analytics/content")
    async def get_content_analytics():
        return {
            "content_analytics": MOCK_ANALYTICS["content_analytics"],
            "processing_analytics": MOCK_ANALYTICS["processing_analytics"],
            "cache_statistics": MOCK_CACHE_STATS
        }
    
    @app.get("/api/v1/analytics/activity")
    async def get_recent_activity():
        activities = [
            {
                "type": "completed",
                "title": "Task Completed Successfully",
                "description": "Extracted knowledge from AI business post",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat()
            },
            {
                "type": "knowledge",
                "title": "New Knowledge Item Added",
                "description": "SaaS Growth Strategies - Business Growth category",
                "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat()
            }
        ]
        return {"activities": activities}
    
    @app.get("/api/v1/export/excel")
    async def export_excel_enhanced(
        scope: str = "all",
        format: str = "excel",
        export_type: str = "standard",
        topics: str = None,
        categories: str = None,
        query: str = None,
        category: str = None,
        topic: str = None,
        course: str = None
    ):
        """Enhanced Excel export with filtering options."""
        
        # Determine which items to export
        items_to_export = MOCK_KNOWLEDGE_ITEMS.copy()
        
        if export_type == "by_topic" and topics:
            topic_list = topics.split(',')
            items_to_export = [item for item in items_to_export if item["topic"] in topic_list]
            export_filename = f"knowledge-by-topics-{'-'.join(topic_list[:2])}"
            
        elif export_type == "by_category" and categories:
            category_list = categories.split(',')
            items_to_export = [item for item in items_to_export if item["category"] in category_list]
            export_filename = f"knowledge-by-categories-{len(category_list)}-selected"
            
        elif scope == "filtered":
            # Apply filters similar to search
            if query:
                query_lower = query.lower()
                items_to_export = [
                    item for item in items_to_export
                    if (query_lower in item["post_title"].lower() or 
                        query_lower in item["topic"].lower() or 
                        query_lower in item["key_knowledge_content"].lower())
                ]
            
            if category:
                items_to_export = [item for item in items_to_export if item["category"] == category]
            
            if topic:
                items_to_export = [item for item in items_to_export if item["topic"] == topic]
                
            if course:
                items_to_export = [item for item in items_to_export if course in item.get("course_references", [])]
            
            export_filename = f"knowledge-filtered-{len(items_to_export)}-items"
        else:
            export_filename = f"knowledge-all-{len(items_to_export)}-items"
        
        # Create export response
        export_data = {
            "export_type": export_type,
            "scope": scope,
            "total_items": len(items_to_export),
            "export_timestamp": datetime.now().isoformat(),
            "filename": f"{export_filename}-{datetime.now().strftime('%Y%m%d')}.xlsx",
            "items": items_to_export,
            "filters_applied": {
                "query": query,
                "category": category,
                "topic": topic,
                "course": course,
                "topics": topics,
                "categories": categories
            }
        }
        
        return JSONResponse(
            content={
                "message": f"Excel export prepared for {len(items_to_export)} items",
                "export_data": export_data
            },
            headers={"Content-Type": "application/json"}
        )
    
    @app.get("/api/v1/export/word")
    async def export_word_enhanced(
        scope: str = "all",
        format: str = "word",
        export_type: str = "standard",
        topics: str = None,
        categories: str = None,
        query: str = None,
        category: str = None,
        topic: str = None,
        course: str = None
    ):
        """Enhanced Word export with filtering options."""
        
        # Similar logic to Excel export
        items_to_export = MOCK_KNOWLEDGE_ITEMS.copy()
        
        if export_type == "by_topic" and topics:
            topic_list = topics.split(',')
            items_to_export = [item for item in items_to_export if item["topic"] in topic_list]
            export_filename = f"knowledge-by-topics-{'-'.join(topic_list[:2])}"
            
        elif export_type == "by_category" and categories:
            category_list = categories.split(',')
            items_to_export = [item for item in items_to_export if item["category"] in category_list]
            export_filename = f"knowledge-by-categories-{len(category_list)}-selected"
            
        elif scope == "filtered":
            # Apply same filtering logic as Excel
            if query:
                query_lower = query.lower()
                items_to_export = [
                    item for item in items_to_export
                    if (query_lower in item["post_title"].lower() or 
                        query_lower in item["topic"].lower() or 
                        query_lower in item["key_knowledge_content"].lower())
                ]
            
            if category:
                items_to_export = [item for item in items_to_export if item["category"] == category]
            
            export_filename = f"knowledge-filtered-{len(items_to_export)}-items"
        else:
            export_filename = f"knowledge-all-{len(items_to_export)}-items"
        
        return JSONResponse(
            content={
                "message": f"Word export prepared for {len(items_to_export)} items",
                "filename": f"{export_filename}-{datetime.now().strftime('%Y%m%d')}.docx",
                "total_items": len(items_to_export)
            },
            headers={"Content-Type": "application/json"}
        )
    
    return app

def main():
    """Run the working test server."""
    print("🚀 Starting LinkedIn Knowledge Management System - Working Test Server")
    print("=" * 70)
    
    # Check if templates exist
    templates_dir = Path("linkedin_scraper/api/templates")
    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        print("Please run from the project root directory.")
        sys.exit(1)
    
    # Create the app
    app = create_working_app()
    
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
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)