"""Data models for the knowledge repository with serialization support."""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from ..models.knowledge_item import KnowledgeItem, Category
from ..models.post_content import PostContent, ImageData
from ..models.exceptions import StorageError
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KnowledgeRepository:
    """Main repository containing all knowledge items."""
    items: List[KnowledgeItem]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: str = "1.0"
    
    def __post_init__(self):
        """Initialize computed fields."""
        if not self.items:
            self.items = []
        
        if not self.metadata:
            self.metadata = {}
        
        # Update metadata with current stats
        self._update_metadata()
    
    def _update_metadata(self):
        """Update repository metadata with current statistics."""
        self.metadata.update({
            'total_items': len(self.items),
            'categories': self._get_category_distribution(),
            'date_range': self._get_date_range(),
            'sources': self._get_source_statistics(),
            'last_updated': datetime.now().isoformat()
        })
    
    def _get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of items by category."""
        distribution = {}
        for item in self.items:
            category = item.category.value
            distribution[category] = distribution.get(category, 0) + 1
        return distribution
    
    def _get_date_range(self) -> Dict[str, str]:
        """Get the date range of items in the repository."""
        if not self.items:
            return {'earliest': None, 'latest': None}
        
        dates = [item.extraction_date for item in self.items if item.extraction_date]
        if not dates:
            return {'earliest': None, 'latest': None}
        
        return {
            'earliest': min(dates).isoformat(),
            'latest': max(dates).isoformat()
        }
    
    def _get_source_statistics(self) -> Dict[str, int]:
        """Get statistics about source links."""
        sources = {}
        for item in self.items:
            domain = self._extract_domain(item.source_link)
            sources[domain] = sources.get(domain, 0) + 1
        return sources
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or 'unknown'
        except:
            return 'unknown'
    
    def add_item(self, item: KnowledgeItem) -> None:
        """Add a knowledge item to the repository."""
        if not isinstance(item, KnowledgeItem):
            raise StorageError("Item must be a KnowledgeItem instance")
        
        # Check for duplicates based on source link
        existing_urls = {item.source_link for item in self.items}
        if item.source_link in existing_urls:
            logger.warning(f"Duplicate item detected: {item.source_link}")
            return
        
        self.items.append(item)
        self.updated_at = datetime.now()
        self._update_metadata()
        
        logger.info(f"Added knowledge item: {item.id}")
    
    def remove_item(self, item_id: str) -> bool:
        """Remove a knowledge item by ID."""
        original_count = len(self.items)
        self.items = [item for item in self.items if item.id != item_id]
        
        if len(self.items) < original_count:
            self.updated_at = datetime.now()
            self._update_metadata()
            logger.info(f"Removed knowledge item: {item_id}")
            return True
        
        return False
    
    def get_item(self, item_id: str) -> Optional[KnowledgeItem]:
        """Get a knowledge item by ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None
    
    def get_items_by_category(self, category: Category) -> List[KnowledgeItem]:
        """Get all items in a specific category."""
        return [item for item in self.items if item.category == category]
    
    def get_items_by_topic(self, topic: str) -> List[KnowledgeItem]:
        """Get all items with a specific topic."""
        topic_lower = topic.lower()
        return [item for item in self.items if topic_lower in item.topic.lower()]
    
    def search_items(self, query: str) -> List[KnowledgeItem]:
        """Search items by content, title, or topic."""
        query_lower = query.lower()
        results = []
        
        for item in self.items:
            if (query_lower in item.post_title.lower() or
                query_lower in item.topic.lower() or
                query_lower in item.key_knowledge_content.lower() or
                query_lower in item.notes_applications.lower()):
                results.append(item)
        
        return results
    
    def get_recent_items(self, limit: int = 10) -> List[KnowledgeItem]:
        """Get the most recently added items."""
        sorted_items = sorted(self.items, key=lambda x: x.extraction_date, reverse=True)
        return sorted_items[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert repository to dictionary for serialization."""
        return {
            'items': [item.to_dict() for item in self.items],
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeRepository':
        """Create repository from dictionary."""
        items = [KnowledgeItem.from_dict(item_data) for item_data in data.get('items', [])]
        
        return cls(
            items=items,
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            version=data.get('version', '1.0')
        )
    
    def to_json(self) -> str:
        """Convert repository to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'KnowledgeRepository':
        """Create repository from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class RepositoryManager:
    """Manager for knowledge repository persistence and operations."""
    
    def __init__(self, repository_path: str):
        """Initialize the repository manager."""
        self.repository_path = Path(repository_path)
        self.repository_path.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.json_file = self.repository_path / "knowledge_repository.json"
        self.db_file = self.repository_path / "knowledge_repository.db"
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Repository manager initialized: {self.repository_path}")
    
    def _init_database(self):
        """Initialize SQLite database for fast queries."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Create knowledge items table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge_items (
                        id TEXT PRIMARY KEY,
                        topic TEXT NOT NULL,
                        post_title TEXT NOT NULL,
                        key_knowledge_content TEXT NOT NULL,
                        infographic_summary TEXT,
                        source_link TEXT NOT NULL,
                        notes_applications TEXT,
                        extraction_date TEXT NOT NULL,
                        category TEXT NOT NULL,
                        course_references TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for faster queries
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON knowledge_items(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_topic ON knowledge_items(topic)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_extraction_date ON knowledge_items(extraction_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_link ON knowledge_items(source_link)')
                
                # Create full-text search table
                cursor.execute('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_search USING fts5(
                        id,
                        topic,
                        post_title,
                        key_knowledge_content,
                        notes_applications,
                        content='knowledge_items',
                        content_rowid='rowid'
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            raise StorageError(f"Failed to initialize database: {e}")
    
    def save_repository(self, repository: KnowledgeRepository) -> None:
        """Save repository to both JSON and database."""
        try:
            # Save to JSON file
            with open(self.json_file, 'w', encoding='utf-8') as f:
                f.write(repository.to_json())
            
            # Save to database
            self._save_to_database(repository)
            
            logger.info(f"Repository saved: {len(repository.items)} items")
            
        except Exception as e:
            raise StorageError(f"Failed to save repository: {e}")
    
    def _save_to_database(self, repository: KnowledgeRepository) -> None:
        """Save repository items to SQLite database."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Clear existing data
                cursor.execute('DELETE FROM knowledge_items')
                cursor.execute('DELETE FROM knowledge_search')
                
                # Insert items
                for item in repository.items:
                    cursor.execute('''
                        INSERT INTO knowledge_items (
                            id, topic, post_title, key_knowledge_content,
                            infographic_summary, source_link, notes_applications,
                            extraction_date, category, course_references
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.id,
                        item.topic,
                        item.post_title,
                        item.key_knowledge_content,
                        item.infographic_summary,
                        item.source_link,
                        item.notes_applications,
                        item.extraction_date.isoformat(),
                        item.category.value,
                        json.dumps(item.course_references)
                    ))
                    
                    # Insert into search table
                    cursor.execute('''
                        INSERT INTO knowledge_search (
                            id, topic, post_title, key_knowledge_content, notes_applications
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        item.id,
                        item.topic,
                        item.post_title,
                        item.key_knowledge_content,
                        item.notes_applications
                    ))
                
                conn.commit()
                
        except Exception as e:
            raise StorageError(f"Failed to save to database: {e}")
    
    def load_repository(self) -> KnowledgeRepository:
        """Load repository from JSON file."""
        try:
            if self.json_file.exists():
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    json_data = f.read()
                
                repository = KnowledgeRepository.from_json(json_data)
                logger.info(f"Repository loaded: {len(repository.items)} items")
                return repository
            else:
                # Create new empty repository
                repository = KnowledgeRepository(
                    items=[],
                    metadata={},
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                logger.info("Created new empty repository")
                return repository
                
        except Exception as e:
            logger.error(f"Failed to load repository: {e}")
            # Return empty repository as fallback
            return KnowledgeRepository(
                items=[],
                metadata={},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
    
    def search_database(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search the database using full-text search."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Use FTS5 for full-text search
                cursor.execute('''
                    SELECT k.* FROM knowledge_items k
                    JOIN knowledge_search s ON k.id = s.id
                    WHERE knowledge_search MATCH ?
                    ORDER BY rank
                    LIMIT ?
                ''', (query, limit))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    result['course_references'] = json.loads(result['course_references'] or '[]')
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Database search failed: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics from database."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Total items
                cursor.execute('SELECT COUNT(*) FROM knowledge_items')
                total_items = cursor.fetchone()[0]
                
                # Category distribution
                cursor.execute('''
                    SELECT category, COUNT(*) as count 
                    FROM knowledge_items 
                    GROUP BY category 
                    ORDER BY count DESC
                ''')
                categories = dict(cursor.fetchall())
                
                # Recent activity
                cursor.execute('''
                    SELECT DATE(extraction_date) as date, COUNT(*) as count
                    FROM knowledge_items
                    WHERE extraction_date >= date('now', '-30 days')
                    GROUP BY DATE(extraction_date)
                    ORDER BY date DESC
                ''')
                recent_activity = dict(cursor.fetchall())
                
                return {
                    'total_items': total_items,
                    'categories': categories,
                    'recent_activity': recent_activity,
                    'database_file': str(self.db_file),
                    'json_file': str(self.json_file)
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def backup_repository(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the repository."""
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.repository_path / f"backup_{timestamp}.json"
            
            backup_path = Path(backup_path)
            
            # Copy JSON file
            if self.json_file.exists():
                import shutil
                shutil.copy2(self.json_file, backup_path)
                logger.info(f"Repository backed up to: {backup_path}")
                return str(backup_path)
            else:
                raise StorageError("No repository file to backup")
                
        except Exception as e:
            raise StorageError(f"Backup failed: {e}")
    
    def restore_repository(self, backup_path: str) -> KnowledgeRepository:
        """Restore repository from backup."""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise StorageError(f"Backup file not found: {backup_path}")
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                json_data = f.read()
            
            repository = KnowledgeRepository.from_json(json_data)
            
            # Save restored repository
            self.save_repository(repository)
            
            logger.info(f"Repository restored from: {backup_path}")
            return repository
            
        except Exception as e:
            raise StorageError(f"Restore failed: {e}")