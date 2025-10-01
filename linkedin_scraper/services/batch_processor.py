"""Batch processing service for handling multiple LinkedIn posts efficiently."""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

from ..models.knowledge_item import KnowledgeItem
from ..models.post_content import PostContent
from ..models.exceptions import ProcessingError, StorageError
from ..utils.config import Config
from ..utils.logger import get_logger
from ..storage.cache_manager import CacheManager
from ..services.content_cache_service import ContentCacheService
from ..scrapers.url_parser import LinkedInURLParser

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Status of processing tasks."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Priority levels for processing tasks."""
    LOW = 1
    NORMAL = 3
    HIGH = 5
    URGENT = 8
    CRITICAL = 10


@dataclass
class ProcessingTask:
    """Represents a single processing task."""
    id: str
    url: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if isinstance(self.priority, int):
            self.priority = TaskPriority(self.priority)
        if isinstance(self.status, str):
            self.status = TaskStatus(self.status)
    
    @property
    def processing_time(self) -> Optional[float]:
        """Get processing time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries and self.status == TaskStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingTask':
        """Create task from dictionary."""
        data = data.copy()
        data['priority'] = TaskPriority(data['priority'])
        data['status'] = TaskStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['started_at'] = datetime.fromisoformat(data['started_at']) if data['started_at'] else None
        data['completed_at'] = datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None
        return cls(**data)


@dataclass
class BatchProcessingStats:
    """Statistics for batch processing operations."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    retried_tasks: int = 0
    duplicates_skipped: int = 0
    average_processing_time: float = 0.0
    total_processing_time: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    @property
    def total_duration(self) -> Optional[float]:
        """Get total batch duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class BatchProcessor:
    """Batch processor for handling multiple LinkedIn posts with queue management."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the batch processor."""
        self.config = config or Config.from_env()
        
        # Initialize components
        self.cache_manager = CacheManager(config)
        self.cache_service = ContentCacheService(config)
        
        # Task management
        self.tasks: Dict[str, ProcessingTask] = {}
        self.task_queue: List[str] = []  # Task IDs in processing order
        self.processing_lock = threading.Lock()
        self.is_processing = False
        self.stop_processing = False
        
        # Statistics
        self.stats = BatchProcessingStats()
        
        # File-based persistence
        self.queue_file = Path(self.config.knowledge_repo_path) / "processing_queue.json"
        self.stats_file = Path(self.config.knowledge_repo_path) / "batch_stats.json"
        
        # Load existing queue
        self._load_queue_from_file()
        
        logger.info("Batch processor initialized")
    
    def add_url(
        self,
        url: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a URL to the processing queue."""
        try:
            # Validate URL
            if not LinkedInURLParser.is_valid_linkedin_url(url):
                raise ProcessingError(f"Invalid LinkedIn URL: {url}")
            
            # Check if already cached
            if self.cache_manager.is_url_cached(url):
                logger.info(f"URL already cached, skipping: {url}")
                self.stats.duplicates_skipped += 1
                return ""
            
            # Generate task ID
            task_id = f"task_{int(time.time() * 1000)}_{len(self.tasks)}"
            
            # Create task
            task = ProcessingTask(
                id=task_id,
                url=url,
                priority=priority,
                status=TaskStatus.QUEUED,
                created_at=datetime.now(),
                metadata=metadata or {}
            )
            
            with self.processing_lock:
                self.tasks[task_id] = task
                self._insert_task_by_priority(task_id)
                self.stats.total_tasks += 1
            
            # Save queue to file
            self._save_queue_to_file()
            
            logger.info(f"Task added to queue: {task_id} (priority: {priority.name})")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to add URL to queue: {e}")
            raise ProcessingError(f"Failed to add URL to queue: {e}")
    
    def add_urls_batch(
        self,
        urls: List[str],
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Add multiple URLs to the processing queue."""
        task_ids = []
        
        for url in urls:
            try:
                task_id = self.add_url(url, priority, metadata)
                if task_id:  # Only add non-empty task IDs
                    task_ids.append(task_id)
            except Exception as e:
                logger.error(f"Failed to add URL {url}: {e}")
                continue
        
        logger.info(f"Added {len(task_ids)} tasks to queue from {len(urls)} URLs")
        return task_ids
    
    def _insert_task_by_priority(self, task_id: str):
        """Insert task into queue based on priority."""
        task = self.tasks[task_id]
        
        # Find insertion point based on priority
        insertion_index = 0
        for i, existing_task_id in enumerate(self.task_queue):
            existing_task = self.tasks[existing_task_id]
            if task.priority.value > existing_task.priority.value:
                insertion_index = i
                break
            insertion_index = i + 1
        
        self.task_queue.insert(insertion_index, task_id)
    
    def get_next_task(self) -> Optional[ProcessingTask]:
        """Get the next task from the queue."""
        with self.processing_lock:
            while self.task_queue:
                task_id = self.task_queue[0]
                task = self.tasks.get(task_id)
                
                if not task:
                    # Remove invalid task ID
                    self.task_queue.pop(0)
                    continue
                
                if task.status == TaskStatus.QUEUED or (task.status == TaskStatus.FAILED and task.can_retry):
                    # Remove from queue and return
                    self.task_queue.pop(0)
                    return task
                else:
                    # Remove completed/cancelled tasks
                    self.task_queue.pop(0)
                    continue
            
            return None
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ):
        """Update task status."""
        with self.processing_lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            old_status = task.status
            task.status = status
            
            if status == TaskStatus.PROCESSING:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()
                
                if status == TaskStatus.COMPLETED:
                    self.stats.completed_tasks += 1
                elif status == TaskStatus.FAILED:
                    self.stats.failed_tasks += 1
                    if task.can_retry:
                        task.retry_count += 1
                        task.status = TaskStatus.RETRYING
                        self.stats.retried_tasks += 1
                        # Re-add to queue for retry
                        self._insert_task_by_priority(task_id)
                elif status == TaskStatus.CANCELLED:
                    self.stats.cancelled_tasks += 1
            
            if error_message:
                task.error_message = error_message
            
            if result:
                task.result = result
            
            logger.debug(f"Task {task_id} status: {old_status.value} -> {status.value}")
    
    async def process_queue(
        self,
        max_concurrent: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> BatchProcessingStats:
        """Process all tasks in the queue."""
        if self.is_processing:
            raise ProcessingError("Batch processing already in progress")
        
        max_concurrent = max_concurrent or self.config.max_concurrent_requests
        self.is_processing = True
        self.stop_processing = False
        self.stats.start_time = datetime.now()
        
        logger.info(f"Starting batch processing with {max_concurrent} concurrent workers")
        
        try:
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(max_concurrent)
            
            # Process tasks
            active_tasks = []
            
            while not self.stop_processing:
                # Start new tasks up to concurrency limit
                while len(active_tasks) < max_concurrent and not self.stop_processing:
                    next_task = self.get_next_task()
                    if not next_task:
                        break
                    
                    # Create processing coroutine
                    task_coroutine = self._process_single_task(next_task, semaphore)
                    active_tasks.append(asyncio.create_task(task_coroutine))
                
                # If no active tasks and no more tasks, we're done
                if not active_tasks:
                    break
                
                # Wait for at least one task to complete
                done, pending = await asyncio.wait(
                    active_tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                active_tasks = list(pending)  # Convert set back to list
                
                # Process completed tasks
                for completed_task in done:
                    try:
                        await completed_task
                    except Exception as e:
                        logger.error(f"Task processing error: {e}")
                
                # Report progress
                if progress_callback:
                    progress_info = {
                        'total_tasks': self.stats.total_tasks,
                        'completed_tasks': self.stats.completed_tasks,
                        'failed_tasks': self.stats.failed_tasks,
                        'active_tasks': len(active_tasks),
                        'queue_size': len(self.task_queue)
                    }
                    progress_callback(progress_info)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
            
            # Wait for remaining active tasks
            if active_tasks:
                await asyncio.gather(*active_tasks, return_exceptions=True)
            
            self.stats.end_time = datetime.now()
            
            # Calculate final statistics
            self._calculate_final_stats()
            
            # Save final state
            self._save_queue_to_file()
            self._save_stats_to_file()
            
            logger.info(f"Batch processing completed: {self.stats.completed_tasks}/{self.stats.total_tasks} successful")
            return self.stats
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise ProcessingError(f"Batch processing failed: {e}")
        finally:
            self.is_processing = False
    
    async def _process_single_task(self, task: ProcessingTask, semaphore: asyncio.Semaphore):
        """Process a single task."""
        async with semaphore:
            try:
                self.update_task_status(task.id, TaskStatus.PROCESSING)
                
                # Check cache first
                cached_knowledge = self.cache_manager.get_cached_knowledge_item(task.url)
                if cached_knowledge:
                    logger.info(f"Using cached knowledge for {task.url}")
                    self.update_task_status(
                        task.id,
                        TaskStatus.COMPLETED,
                        result={'knowledge_item_id': cached_knowledge.id, 'from_cache': True}
                    )
                    return
                
                # Process the URL (this would integrate with your scraping and processing pipeline)
                result = await self._process_url(task.url, task.metadata)
                
                self.update_task_status(
                    task.id,
                    TaskStatus.COMPLETED,
                    result=result
                )
                
                logger.info(f"Task completed successfully: {task.id}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Task failed: {task.id} - {error_msg}")
                
                self.update_task_status(
                    task.id,
                    TaskStatus.FAILED,
                    error_message=error_msg
                )
    
    async def _process_url(self, url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single URL (placeholder for actual processing pipeline)."""
        # This is a placeholder that would integrate with your actual scraping pipeline
        # For now, we'll simulate processing
        
        await asyncio.sleep(1)  # Simulate processing time
        
        # Add to cache manager's processing queue
        self.cache_manager.add_to_processing_queue(url, priority=5)
        
        return {
            'url': url,
            'processed_at': datetime.now().isoformat(),
            'metadata': metadata,
            'simulated': True
        }
    
    def _calculate_final_stats(self):
        """Calculate final processing statistics."""
        processing_times = []
        
        for task in self.tasks.values():
            if task.processing_time:
                processing_times.append(task.processing_time)
        
        if processing_times:
            self.stats.average_processing_time = sum(processing_times) / len(processing_times)
            self.stats.total_processing_time = sum(processing_times)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        with self.processing_lock:
            status_counts = {}
            for task in self.tasks.values():
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                'total_tasks': len(self.tasks),
                'queued_tasks': len(self.task_queue),
                'status_distribution': status_counts,
                'is_processing': self.is_processing,
                'stats': asdict(self.stats)
            }
    
    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific task."""
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task."""
        with self.processing_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status in [TaskStatus.QUEUED, TaskStatus.RETRYING]:
                self.update_task_status(task_id, TaskStatus.CANCELLED)
                
                # Remove from queue if present
                if task_id in self.task_queue:
                    self.task_queue.remove(task_id)
                
                return True
            
            return False
    
    def clear_completed_tasks(self) -> int:
        """Clear completed and failed tasks from memory."""
        with self.processing_lock:
            completed_statuses = [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            tasks_to_remove = [
                task_id for task_id, task in self.tasks.items()
                if task.status in completed_statuses
            ]
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            logger.info(f"Cleared {len(tasks_to_remove)} completed tasks")
            return len(tasks_to_remove)
    
    def stop_processing_queue(self):
        """Stop the current batch processing."""
        self.stop_processing = True
        logger.info("Batch processing stop requested")
    
    def _save_queue_to_file(self):
        """Save current queue state to file."""
        try:
            queue_data = {
                'tasks': {task_id: task.to_dict() for task_id, task in self.tasks.items()},
                'task_queue': self.task_queue,
                'stats': asdict(self.stats),
                'saved_at': datetime.now().isoformat()
            }
            
            self.queue_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save queue to file: {e}")
    
    def _load_queue_from_file(self):
        """Load queue state from file."""
        try:
            if not self.queue_file.exists():
                return
            
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                queue_data = json.load(f)
            
            # Restore tasks
            for task_id, task_data in queue_data.get('tasks', {}).items():
                try:
                    task = ProcessingTask.from_dict(task_data)
                    self.tasks[task_id] = task
                except Exception as e:
                    logger.warning(f"Failed to restore task {task_id}: {e}")
            
            # Restore queue order
            self.task_queue = queue_data.get('task_queue', [])
            
            # Restore stats
            stats_data = queue_data.get('stats', {})
            if stats_data:
                try:
                    # Convert datetime strings back to datetime objects
                    if stats_data.get('start_time'):
                        stats_data['start_time'] = datetime.fromisoformat(stats_data['start_time'])
                    if stats_data.get('end_time'):
                        stats_data['end_time'] = datetime.fromisoformat(stats_data['end_time'])
                    
                    self.stats = BatchProcessingStats(**stats_data)
                except Exception as e:
                    logger.warning(f"Failed to restore stats: {e}")
            
            logger.info(f"Loaded {len(self.tasks)} tasks from queue file")
            
        except Exception as e:
            logger.error(f"Failed to load queue from file: {e}")
    
    def _save_stats_to_file(self):
        """Save processing statistics to file."""
        try:
            stats_data = asdict(self.stats)
            
            # Convert datetime objects to strings
            if stats_data.get('start_time'):
                stats_data['start_time'] = self.stats.start_time.isoformat()
            if stats_data.get('end_time'):
                stats_data['end_time'] = self.stats.end_time.isoformat()
            
            stats_data['saved_at'] = datetime.now().isoformat()
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save stats to file: {e}")
    
    def export_results(self, output_path: str, include_failed: bool = False) -> bool:
        """Export processing results to JSON file."""
        try:
            results = {
                'export_date': datetime.now().isoformat(),
                'stats': asdict(self.stats),
                'tasks': []
            }
            
            # Convert stats datetime objects
            if results['stats'].get('start_time'):
                results['stats']['start_time'] = self.stats.start_time.isoformat()
            if results['stats'].get('end_time'):
                results['stats']['end_time'] = self.stats.end_time.isoformat()
            
            # Add task results
            for task in self.tasks.values():
                if task.status == TaskStatus.COMPLETED or (include_failed and task.status == TaskStatus.FAILED):
                    results['tasks'].append(task.to_dict())
            
            # Save to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results exported to: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export results: {e}")
            return False