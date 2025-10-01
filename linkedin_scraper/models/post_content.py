"""Data models for LinkedIn post content."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ImageData:
    """Represents an image from a LinkedIn post."""
    url: str
    filename: str
    alt_text: str
    description: str
    local_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate image data after initialization."""
        if not self.url:
            raise ValueError("Image URL cannot be empty")
        if not self.filename:
            raise ValueError("Image filename cannot be empty")


@dataclass
class EngagementData:
    """Represents engagement metrics for a LinkedIn post."""
    likes: int = 0
    comments: int = 0
    shares: int = 0
    reactions: int = 0
    
    def __post_init__(self):
        """Validate engagement data after initialization."""
        if any(value < 0 for value in [self.likes, self.comments, self.shares, self.reactions]):
            raise ValueError("Engagement metrics cannot be negative")


@dataclass
class PostContent:
    """Represents the complete content of a LinkedIn post."""
    url: str
    title: str
    body_text: str
    author: str
    post_date: datetime
    images: List[ImageData]
    engagement_metrics: Optional[EngagementData] = None
    
    def __post_init__(self):
        """Validate post content after initialization."""
        if not self.url:
            raise ValueError("Post URL cannot be empty")
        if not self.body_text:
            raise ValueError("Post body text cannot be empty")
        if not self.author:
            raise ValueError("Post author cannot be empty")
        
        # Ensure images is always a list
        if self.images is None:
            self.images = []
    
    @property
    def has_images(self) -> bool:
        """Check if the post contains images."""
        return len(self.images) > 0
    
    @property
    def image_count(self) -> int:
        """Get the number of images in the post."""
        return len(self.images)