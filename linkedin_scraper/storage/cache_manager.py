"""Cache manager for deduplication and performance optimization."""

import sqlite3
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import threading

from ..models.knowledge_item import KnowledgeItem
from ..models.post_content import PostContent
from ..models.exceptions import StorageError
from ..utils.config import Config
from ..utils.logger import get_logger
from ..scrapers.url_parser import LinkedInURLParser

logger = get_logger(__name__)


class CacheManager:
    """Manager for caching and deduplication of LinkedIn posts and knowledge items."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the cache manager."""
        self.config = config or Config.from_env()
        
        # Cache database path
        self.cache_db_path = Path(self.config.cache_db_path)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for database operations
        self._db_lock = threading.Lock()
        
        # Initialize database
        self._init_cache_database()
        
        # Cache statistics
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'items_cached': 0,
            'duplicates_prevented': 0
        }
        
        logger.info(f"Cache manager initialized: {self.cache_db_path}")
    
    def _init_cache_database(self):
        """Initialize the cache database with required tables."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # URL cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS url_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_url TEXT NOT NULL,
                        normalized_url TEXT NOT NULL UNIQUE,
                        url_hash TEXT NOT NULL UNIQUE,
                        post_type TEXT,
                        post_id TEXT,
                        author_id TEXT,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1,
                        processing_status TEXT DEFAULT 'pending',
                        error_message TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Content cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS content_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url_hash TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        post_title TEXT,
                        post_author TEXT,
                        post_date TIMESTAMP,
                        body_text TEXT,
                        image_count INTEGER DEFAULT 0,
                        engagement_data TEXT,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1,
                        content_size INTEGER,
                        FOREIGN KEY (url_hash) REFERENCES url_cache (url_hash)
                    )
                ''')
                
                # Knowledge item cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        knowledge_id TEXT NOT NULL UNIQUE,
                        url_hash TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        topic TEXT,
                        category TEXT,
                        key_knowledge_content TEXT,
                        infographic_summary TEXT,
                        notes_applications TEXT,
                        course_references TEXT,
                        extraction_date TIMESTAMP,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processing_time_ms INTEGER,
                        FOREIGN KEY (url_hash) REFERENCES url_cache (url_hash)
                    )
                ''')
                
                # Processing queue table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processing_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url_hash TEXT NOT NULL,
                        priority INTEGER DEFAULT 5,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processing_started TIMESTAMP,
                        processing_completed TIMESTAMP,
                        status TEXT DEFAULT 'queued',
                        retry_count INTEGER DEFAULT 0,
                        error_message TEXT,
                        FOREIGN KEY (url_hash) REFERENCES url_cache (url_hash)
                    )
                ''')
                
                # Create indexes for performance
                indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_url_hash ON url_cache(url_hash)',
                    'CREATE INDEX IF NOT EXISTS idx_normalized_url ON url_cache(normalized_url)',
                    'CREATE INDEX IF NOT EXISTS idx_content_hash ON content_cache(content_hash)',
                    'CREATE INDEX IF NOT EXISTS idx_knowledge_id ON knowledge_cache(knowledge_id)',
                    'CREATE INDEX IF NOT EXISTS idx_processing_status ON url_cache(processing_status)',
                    'CREATE INDEX IF NOT EXISTS idx_queue_status ON processing_queue(status)',
                    'CREATE INDEX IF NOT EXISTS idx_last_accessed ON url_cache(last_accessed)',
                ]
                
                for index_sql in indexes:
                    cursor.execute(index_sql)
                
                conn.commit()
                logger.debug("Cache database initialized successfully")
                
        except Exception as e:
            raise StorageError(f"Failed to initialize cache database: {e}")
    
    def generate_url_hash(self, url: str) -> str:
        """Generate a consistent hash for a URL."""
        try:
            # Parse and normalize URL first
            post_info = LinkedInURLParser.parse_url(url)
            normalized_url = post_info.normalized_url
            
            # Generate hash from normalized URL
            return hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()[:16]
            
        except Exception as e:
            # Fallback to direct URL hash if parsing fails
            logger.warning(f"URL parsing failed, using direct hash: {e}")
            return hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    
    def is_url_cached(self, url: str) -> bool:
        """Check if a URL is already cached."""
        try:
            url_hash = self.generate_url_hash(url)
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id FROM url_cache WHERE url_hash = ?',
                    (url_hash,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Update access statistics
                    cursor.execute('''
                        UPDATE url_cache 
                        SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                        WHERE url_hash = ?
                    ''', (url_hash,))
                    conn.commit()
                    
                    self._stats['cache_hits'] += 1
                    return True
                else:
                    self._stats['cache_misses'] += 1
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking URL cache: {e}")
            return False
    
    def cache_url(
        self,
        url: str,
        post_type: str = None,
        post_id: str = None,
        author_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Cache a URL with metadata."""
        try:
            url_hash = self.generate_url_hash(url)
            
            # Parse URL for additional info
            try:
                post_info = LinkedInURLParser.parse_url(url)
                normalized_url = post_info.normalized_url
                post_type = post_type or post_info.post_type
                post_id = post_id or post_info.post_id
                author_id = author_id or post_info.author_id
            except:
                normalized_url = url
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Insert or update URL cache
                cursor.execute('''
                    INSERT OR REPLACE INTO url_cache 
                    (original_url, normalized_url, url_hash, post_type, post_id, author_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    url,
                    normalized_url,
                    url_hash,
                    post_type,
                    post_id,
                    author_id,
                    json.dumps(metadata) if metadata else None
                ))
                
                conn.commit()
                self._stats['items_cached'] += 1
                
                logger.debug(f"URL cached: {url_hash}")
                return url_hash
                
        except Exception as e:
            logger.error(f"Failed to cache URL: {e}")
            raise StorageError(f"URL caching failed: {e}")
    
    def get_cached_url_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached information for a URL."""
        try:
            url_hash = self.generate_url_hash(url)
            
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM url_cache WHERE url_hash = ?
                ''', (url_hash,))
                
                row = cursor.fetchone()
                if row:
                    # Update access statistics
                    cursor.execute('''
                        UPDATE url_cache 
                        SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                        WHERE url_hash = ?
                    ''', (url_hash,))
                    conn.commit()
                    
                    # Convert to dictionary
                    result = dict(row)
                    if result['metadata']:
                        result['metadata'] = json.loads(result['metadata'])
                    
                    return result
                
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached URL info: {e}")
            return None
    
    def cache_post_content(self, url: str, post_content: PostContent) -> str:
        """Cache post content."""
        try:
            url_hash = self.generate_url_hash(url)
            
            # Generate content hash
            content_data = {
                'title': post_content.title,
                'body_text': post_content.body_text,
                'author': post_content.author,
                'post_date': post_content.post_date.isoformat() if post_content.post_date else None
            }
            content_str = json.dumps(content_data, sort_keys=True)
            content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()[:16]
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Cache content
                cursor.execute('''
                    INSERT OR REPLACE INTO content_cache 
                    (url_hash, content_hash, post_title, post_author, post_date, 
                     body_text, image_count, engagement_data, content_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    url_hash,
                    content_hash,
                    post_content.title,
                    post_content.author,
                    post_content.post_date.isoformat() if post_content.post_date else None,
                    post_content.body_text,
                    len(post_content.images),
                    json.dumps(post_content.engagement_metrics.__dict__ if post_content.engagement_metrics else {}),
                    len(post_content.body_text)
                ))
                
                conn.commit()
                logger.debug(f"Content cached: {content_hash}")
                return content_hash
                
        except Exception as e:
            logger.error(f"Failed to cache content: {e}")
            raise StorageError(f"Content caching failed: {e}")
    
    def get_cached_content(self, url: str) -> Optional[PostContent]:
        """Get cached post content."""
        try:
            url_hash = self.generate_url_hash(url)
            
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM content_cache WHERE url_hash = ?
                ''', (url_hash,))
                
                row = cursor.fetchone()
                if row:
                    # Update access statistics
                    cursor.execute('''
                        UPDATE content_cache 
                        SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                        WHERE url_hash = ?
                    ''', (url_hash,))
                    conn.commit()
                    
                    # Reconstruct PostContent
                    from ..models.post_content import EngagementData
                    
                    engagement_data = None
                    if row['engagement_data']:
                        engagement_dict = json.loads(row['engagement_data'])
                        engagement_data = EngagementData(**engagement_dict)
                    
                    post_content = PostContent(
                        url=url,
                        title=row['post_title'] or '',
                        body_text=row['body_text'] or '',
                        author=row['post_author'] or '',
                        post_date=datetime.fromisoformat(row['post_date']) if row['post_date'] else datetime.now(),
                        images=[],  # Images not cached in this table
                        engagement_metrics=engagement_data
                    )
                    
                    return post_content
                
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached content: {e}")
            return None
    
    def cache_knowledge_item(self, knowledge_item: KnowledgeItem, processing_time_ms: int = 0) -> str:
        """Cache a processed knowledge item."""
        try:
            url_hash = self.generate_url_hash(knowledge_item.source_link)
            
            # Generate content hash for deduplication
            content_data = {
                'key_knowledge_content': knowledge_item.key_knowledge_content,
                'topic': knowledge_item.topic,
                'category': knowledge_item.category.value
            }
            content_str = json.dumps(content_data, sort_keys=True)
            content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()[:16]
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Check for duplicate content
                cursor.execute('''
                    SELECT knowledge_id FROM knowledge_cache WHERE content_hash = ?
                ''', (content_hash,))
                
                existing = cursor.fetchone()
                if existing:
                    self._stats['duplicates_prevented'] += 1
                    logger.info(f"Duplicate knowledge content detected: {content_hash}")
                    return existing[0]
                
                # Cache knowledge item
                cursor.execute('''
                    INSERT OR REPLACE INTO knowledge_cache 
                    (knowledge_id, url_hash, content_hash, topic, category, 
                     key_knowledge_content, infographic_summary, notes_applications,
                     course_references, extraction_date, processing_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    knowledge_item.id,
                    url_hash,
                    content_hash,
                    knowledge_item.topic,
                    knowledge_item.category.value,
                    knowledge_item.key_knowledge_content,
                    knowledge_item.infographic_summary,
                    knowledge_item.notes_applications,
                    json.dumps(knowledge_item.course_references),
                    knowledge_item.extraction_date.isoformat() if knowledge_item.extraction_date else None,
                    processing_time_ms
                ))
                
                conn.commit()
                logger.debug(f"Knowledge item cached: {knowledge_item.id}")
                return knowledge_item.id
                
        except Exception as e:
            logger.error(f"Failed to cache knowledge item: {e}")
            raise StorageError(f"Knowledge item caching failed: {e}")
    
    def get_cached_knowledge_item(self, url: str) -> Optional[KnowledgeItem]:
        """Get cached knowledge item for a URL."""
        try:
            url_hash = self.generate_url_hash(url)
            
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM knowledge_cache WHERE url_hash = ?
                ''', (url_hash,))
                
                row = cursor.fetchone()
                if row:
                    # Update access statistics
                    cursor.execute('''
                        UPDATE knowledge_cache 
                        SET last_accessed = CURRENT_TIMESTAMP
                        WHERE url_hash = ?
                    ''', (url_hash,))
                    conn.commit()
                    
                    # Reconstruct KnowledgeItem
                    from ..models.knowledge_item import Category
                    
                    knowledge_item = KnowledgeItem(
                        id=row['knowledge_id'],
                        topic=row['topic'],
                        post_title='',  # Not stored in this cache
                        key_knowledge_content=row['key_knowledge_content'],
                        infographic_summary=row['infographic_summary'] or '',
                        source_link=url,
                        notes_applications=row['notes_applications'] or '',
                        category=Category.from_string(row['category']),
                        course_references=json.loads(row['course_references']) if row['course_references'] else [],
                        extraction_date=datetime.fromisoformat(row['extraction_date']) if row['extraction_date'] else None
                    )
                    
                    return knowledge_item
                
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached knowledge item: {e}")
            return None
    
    def add_to_processing_queue(self, url: str, priority: int = 5) -> bool:
        """Add a URL to the processing queue."""
        try:
            url_hash = self.generate_url_hash(url)
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Check if already in queue
                cursor.execute('''
                    SELECT id FROM processing_queue 
                    WHERE url_hash = ? AND status IN ('queued', 'processing')
                ''', (url_hash,))
                
                if cursor.fetchone():
                    logger.debug(f"URL already in processing queue: {url_hash}")
                    return False
                
                # Add to queue
                cursor.execute('''
                    INSERT INTO processing_queue (url_hash, priority)
                    VALUES (?, ?)
                ''', (url_hash, priority))
                
                conn.commit()
                logger.debug(f"URL added to processing queue: {url_hash}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add URL to processing queue: {e}")
            return False
    
    def get_next_from_queue(self) -> Optional[Dict[str, Any]]:
        """Get the next URL from the processing queue."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get highest priority queued item
                cursor.execute('''
                    SELECT pq.*, uc.original_url, uc.normalized_url
                    FROM processing_queue pq
                    JOIN url_cache uc ON pq.url_hash = uc.url_hash
                    WHERE pq.status = 'queued'
                    ORDER BY pq.priority DESC, pq.added_at ASC
                    LIMIT 1
                ''')
                
                row = cursor.fetchone()
                if row:
                    # Mark as processing
                    cursor.execute('''
                        UPDATE processing_queue 
                        SET status = 'processing', processing_started = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (row['id'],))
                    
                    conn.commit()
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting next item from queue: {e}")
            return None
    
    def mark_processing_complete(self, url_hash: str, success: bool = True, error_message: str = None):
        """Mark a processing queue item as complete."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                status = 'completed' if success else 'failed'
                
                cursor.execute('''
                    UPDATE processing_queue 
                    SET status = ?, processing_completed = CURRENT_TIMESTAMP, error_message = ?
                    WHERE url_hash = ? AND status = 'processing'
                ''', (status, error_message, url_hash))
                
                # Also update URL cache status
                cursor.execute('''
                    UPDATE url_cache 
                    SET processing_status = ?, error_message = ?
                    WHERE url_hash = ?
                ''', (status, error_message, url_hash))
                
                conn.commit()
                logger.debug(f"Processing marked as {status}: {url_hash}")
                
        except Exception as e:
            logger.error(f"Failed to mark processing complete: {e}")
    
    def cleanup_old_cache(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old cache entries."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleanup_stats = {
                'urls_removed': 0,
                'content_removed': 0,
                'knowledge_removed': 0,
                'queue_cleaned': 0
            }
            
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Clean old queue entries
                cursor.execute('''
                    DELETE FROM processing_queue 
                    WHERE status IN ('completed', 'failed') 
                    AND processing_completed < ?
                ''', (cutoff_date.isoformat(),))
                cleanup_stats['queue_cleaned'] = cursor.rowcount
                
                # Clean old content cache (keep frequently accessed items longer)
                cursor.execute('''
                    DELETE FROM content_cache 
                    WHERE last_accessed < ? AND access_count < 3
                ''', (cutoff_date.isoformat(),))
                cleanup_stats['content_removed'] = cursor.rowcount
                
                # Clean old URL cache (keep if referenced by knowledge items)
                cursor.execute('''
                    DELETE FROM url_cache 
                    WHERE last_accessed < ? 
                    AND url_hash NOT IN (SELECT DISTINCT url_hash FROM knowledge_cache)
                    AND processing_status NOT IN ('pending', 'processing')
                ''', (cutoff_date.isoformat(),))
                cleanup_stats['urls_removed'] = cursor.rowcount
                
                conn.commit()
                
                # Vacuum database to reclaim space
                cursor.execute('VACUUM')
                
                logger.info(f"Cache cleanup completed: {cleanup_stats}")
                return cleanup_stats
                
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return {'urls_removed': 0, 'content_removed': 0, 'knowledge_removed': 0, 'queue_cleaned': 0}
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                stats = dict(self._stats)
                
                # Database statistics
                cursor.execute('SELECT COUNT(*) FROM url_cache')
                stats['total_urls_cached'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM content_cache')
                stats['total_content_cached'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM knowledge_cache')
                stats['total_knowledge_cached'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM processing_queue WHERE status = "queued"')
                stats['queue_pending'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM processing_queue WHERE status = "processing"')
                stats['queue_processing'] = cursor.fetchone()[0]
                
                # Cache hit rate
                total_requests = stats['cache_hits'] + stats['cache_misses']
                stats['cache_hit_rate'] = (stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
                
                # Database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                stats['database_size_mb'] = db_size / (1024 * 1024)
                
                stats['last_updated'] = datetime.now().isoformat()
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return dict(self._stats)
    
    def invalidate_cache(self, url: str = None, content_hash: str = None) -> bool:
        """Invalidate cache entries."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()
                
                if url:
                    url_hash = self.generate_url_hash(url)
                    
                    # Remove from all cache tables
                    cursor.execute('DELETE FROM knowledge_cache WHERE url_hash = ?', (url_hash,))
                    cursor.execute('DELETE FROM content_cache WHERE url_hash = ?', (url_hash,))
                    cursor.execute('DELETE FROM processing_queue WHERE url_hash = ?', (url_hash,))
                    cursor.execute('DELETE FROM url_cache WHERE url_hash = ?', (url_hash,))
                    
                elif content_hash:
                    # Remove by content hash
                    cursor.execute('DELETE FROM knowledge_cache WHERE content_hash = ?', (content_hash,))
                    cursor.execute('DELETE FROM content_cache WHERE content_hash = ?', (content_hash,))
                
                conn.commit()
                logger.info(f"Cache invalidated for {'URL: ' + url if url else 'content hash: ' + content_hash}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return False
    
    def export_cache_data(self, output_path: str) -> bool:
        """Export cache data to JSON file."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                export_data = {
                    'export_date': datetime.now().isoformat(),
                    'statistics': self.get_cache_statistics(),
                    'url_cache': [],
                    'content_cache': [],
                    'knowledge_cache': []
                }
                
                # Export URL cache
                cursor.execute('SELECT * FROM url_cache')
                export_data['url_cache'] = [dict(row) for row in cursor.fetchall()]
                
                # Export content cache
                cursor.execute('SELECT * FROM content_cache')
                export_data['content_cache'] = [dict(row) for row in cursor.fetchall()]
                
                # Export knowledge cache
                cursor.execute('SELECT * FROM knowledge_cache')
                export_data['knowledge_cache'] = [dict(row) for row in cursor.fetchall()]
                
                # Save to file
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Cache data exported to: {output_file}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to export cache data: {e}")
            return False