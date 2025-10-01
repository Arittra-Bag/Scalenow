"""Enhanced content caching service for knowledge items with search and retrieval."""

import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

from ..models.knowledge_item import KnowledgeItem, Category
from ..models.post_content import PostContent
from ..models.exceptions import StorageError
from ..utils.config import Config
from ..utils.logger import get_logger
from ..storage.cache_manager import CacheManager

logger = get_logger(__name__)


class ContentCacheService:
    """Enhanced service for caching and retrieving knowledge items with advanced search."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the content cache service."""
        self.config = config or Config.from_env()
        self.cache_manager = CacheManager(config)
        
        # Initialize enhanced search database
        self._init_search_database()
        
        logger.info("Content cache service initialized")
    
    def _init_search_database(self):
        """Initialize enhanced search capabilities."""
        try:
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Create full-text search table for knowledge items
                cursor.execute('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_search USING fts5(
                        knowledge_id,
                        topic,
                        post_title,
                        key_knowledge_content,
                        notes_applications,
                        category,
                        course_references,
                        content='knowledge_cache',
                        content_rowid='id'
                    )
                ''')
                
                # Create similarity index table for duplicate detection
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS content_similarity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        knowledge_id_1 TEXT NOT NULL,
                        knowledge_id_2 TEXT NOT NULL,
                        similarity_score REAL NOT NULL,
                        similarity_type TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(knowledge_id_1, knowledge_id_2)
                    )
                ''')
                
                # Create topic clustering table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS topic_clusters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cluster_name TEXT NOT NULL,
                        topic_keywords TEXT NOT NULL,
                        knowledge_ids TEXT NOT NULL,
                        cluster_size INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize search database: {e}")
    
    def cache_knowledge_item_enhanced(
        self,
        knowledge_item: KnowledgeItem,
        post_content: Optional[PostContent] = None,
        processing_time_ms: int = 0
    ) -> Tuple[str, bool]:
        """Cache knowledge item with enhanced features and duplicate detection."""
        try:
            # Check for similar content first
            similar_items = self.find_similar_content(knowledge_item)
            
            if similar_items:
                logger.info(f"Similar content found for {knowledge_item.id}: {len(similar_items)} matches")
                # Return the most similar existing item ID
                return similar_items[0]['knowledge_id'], False
            
            # Cache the knowledge item
            cached_id = self.cache_manager.cache_knowledge_item(knowledge_item, processing_time_ms)
            
            # Cache post content if provided
            if post_content:
                self.cache_manager.cache_post_content(knowledge_item.source_link, post_content)
            
            # Update search index
            self._update_search_index(knowledge_item)
            
            # Update topic clusters
            self._update_topic_clusters(knowledge_item)
            
            return cached_id, True
            
        except Exception as e:
            logger.error(f"Enhanced caching failed: {e}")
            raise StorageError(f"Enhanced knowledge caching failed: {e}")
    
    def find_similar_content(
        self,
        knowledge_item: KnowledgeItem,
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Find similar knowledge items based on content similarity."""
        try:
            similar_items = []
            
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Search by category and topic first
                cursor.execute('''
                    SELECT knowledge_id, topic, key_knowledge_content, category
                    FROM knowledge_cache
                    WHERE category = ? AND topic LIKE ?
                    ORDER BY last_accessed DESC
                    LIMIT 20
                ''', (knowledge_item.category.value, f"%{knowledge_item.topic}%"))
                
                candidates = cursor.fetchall()
                
                # Calculate similarity scores
                for candidate in candidates:
                    similarity_score = self._calculate_content_similarity(
                        knowledge_item.key_knowledge_content,
                        candidate['key_knowledge_content']
                    )
                    
                    if similarity_score >= similarity_threshold:
                        similar_items.append({
                            'knowledge_id': candidate['knowledge_id'],
                            'topic': candidate['topic'],
                            'category': candidate['category'],
                            'similarity_score': similarity_score
                        })
                        
                        # Store similarity relationship
                        self._store_similarity_relationship(
                            knowledge_item.id,
                            candidate['knowledge_id'],
                            similarity_score,
                            'content_similarity'
                        )
            
            # Sort by similarity score
            similar_items.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_items
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        try:
            # Simple word-based similarity (can be enhanced with more sophisticated algorithms)
            words1 = set(content1.lower().split())
            words2 = set(content2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            # Jaccard similarity
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            jaccard_similarity = intersection / union if union > 0 else 0.0
            
            # Length similarity factor
            len1, len2 = len(content1), len(content2)
            length_similarity = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 0.0
            
            # Combined similarity score
            combined_similarity = (jaccard_similarity * 0.7) + (length_similarity * 0.3)
            
            return combined_similarity
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def _store_similarity_relationship(
        self,
        knowledge_id_1: str,
        knowledge_id_2: str,
        similarity_score: float,
        similarity_type: str
    ):
        """Store similarity relationship between knowledge items."""
        try:
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO content_similarity
                    (knowledge_id_1, knowledge_id_2, similarity_score, similarity_type)
                    VALUES (?, ?, ?, ?)
                ''', (knowledge_id_1, knowledge_id_2, similarity_score, similarity_type))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store similarity relationship: {e}")
    
    def _update_search_index(self, knowledge_item: KnowledgeItem):
        """Update the full-text search index."""
        try:
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Insert into search index
                cursor.execute('''
                    INSERT OR REPLACE INTO knowledge_search
                    (knowledge_id, topic, post_title, key_knowledge_content, 
                     notes_applications, category, course_references)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    knowledge_item.id,
                    knowledge_item.topic,
                    knowledge_item.post_title,
                    knowledge_item.key_knowledge_content,
                    knowledge_item.notes_applications,
                    knowledge_item.category.value,
                    ', '.join(knowledge_item.course_references)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update search index: {e}")
    
    def _update_topic_clusters(self, knowledge_item: KnowledgeItem):
        """Update topic clusters with new knowledge item."""
        try:
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Find existing cluster for this topic/category
                cursor.execute('''
                    SELECT id, knowledge_ids, cluster_size
                    FROM topic_clusters
                    WHERE cluster_name = ?
                ''', (f"{knowledge_item.category.value}_{knowledge_item.topic}",))
                
                cluster = cursor.fetchone()
                
                if cluster:
                    # Update existing cluster
                    knowledge_ids = json.loads(cluster[1])
                    if knowledge_item.id not in knowledge_ids:
                        knowledge_ids.append(knowledge_item.id)
                        
                        cursor.execute('''
                            UPDATE topic_clusters
                            SET knowledge_ids = ?, cluster_size = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (json.dumps(knowledge_ids), len(knowledge_ids), cluster[0]))
                else:
                    # Create new cluster
                    topic_keywords = self._extract_topic_keywords(knowledge_item)
                    
                    cursor.execute('''
                        INSERT INTO topic_clusters
                        (cluster_name, topic_keywords, knowledge_ids, cluster_size)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        f"{knowledge_item.category.value}_{knowledge_item.topic}",
                        json.dumps(topic_keywords),
                        json.dumps([knowledge_item.id]),
                        1
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update topic clusters: {e}")
    
    def _extract_topic_keywords(self, knowledge_item: KnowledgeItem) -> List[str]:
        """Extract keywords from knowledge item for clustering."""
        try:
            # Simple keyword extraction (can be enhanced with NLP)
            text = f"{knowledge_item.topic} {knowledge_item.key_knowledge_content}"
            words = text.lower().split()
            
            # Filter out common words and short words
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
            
            keywords = [word for word in words if len(word) > 3 and word not in stop_words]
            
            # Return top 10 most frequent keywords
            from collections import Counter
            keyword_counts = Counter(keywords)
            return [word for word, count in keyword_counts.most_common(10)]
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
    
    def search_cached_content(
        self,
        query: str,
        category: Optional[Category] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search cached knowledge items with full-text search."""
        try:
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build search query
                if category:
                    search_query = f"{query} AND category:{category.value}"
                else:
                    search_query = query
                
                # Perform full-text search
                cursor.execute('''
                    SELECT ks.*, kc.extraction_date, kc.last_accessed
                    FROM knowledge_search ks
                    JOIN knowledge_cache kc ON ks.knowledge_id = kc.knowledge_id
                    WHERE knowledge_search MATCH ?
                    ORDER BY rank
                    LIMIT ?
                ''', (search_query, limit))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    result['course_references'] = result['course_references'].split(', ') if result['course_references'] else []
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Content search failed: {e}")
            return []
    
    def get_related_content(
        self,
        knowledge_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get content related to a specific knowledge item."""
        try:
            related_items = []
            
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get similar items from similarity table
                cursor.execute('''
                    SELECT cs.knowledge_id_2 as related_id, cs.similarity_score,
                           kc.topic, kc.category, kc.key_knowledge_content
                    FROM content_similarity cs
                    JOIN knowledge_cache kc ON cs.knowledge_id_2 = kc.knowledge_id
                    WHERE cs.knowledge_id_1 = ?
                    ORDER BY cs.similarity_score DESC
                    LIMIT ?
                ''', (knowledge_id, limit))
                
                for row in cursor.fetchall():
                    related_items.append(dict(row))
                
                # If not enough similar items, get items from same category/topic
                if len(related_items) < limit:
                    cursor.execute('''
                        SELECT topic, category FROM knowledge_cache WHERE knowledge_id = ?
                    ''', (knowledge_id,))
                    
                    item_info = cursor.fetchone()
                    if item_info:
                        cursor.execute('''
                            SELECT knowledge_id as related_id, topic, category, 
                                   key_knowledge_content, 0.5 as similarity_score
                            FROM knowledge_cache
                            WHERE category = ? AND topic LIKE ? AND knowledge_id != ?
                            ORDER BY last_accessed DESC
                            LIMIT ?
                        ''', (
                            item_info['category'],
                            f"%{item_info['topic']}%",
                            knowledge_id,
                            limit - len(related_items)
                        ))
                        
                        for row in cursor.fetchall():
                            related_items.append(dict(row))
                
                return related_items
                
        except Exception as e:
            logger.error(f"Failed to get related content: {e}")
            return []
    
    def get_topic_clusters(self, min_cluster_size: int = 2) -> List[Dict[str, Any]]:
        """Get topic clusters with their knowledge items."""
        try:
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM topic_clusters
                    WHERE cluster_size >= ?
                    ORDER BY cluster_size DESC, updated_at DESC
                ''', (min_cluster_size,))
                
                clusters = []
                for row in cursor.fetchall():
                    cluster = dict(row)
                    cluster['topic_keywords'] = json.loads(cluster['topic_keywords'])
                    cluster['knowledge_ids'] = json.loads(cluster['knowledge_ids'])
                    clusters.append(cluster)
                
                return clusters
                
        except Exception as e:
            logger.error(f"Failed to get topic clusters: {e}")
            return []
    
    def get_content_analytics(self) -> Dict[str, Any]:
        """Get analytics about cached content."""
        try:
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                cursor = conn.cursor()
                
                analytics = {}
                
                # Category distribution
                cursor.execute('''
                    SELECT category, COUNT(*) as count
                    FROM knowledge_cache
                    GROUP BY category
                    ORDER BY count DESC
                ''')
                analytics['category_distribution'] = dict(cursor.fetchall())
                
                # Topic trends
                cursor.execute('''
                    SELECT topic, COUNT(*) as count
                    FROM knowledge_cache
                    GROUP BY topic
                    ORDER BY count DESC
                    LIMIT 10
                ''')
                analytics['top_topics'] = dict(cursor.fetchall())
                
                # Content similarity statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_similarities,
                        AVG(similarity_score) as avg_similarity,
                        MAX(similarity_score) as max_similarity
                    FROM content_similarity
                ''')
                similarity_stats = cursor.fetchone()
                analytics['similarity_stats'] = {
                    'total_similarities': similarity_stats[0],
                    'avg_similarity': round(similarity_stats[1], 3) if similarity_stats[1] else 0,
                    'max_similarity': round(similarity_stats[2], 3) if similarity_stats[2] else 0
                }
                
                # Cluster statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_clusters,
                        AVG(cluster_size) as avg_cluster_size,
                        MAX(cluster_size) as max_cluster_size
                    FROM topic_clusters
                ''')
                cluster_stats = cursor.fetchone()
                analytics['cluster_stats'] = {
                    'total_clusters': cluster_stats[0],
                    'avg_cluster_size': round(cluster_stats[1], 1) if cluster_stats[1] else 0,
                    'max_cluster_size': cluster_stats[2] if cluster_stats[2] else 0
                }
                
                # Recent activity
                cursor.execute('''
                    SELECT DATE(cached_at) as date, COUNT(*) as count
                    FROM knowledge_cache
                    WHERE cached_at >= date('now', '-30 days')
                    GROUP BY DATE(cached_at)
                    ORDER BY date DESC
                ''')
                analytics['recent_activity'] = dict(cursor.fetchall())
                
                analytics['generated_at'] = datetime.now().isoformat()
                
                return analytics
                
        except Exception as e:
            logger.error(f"Failed to get content analytics: {e}")
            return {}
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache performance and storage."""
        try:
            optimization_results = {
                'duplicates_merged': 0,
                'clusters_updated': 0,
                'similarities_calculated': 0,
                'index_rebuilt': False
            }
            
            with sqlite3.connect(self.cache_manager.cache_db_path) as conn:
                cursor = conn.cursor()
                
                # Rebuild search index
                cursor.execute('DELETE FROM knowledge_search')
                cursor.execute('''
                    INSERT INTO knowledge_search
                    (knowledge_id, topic, post_title, key_knowledge_content, 
                     notes_applications, category, course_references)
                    SELECT knowledge_id, topic, '', key_knowledge_content,
                           notes_applications, category, course_references
                    FROM knowledge_cache
                ''')
                optimization_results['index_rebuilt'] = True
                
                # Update topic clusters
                cursor.execute('DELETE FROM topic_clusters')
                
                # Recalculate clusters
                cursor.execute('''
                    SELECT DISTINCT category, topic FROM knowledge_cache
                ''')
                
                category_topics = cursor.fetchall()
                for category, topic in category_topics:
                    cursor.execute('''
                        SELECT knowledge_id FROM knowledge_cache
                        WHERE category = ? AND topic = ?
                    ''', (category, topic))
                    
                    knowledge_ids = [row[0] for row in cursor.fetchall()]
                    
                    if len(knowledge_ids) > 1:
                        cursor.execute('''
                            INSERT INTO topic_clusters
                            (cluster_name, topic_keywords, knowledge_ids, cluster_size)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            f"{category}_{topic}",
                            json.dumps([topic.lower()]),
                            json.dumps(knowledge_ids),
                            len(knowledge_ids)
                        ))
                        optimization_results['clusters_updated'] += 1
                
                conn.commit()
                
                # Vacuum database
                cursor.execute('VACUUM')
                
                logger.info(f"Cache optimization completed: {optimization_results}")
                return optimization_results
                
        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            return optimization_results