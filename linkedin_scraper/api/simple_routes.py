"""Simplified API routes for testing the web UI."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta
import random

# Create routers
api_router = APIRouter()
web_router = APIRouter()

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Mock data for testing
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
    }
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
    },
    {
        "id": "knowledge-3",
        "post_title": "Modern Sales Techniques for B2B Success",
        "topic": "Sales Strategy",
        "category": "Marketing & Sales",
        "key_knowledge_content": "Modern B2B sales success relies on consultative selling, social selling through LinkedIn, and value-based conversations. Top performers spend 60% of their time researching prospects and only 40% on actual selling activities.",
        "source_url": "https://linkedin.com/posts/example-3",
        "created_at": (datetime.now() - timedelta(hours=8)).isoformat(),
        "course_references": ["Consultative Selling Mastery"],
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
            "Consultative Selling Mastery": 3,
            "Growth Hacking for SaaS": 2,
            "Machine Learning Fundamentals": 2
        }
    },
    "processing_analytics": {
        "total_processed": 50,
        "success_rate": 84.0,
        "average_processing_time": 2.3,
        "daily_average": 8.5,
        "daily_stats": {
            "2024-01-01": {"processed": 10, "knowledge_extracted": 8},
            "2024-01-02": {"processed": 12, "knowledge_extracted": 10},
            "2024-01-03": {"processed": 8, "knowledge_extracted": 7}
        }
    }
}

MOCK_TASKS = [
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
    },
    {
        "id": "task-3",
        "url": "https://linkedin.com/posts/example-3",
        "priority": 3,
        "status": "failed",
        "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "started_at": (datetime.now() - timedelta(minutes=58)).isoformat(),
        "completed_at": (datetime.now() - timedelta(minutes=55)).isoformat(),
        "retry_count": 2,
        "error_message": "Failed to extract content: Rate limit exceeded",
        "result": None,
        "metadata": {"source": "web_interface"}
    }
]

MOCK_ACTIVITIES = [
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
    },
    {
        "type": "error",
        "title": "Processing Error",
        "description": "Rate limit exceeded for LinkedIn API",
        "timestamp": (datetime.now() - timedelta(hours=1)).isoformat()
    },
    {
        "type": "started",
        "title": "Batch Processing Started",
        "description": "Processing 5 URLs from batch upload",
        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat()
    }
]

# ============================================================================
# API Routes
# ============================================================================

@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "LinkedIn Knowledge Management System",
        "version": "1.0.0-test",
        "timestamp": datetime.now().isoformat()
    }

@api_router.post("/urls/add")
async def add_url(request: dict):
    """Add a single URL to the processing queue."""
    url = request.get("url")
    priority = request.get("priority", 3)
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    if "linkedin.com" not in url:
        raise HTTPException(status_code=400, detail="Invalid LinkedIn URL")
    
    # Generate mock task ID
    task_id = f"task-{random.randint(1000, 9999)}"
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "URL added to processing queue"
    }

@api_router.post("/urls/batch")
async def add_urls_batch(request: dict):
    """Add multiple URLs to the processing queue."""
    urls = request.get("urls", [])
    priority = request.get("priority", 3)
    
    if not urls:
        raise HTTPException(status_code=400, detail="URLs are required")
    
    # Validate URLs
    valid_urls = [url for url in urls if "linkedin.com" in url]
    invalid_urls = [url for url in urls if "linkedin.com" not in url]
    
    # Generate mock task IDs
    task_ids = [f"task-{random.randint(1000, 9999)}" for _ in valid_urls]
    
    return {
        "success": True,
        "task_ids": task_ids,
        "valid_urls": len(valid_urls),
        "invalid_urls": len(invalid_urls),
        "invalid_url_list": invalid_urls,
        "message": f"Added {len(valid_urls)} URLs to processing queue"
    }

@api_router.post("/process/start")
async def start_processing(request: dict = None):
    """Start processing the queue."""
    max_concurrent = request.get("max_concurrent", 3) if request else 3
    
    # Update mock status
    MOCK_QUEUE_STATUS["is_processing"] = True
    
    return {
        "success": True,
        "message": "Processing started",
        "max_concurrent": max_concurrent
    }

@api_router.post("/process/stop")
async def stop_processing():
    """Stop the current processing."""
    MOCK_QUEUE_STATUS["is_processing"] = False
    
    return {
        "success": True,
        "message": "Processing stopped"
    }

@api_router.get("/process/status")
async def get_processing_status():
    """Get current processing status."""
    return {
        "is_processing": MOCK_QUEUE_STATUS["is_processing"],
        "queued_tasks": MOCK_QUEUE_STATUS["queued_tasks"],
        "total_tasks": MOCK_QUEUE_STATUS["total_tasks"]
    }

@api_router.get("/queue/status")
async def get_queue_status():
    """Get current queue status."""
    return MOCK_QUEUE_STATUS

@api_router.get("/tasks/{task_id}")
async def get_task_details(task_id: str):
    """Get details for a specific task."""
    # Find task in mock data
    task = next((t for t in MOCK_TASKS if t["id"] == task_id), None)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

@api_router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a specific task."""
    # Find task in mock data
    task = next((t for t in MOCK_TASKS if t["id"] == task_id), None)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] not in ["queued", "retrying"]:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    
    task["status"] = "cancelled"
    
    return {"success": True, "message": "Task cancelled"}

@api_router.get("/knowledge")
async def get_knowledge_items(
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None
):
    """Get knowledge items with pagination."""
    items = MOCK_KNOWLEDGE_ITEMS.copy()
    
    # Filter by category if provided
    if category:
        items = [item for item in items if item["category"] == category]
    
    # Apply pagination
    total_items = len(items)
    paginated_items = items[offset:offset + limit]
    
    return {
        "items": paginated_items,
        "total": total_items,
        "limit": limit,
        "offset": offset
    }

@api_router.get("/knowledge/{knowledge_id}")
async def get_knowledge_item(knowledge_id: str):
    """Get a specific knowledge item."""
    item = next((item for item in MOCK_KNOWLEDGE_ITEMS if item["id"] == knowledge_id), None)
    
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    
    return item

@api_router.get("/knowledge/search")
async def search_knowledge(
    q: str,
    category: Optional[str] = None,
    limit: int = 20
):
    """Search knowledge items."""
    items = MOCK_KNOWLEDGE_ITEMS.copy()
    
    # Simple search implementation
    query_lower = q.lower()
    filtered_items = []
    
    for item in items:
        if (query_lower in item["post_title"].lower() or 
            query_lower in item["topic"].lower() or 
            query_lower in item["key_knowledge_content"].lower()):
            
            if not category or item["category"] == category:
                filtered_items.append(item)
    
    # Apply limit
    results = filtered_items[:limit]
    
    return {
        "items": results,
        "total_results": len(results),
        "query": q,
        "category": category
    }

@api_router.get("/knowledge/{knowledge_id}/related")
async def get_related_knowledge(knowledge_id: str, limit: int = 10):
    """Get related knowledge items."""
    # Find the source item
    source_item = next((item for item in MOCK_KNOWLEDGE_ITEMS if item["id"] == knowledge_id), None)
    
    if not source_item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    
    # Simple related logic - same category
    related_items = [
        item for item in MOCK_KNOWLEDGE_ITEMS 
        if item["id"] != knowledge_id and item["category"] == source_item["category"]
    ][:limit]
    
    return {
        "knowledge_id": knowledge_id,
        "items": related_items,
        "total_related": len(related_items)
    }

@api_router.get("/analytics/content")
async def get_content_analytics():
    """Get content analytics."""
    return {
        "content_analytics": MOCK_ANALYTICS["content_analytics"],
        "processing_analytics": MOCK_ANALYTICS["processing_analytics"],
        "cache_statistics": MOCK_CACHE_STATS
    }

@api_router.get("/analytics/activity")
async def get_recent_activity(limit: int = 50):
    """Get recent activity log."""
    return {"activities": MOCK_ACTIVITIES[:limit]}

@api_router.get("/export/excel")
async def export_excel():
    """Export knowledge repository to Excel."""
    # For testing, return a simple response
    return JSONResponse(
        content={"message": "Excel export would be generated here"},
        headers={"Content-Type": "application/json"}
    )

@api_router.get("/export/word")
async def export_word():
    """Export knowledge repository to Word."""
    # For testing, return a simple response
    return JSONResponse(
        content={"message": "Word export would be generated here"},
        headers={"Content-Type": "application/json"}
    )

# ============================================================================
# Web Routes (HTML Interface)
# ============================================================================

@web_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "queue_status": MOCK_QUEUE_STATUS,
        "cache_stats": MOCK_CACHE_STATS,
        "title": "Dashboard",
        "datetime": datetime
    })

@web_router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """URL upload page."""
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "title": "Upload URLs"
    })

@web_router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    """Queue management page."""
    # Add tasks to queue status for the template
    queue_status_with_tasks = MOCK_QUEUE_STATUS.copy()
    queue_status_with_tasks["tasks"] = MOCK_TASKS
    
    return templates.TemplateResponse("queue.html", {
        "request": request,
        "queue_status": queue_status_with_tasks,
        "title": "Processing Queue"
    })

@web_router.get("/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request):
    """Knowledge repository page."""
    return templates.TemplateResponse("knowledge.html", {
        "request": request,
        "recent_items": MOCK_KNOWLEDGE_ITEMS,
        "total_items": len(MOCK_KNOWLEDGE_ITEMS),
        "title": "Knowledge Repository"
    })

@web_router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics page."""
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "analytics": MOCK_ANALYTICS,
        "cache_stats": MOCK_CACHE_STATS,
        "title": "Analytics"
    })