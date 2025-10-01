"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

from ..services.batch_processor import TaskPriority, TaskStatus


# ============================================================================
# Enums
# ============================================================================

class TaskPriorityEnum(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskStatusEnum(str, Enum):
    """Task status values."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# ============================================================================
# Request Models
# ============================================================================

class AddUrlRequest(BaseModel):
    """Request model for adding a single URL."""
    url: str = Field(..., description="LinkedIn URL to process")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Processing priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.linkedin.com/posts/user_topic_activity-123456",
                "priority": "normal",
                "metadata": {"source": "manual_input", "category": "research"}
            }
        }


class BatchUrlRequest(BaseModel):
    """Request model for adding multiple URLs."""
    urls: List[str] = Field(..., description="List of LinkedIn URLs to process")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Processing priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "urls": [
                    "https://www.linkedin.com/posts/user1_topic1_activity-123456",
                    "https://www.linkedin.com/posts/user2_topic2_activity-789012"
                ],
                "priority": "high",
                "metadata": {"batch_id": "batch_001", "source": "csv_import"}
            }
        }


class ProcessRequest(BaseModel):
    """Request model for starting processing."""
    max_concurrent: int = Field(5, ge=1, le=20, description="Maximum concurrent workers")
    progress_callback_url: Optional[str] = Field(None, description="URL for progress callbacks")
    
    class Config:
        schema_extra = {
            "example": {
                "max_concurrent": 3,
                "progress_callback_url": "https://example.com/webhook/progress"
            }
        }


class SearchRequest(BaseModel):
    """Request model for searching knowledge."""
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Category filter")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "AI machine learning",
                "category": "AI & Machine Learning",
                "limit": 10
            }
        }


# ============================================================================
# Response Models
# ============================================================================

class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class AddUrlResponse(BaseResponse):
    """Response for adding a single URL."""
    task_id: str = Field(..., description="Generated task ID")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "URL added to processing queue",
                "task_id": "task_1234567890_1",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class BatchUrlResponse(BaseResponse):
    """Response for adding multiple URLs."""
    task_ids: List[str] = Field(..., description="Generated task IDs")
    valid_urls: int = Field(..., description="Number of valid URLs")
    invalid_urls: int = Field(..., description="Number of invalid URLs")
    invalid_url_list: List[str] = Field(default_factory=list, description="List of invalid URLs")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Added 2 URLs to processing queue",
                "task_ids": ["task_1234567890_1", "task_1234567890_2"],
                "valid_urls": 2,
                "invalid_urls": 0,
                "invalid_url_list": [],
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class ProcessResponse(BaseResponse):
    """Response for processing operations."""
    max_concurrent: Optional[int] = Field(None, description="Maximum concurrent workers")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Processing started",
                "max_concurrent": 5,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class QueueStatusResponse(BaseModel):
    """Queue status response."""
    total_tasks: int = Field(..., description="Total number of tasks")
    queued_tasks: int = Field(..., description="Number of queued tasks")
    is_processing: bool = Field(..., description="Whether processing is active")
    status_distribution: Dict[str, int] = Field(..., description="Task status distribution")
    stats: Dict[str, Any] = Field(..., description="Processing statistics")
    
    class Config:
        schema_extra = {
            "example": {
                "total_tasks": 10,
                "queued_tasks": 3,
                "is_processing": True,
                "status_distribution": {
                    "queued": 3,
                    "processing": 2,
                    "completed": 4,
                    "failed": 1
                },
                "stats": {
                    "total_tasks": 10,
                    "completed_tasks": 4,
                    "failed_tasks": 1,
                    "success_rate": 80.0
                }
            }
        }


class TaskDetailsResponse(BaseModel):
    """Task details response."""
    id: str = Field(..., description="Task ID")
    url: str = Field(..., description="LinkedIn URL")
    priority: int = Field(..., description="Task priority")
    status: str = Field(..., description="Task status")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    retry_count: int = Field(..., description="Number of retries")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Task metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "task_1234567890_1",
                "url": "https://www.linkedin.com/posts/user_topic_activity-123456",
                "priority": 3,
                "status": "completed",
                "created_at": "2024-01-01T12:00:00Z",
                "started_at": "2024-01-01T12:01:00Z",
                "completed_at": "2024-01-01T12:02:30Z",
                "retry_count": 0,
                "error_message": None,
                "result": {"knowledge_item_id": "abc123", "processing_time": 1.5},
                "metadata": {"source": "manual_input"}
            }
        }


class SearchResponse(BaseModel):
    """Search results response."""
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Category filter")
    
    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "knowledge_id": "abc123",
                        "topic": "AI in Business",
                        "category": "AI & Machine Learning",
                        "key_knowledge_content": "AI can improve business efficiency...",
                        "extraction_date": "2024-01-01T12:00:00Z"
                    }
                ],
                "total_results": 1,
                "query": "AI business",
                "category": "AI & Machine Learning"
            }
        }


class AnalyticsResponse(BaseModel):
    """Analytics response."""
    content_analytics: Dict[str, Any] = Field(..., description="Content analytics data")
    cache_statistics: Dict[str, Any] = Field(..., description="Cache statistics")
    
    class Config:
        schema_extra = {
            "example": {
                "content_analytics": {
                    "category_distribution": {
                        "AI & Machine Learning": 15,
                        "SaaS & Business": 10,
                        "Marketing & Sales": 8
                    },
                    "top_topics": {
                        "AI in Business": 5,
                        "SaaS Growth": 3,
                        "Email Marketing": 2
                    }
                },
                "cache_statistics": {
                    "total_urls_cached": 50,
                    "total_knowledge_cached": 45,
                    "cache_hit_rate": 85.5,
                    "database_size_mb": 2.3
                }
            }
        }


# ============================================================================
# File Upload Models
# ============================================================================

class FileUploadResponse(BaseResponse):
    """File upload response."""
    filename: str = Field(..., description="Uploaded filename")
    file_size: int = Field(..., description="File size in bytes")
    urls_extracted: int = Field(..., description="Number of URLs extracted")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "File uploaded and processed",
                "filename": "linkedin_urls.csv",
                "file_size": 1024,
                "urls_extracted": 25,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response model."""
    error: bool = Field(True, description="Indicates an error occurred")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    path: str = Field(..., description="Request path")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "error": True,
                "message": "Invalid LinkedIn URL",
                "status_code": 400,
                "path": "/api/v1/urls/add",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }