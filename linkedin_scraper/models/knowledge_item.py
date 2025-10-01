"""Data models for knowledge items and categorization."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List
import uuid


class Category(Enum):
    """Categories for organizing knowledge content."""
    AI_MACHINE_LEARNING = "AI & Machine Learning"
    SAAS_BUSINESS = "SaaS & Business"
    MARKETING_SALES = "Marketing & Sales"
    LEADERSHIP_MANAGEMENT = "Leadership & Management"
    TECHNOLOGY_TRENDS = "Technology Trends"
    COURSE_CONTENT = "Course Content"
    OTHER = "Other"
    
    @classmethod
    def from_string(cls, category_str: str) -> 'Category':
        """Convert string to Category enum."""
        for category in cls:
            if category.value.lower() == category_str.lower():
                return category
        return cls.OTHER


@dataclass
class KnowledgeItem:
    """Represents a processed knowledge item extracted from a LinkedIn post."""
    topic: str
    post_title: str
    key_knowledge_content: str
    infographic_summary: str
    source_link: str
    notes_applications: str
    category: Category
    course_references: List[str]
    id: str = None
    extraction_date: datetime = None
    
    def __post_init__(self):
        """Initialize computed fields after object creation."""
        if self.id is None:
            self.id = str(uuid.uuid4())
        
        if self.extraction_date is None:
            self.extraction_date = datetime.now()
        
        # Ensure course_references is always a list
        if self.course_references is None:
            self.course_references = []
        
        # Validate required fields
        if not self.topic:
            raise ValueError("Topic cannot be empty")
        if not self.post_title:
            raise ValueError("Post title cannot be empty")
        if not self.key_knowledge_content:
            raise ValueError("Key knowledge content cannot be empty")
        if not self.source_link:
            raise ValueError("Source link cannot be empty")
    
    @property
    def has_course_references(self) -> bool:
        """Check if the knowledge item contains course references."""
        return len(self.course_references) > 0
    
    @property
    def has_infographics(self) -> bool:
        """Check if the knowledge item has infographic content."""
        return bool(self.infographic_summary.strip())
    
    def to_dict(self) -> dict:
        """Convert knowledge item to dictionary for serialization."""
        return {
            'id': self.id,
            'topic': self.topic,
            'post_title': self.post_title,
            'key_knowledge_content': self.key_knowledge_content,
            'infographic_summary': self.infographic_summary,
            'source_link': self.source_link,
            'notes_applications': self.notes_applications,
            'extraction_date': self.extraction_date.isoformat(),
            'category': self.category.value,
            'course_references': self.course_references
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'KnowledgeItem':
        """Create knowledge item from dictionary."""
        return cls(
            id=data.get('id'),
            topic=data['topic'],
            post_title=data['post_title'],
            key_knowledge_content=data['key_knowledge_content'],
            infographic_summary=data.get('infographic_summary', ''),
            source_link=data['source_link'],
            notes_applications=data.get('notes_applications', ''),
            extraction_date=datetime.fromisoformat(data['extraction_date']) if data.get('extraction_date') else None,
            category=Category.from_string(data.get('category', 'Other')),
            course_references=data.get('course_references', [])
        )