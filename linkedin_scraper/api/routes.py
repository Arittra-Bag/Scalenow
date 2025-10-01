"""API and web routes for the LinkedIn Knowledge Management System."""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio
import json
from datetime import datetime

from ..services.batch_processor import BatchProcessor, TaskPriority, TaskStatus
from ..services.content_processor import ContentProcessor
from ..services.content_cache_service import ContentCacheService
from ..services.error_handler import ErrorHandler
from ..storage.cache_manager import CacheManager
from ..storage.repository_models import KnowledgeRepository, RepositoryManager
from ..storage.excel_generator import ExcelGenerator
from ..storage.word_generator import WordGenerator
from ..storage.file_organizer import FileOrganizer
from ..scrapers.url_parser import LinkedInURLParser
from ..utils.config import Config
from ..utils.logger import get_logger
from .models import *

logger = get_logger(__name__)

# Create routers
api_router = APIRouter()
web_router = APIRouter()

# Global instances (will be initialized properly in production)
config = Config.from_env()
batch_processor = BatchProcessor(config)
content_processor = ContentProcessor(config)
cache_service = ContentCacheService(config)
cache_manager = CacheManager(config)
error_handler = ErrorHandler(config)
repo_manager = RepositoryManager(config.knowledge_repo_path)
excel_generator = ExcelGenerator(config)
word_generator = WordGenerator(config)
file_organizer = FileOrganizer(config)

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# ============================================================================
# API Routes
# ============================================================================

@api_router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="LinkedIn Knowledge Management System",
        version="1.0.0",
        timestamp=datetime.now()
    )


@api_router.post("/urls/add", response_model=AddUrlResponse)
async def add_url(request: AddUrlRequest):
    """Add a single URL to the processing queue."""
    try:
        # Validate URL
        if not LinkedInURLParser.is_valid_linkedin_url(request.url):
            raise HTTPException(status_code=400, detail="Invalid LinkedIn URL")
        
        # Add to batch processor
        task_id = batch_processor.add_url(
            url=request.url,
            priority=request.priority,
            metadata=request.metadata or {}
        )
        
        if not task_id:
            raise HTTPException(status_code=409, detail="URL already cached or in queue")
        
        return AddUrlResponse(
            success=True,
            task_id=task_id,
            message="URL added to processing queue"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/urls/batch", response_model=BatchUrlResponse)
async def add_urls_batch(request: BatchUrlRequest):
    """Add multiple URLs to the processing queue."""
    try:
        # Validate URLs
        invalid_urls = []
        valid_urls = []
        
        for url in request.urls:
            if LinkedInURLParser.is_valid_linkedin_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)
        
        if not valid_urls:
            raise HTTPException(status_code=400, detail="No valid LinkedIn URLs provided")
        
        # Add to batch processor
        task_ids = batch_processor.add_urls_batch(
            urls=valid_urls,
            priority=request.priority,
            metadata=request.metadata or {}
        )
        
        return BatchUrlResponse(
            success=True,
            task_ids=task_ids,
            valid_urls=len(valid_urls),
            invalid_urls=len(invalid_urls),
            invalid_url_list=invalid_urls,
            message=f"Added {len(task_ids)} URLs to processing queue"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add URLs batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/process/start", response_model=ProcessResponse)
async def start_processing(
    background_tasks: BackgroundTasks,
    request: ProcessRequest = ProcessRequest()
):
    """Start processing the queue."""
    try:
        if batch_processor.is_processing:
            raise HTTPException(status_code=409, detail="Processing already in progress")
        
        # Start processing in background
        background_tasks.add_task(
            process_queue_background,
            request.max_concurrent,
            request.progress_callback_url
        )
        
        return ProcessResponse(
            success=True,
            message="Processing started",
            max_concurrent=request.max_concurrent
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/process/stop", response_model=ProcessResponse)
async def stop_processing():
    """Stop the current processing."""
    try:
        batch_processor.stop_processing_queue()
        
        return ProcessResponse(
            success=True,
            message="Processing stop requested"
        )
        
    except Exception as e:
        logger.error(f"Failed to stop processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status():
    """Get current queue status."""
    try:
        status = batch_processor.get_queue_status()
        
        return QueueStatusResponse(
            total_tasks=status['total_tasks'],
            queued_tasks=status['queued_tasks'],
            is_processing=status['is_processing'],
            status_distribution=status['status_distribution'],
            stats=status['stats']
        )
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/tasks/{task_id}", response_model=TaskDetailsResponse)
async def get_task_details(task_id: str):
    """Get details for a specific task."""
    try:
        task_details = batch_processor.get_task_details(task_id)
        
        if not task_details:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskDetailsResponse(**task_details)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a specific task."""
    try:
        success = batch_processor.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
        
        return {"success": True, "message": "Task cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/knowledge/search", response_model=SearchResponse)
async def search_knowledge(
    query: str,
    category: Optional[str] = None,
    limit: int = 20
):
    """Search knowledge items."""
    try:
        from ..models.knowledge_item import Category
        
        # Convert category string to enum if provided
        category_enum = None
        if category:
            try:
                category_enum = Category.from_string(category)
            except:
                raise HTTPException(status_code=400, detail="Invalid category")
        
        # Search cached content
        results = cache_service.search_cached_content(
            query=query,
            category=category_enum,
            limit=limit
        )
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            query=query,
            category=category
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/knowledge/{knowledge_id}/related")
async def get_related_knowledge(knowledge_id: str, limit: int = 10):
    """Get related knowledge items."""
    try:
        related_items = cache_service.get_related_content(knowledge_id, limit=limit)
        
        return {
            "knowledge_id": knowledge_id,
            "related_items": related_items,
            "total_related": len(related_items)
        }
        
    except Exception as e:
        logger.error(f"Failed to get related knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/analytics/content", response_model=AnalyticsResponse)
async def get_content_analytics():
    """Get content analytics."""
    try:
        analytics = cache_service.get_content_analytics()
        cache_stats = cache_manager.get_cache_statistics()
        
        return AnalyticsResponse(
            content_analytics=analytics,
            cache_statistics=cache_stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/analytics/activity")
async def get_recent_activity(limit: int = 50):
    """Get recent activity log."""
    try:
        # This would typically come from a logging/activity service
        # For now, return mock data based on cache and queue status
        activities = []
        
        # Get recent tasks
        queue_status = batch_processor.get_queue_status()
        
        # Add some mock activities based on current state
        if queue_status.get('is_processing'):
            activities.append({
                "type": "started",
                "title": "Processing Started",
                "description": f"Queue processing started with {queue_status.get('queued_tasks', 0)} tasks",
                "timestamp": datetime.now().isoformat()
            })
        
        # Add completed tasks as activities
        completed_count = queue_status.get('status_distribution', {}).get('completed', 0)
        if completed_count > 0:
            activities.append({
                "type": "completed",
                "title": f"{completed_count} Tasks Completed",
                "description": "Successfully processed LinkedIn posts",
                "timestamp": datetime.now().isoformat()
            })
        
        return {"activities": activities}
        
    except Exception as e:
        logger.error(f"Failed to get activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/knowledge")
async def get_knowledge_items(
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None
):
    """Get knowledge items with pagination."""
    try:
        repository = repo_manager.load_repository()
        
        # Filter by category if provided
        items = repository.items
        if category:
            from ..models.knowledge_item import Category
            try:
                category_enum = Category.from_string(category)
                items = [item for item in items if item.category == category_enum]
            except:
                pass  # Invalid category, return all items
        
        # Apply pagination
        total_items = len(items)
        paginated_items = items[offset:offset + limit]
        
        # Convert to dict format for JSON response
        items_data = []
        for item in paginated_items:
            items_data.append({
                "id": item.id,
                "post_title": item.post_title,
                "topic": item.topic,
                "category": item.category.value,
                "key_knowledge_content": item.key_knowledge_content,
                "source_url": item.source_url,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "course_references": item.course_references,
                "images": [{"url": img.url, "local_path": img.local_path} for img in item.images] if item.images else []
            })
        
        return {
            "items": items_data,
            "total": total_items,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get knowledge items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/knowledge/{knowledge_id}")
async def get_knowledge_item(knowledge_id: str):
    """Get a specific knowledge item."""
    try:
        repository = repo_manager.load_repository()
        
        # Find the item
        item = None
        for repo_item in repository.items:
            if repo_item.id == knowledge_id:
                item = repo_item
                break
        
        if not item:
            raise HTTPException(status_code=404, detail="Knowledge item not found")
        
        # Convert to dict format
        return {
            "id": item.id,
            "post_title": item.post_title,
            "topic": item.topic,
            "category": item.category.value,
            "key_knowledge_content": item.key_knowledge_content,
            "source_url": item.source_url,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "course_references": item.course_references,
            "images": [{"url": img.url, "local_path": img.local_path} for img in item.images] if item.images else []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/process/status")
async def get_processing_status():
    """Get current processing status."""
    try:
        queue_status = batch_processor.get_queue_status()
        
        return {
            "is_processing": queue_status.get('is_processing', False),
            "queued_tasks": queue_status.get('queued_tasks', 0),
            "total_tasks": queue_status.get('total_tasks', 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to get processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/export/excel")
async def export_excel(background_tasks: BackgroundTasks):
    """Export knowledge repository to Excel."""
    try:
        # Load repository
        repository = repo_manager.load_repository()
        
        # Generate Excel file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"knowledge_export_{timestamp}.xlsx"
        file_path = file_organizer.excels_path / filename
        
        excel_generator.generate_excel_file(repository, str(file_path))
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        logger.error(f"Failed to export Excel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/export/word")
async def export_word(background_tasks: BackgroundTasks):
    """Export knowledge repository to Word."""
    try:
        # Load repository
        repository = repo_manager.load_repository()
        
        # Generate Word file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"knowledge_export_{timestamp}.docx"
        file_path = file_organizer.docs_path / filename
        
        word_generator.generate_word_document(repository, str(file_path))
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except Exception as e:
        logger.error(f"Failed to export Word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Web Routes (HTML Interface)
# ============================================================================

@web_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    try:
        # Get current statistics
        queue_status = batch_processor.get_queue_status()
        cache_stats = cache_manager.get_cache_statistics()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "queue_status": queue_status,
            "cache_stats": cache_stats,
            "title": "LinkedIn Knowledge Management System"
        })
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Dashboard unavailable")


@web_router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    """Queue management page."""
    try:
        queue_status = batch_processor.get_queue_status()
        
        return templates.TemplateResponse("queue.html", {
            "request": request,
            "queue_status": queue_status,
            "title": "Processing Queue"
        })
        
    except Exception as e:
        logger.error(f"Queue page error: {e}")
        raise HTTPException(status_code=500, detail="Queue page unavailable")


@web_router.get("/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request):
    """Knowledge repository page."""
    try:
        # Get recent knowledge items
        repository = repo_manager.load_repository()
        recent_items = repository.get_recent_items(limit=20)
        
        return templates.TemplateResponse("knowledge.html", {
            "request": request,
            "recent_items": recent_items,
            "total_items": len(repository.items),
            "title": "Knowledge Repository"
        })
        
    except Exception as e:
        logger.error(f"Knowledge page error: {e}")
        raise HTTPException(status_code=500, detail="Knowledge page unavailable")


@web_router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics page."""
    try:
        analytics = cache_service.get_content_analytics()
        cache_stats = cache_manager.get_cache_statistics()
        
        return templates.TemplateResponse("analytics.html", {
            "request": request,
            "analytics": analytics,
            "cache_stats": cache_stats,
            "title": "Analytics & Statistics"
        })
        
    except Exception as e:
        logger.error(f"Analytics page error: {e}")
        raise HTTPException(status_code=500, detail="Analytics page unavailable")


@web_router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """URL upload page."""
    try:
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "title": "Upload URLs"
        })
        
    except Exception as e:
        logger.error(f"Upload page error: {e}")
        raise HTTPException(status_code=500, detail="Upload page unavailable")


# ============================================================================
# Background Tasks
# ============================================================================

async def process_queue_background(
    max_concurrent: int = 5,
    progress_callback_url: Optional[str] = None
):
    """Background task for processing the queue."""
    try:
        logger.info(f"Starting background processing with {max_concurrent} workers")
        
        # Define progress callback
        def progress_callback(progress_info):
            logger.info(f"Processing progress: {progress_info}")
            # Here you could send progress to a webhook URL if provided
        
        # Process the queue
        stats = await batch_processor.process_queue(
            max_concurrent=max_concurrent,
            progress_callback=progress_callback if not progress_callback_url else None
        )
        
        logger.info(f"Background processing completed: {stats.success_rate:.1f}% success rate")
        
    except Exception as e:
        logger.error(f"Background processing failed: {e}")
        # Handle error appropriately