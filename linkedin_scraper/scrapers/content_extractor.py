"""Content extraction and processing utilities for scraped LinkedIn data."""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from ..models.post_content import PostContent, ImageData
from ..models.exceptions import ProcessingError
from ..utils.logger import get_logger
from ..utils.validators import URLValidator

logger = get_logger(__name__)


class ContentExtractor:
    """Extracts and processes content from scraped LinkedIn posts."""
    
    def __init__(self):
        """Initialize the content extractor."""
        # Patterns for identifying different types of content
        self.course_patterns = [
            r'course\s+(?:on|about|in)\s+([^.!?]+)',
            r'learn\s+([^.!?]+)\s+(?:course|training|program)',
            r'certification\s+(?:in|for)\s+([^.!?]+)',
            r'masterclass\s+(?:on|in)\s+([^.!?]+)',
            r'workshop\s+(?:on|about)\s+([^.!?]+)',
        ]
        
        self.marketing_fluff_patterns = [
            r'like\s+and\s+share',
            r'follow\s+(?:me|us)\s+for\s+more',
            r'don\'t\s+forget\s+to\s+(?:like|share|follow)',
            r'what\s+do\s+you\s+think\?',
            r'let\s+me\s+know\s+in\s+the\s+comments',
            r'tag\s+someone\s+who',
            r'double\s+tap\s+if',
            r'swipe\s+left\s+for\s+more',
            r'link\s+in\s+(?:bio|comments)',
            r'dm\s+me\s+for',
        ]
        
        self.knowledge_indicators = [
            r'here\'s\s+(?:how|why|what)',
            r'key\s+(?:insights?|takeaways?|learnings?)',
            r'important\s+to\s+(?:know|understand|remember)',
            r'best\s+practices?\s+(?:for|in)',
            r'tips?\s+(?:for|to)',
            r'strategies?\s+(?:for|to)',
            r'framework\s+(?:for|to)',
            r'methodology\s+(?:for|to)',
            r'approach\s+(?:to|for)',
        ]
    
    def extract_knowledge_content(self, post_content: PostContent) -> Dict[str, str]:
        """Extract knowledge-focused content from a LinkedIn post."""
        try:
            # Clean and process the main text
            cleaned_text = self._clean_post_text(post_content.body_text)
            
            # Separate knowledge content from marketing fluff
            knowledge_text = self._filter_knowledge_content(cleaned_text)
            
            # Extract course references
            course_references = self._extract_course_references(cleaned_text)
            
            # Process images for knowledge content
            image_insights = self._extract_image_insights(post_content.images)
            
            return {
                'knowledge_content': knowledge_text,
                'course_references': course_references,
                'image_insights': image_insights,
                'original_length': len(post_content.body_text),
                'processed_length': len(knowledge_text)
            }
            
        except Exception as e:
            raise ProcessingError(f"Failed to extract knowledge content: {e}", stage="content_extraction")
    
    def _clean_post_text(self, text: str) -> str:
        """Clean and normalize post text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove LinkedIn-specific formatting
        text = re.sub(r'#\w+', '', text)  # Remove hashtags
        text = re.sub(r'@\w+', '', text)  # Remove mentions
        
        # Remove URLs (they'll be preserved in source_link)
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Clean up punctuation and spacing
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _filter_knowledge_content(self, text: str) -> str:
        """Filter out marketing fluff and retain knowledge content."""
        if not text:
            return ""
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        knowledge_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Skip sentences that are clearly marketing fluff
            if self._is_marketing_fluff(sentence):
                logger.debug(f"Filtered marketing fluff: {sentence[:50]}...")
                continue
            
            # Prioritize sentences with knowledge indicators
            if self._has_knowledge_indicators(sentence) or len(sentence) > 20:
                knowledge_sentences.append(sentence)
        
        # Rejoin sentences
        knowledge_text = '. '.join(knowledge_sentences)
        
        # Final cleanup
        knowledge_text = re.sub(r'\s+', ' ', knowledge_text).strip()
        
        return knowledge_text
    
    def _is_marketing_fluff(self, sentence: str) -> bool:
        """Check if a sentence is marketing fluff."""
        sentence_lower = sentence.lower()
        
        # Check against marketing fluff patterns
        for pattern in self.marketing_fluff_patterns:
            if re.search(pattern, sentence_lower):
                return True
        
        # Check for very short sentences (likely CTAs)
        if len(sentence.split()) < 4:
            return True
        
        # Check for excessive punctuation (!!!, ???)
        if re.search(r'[!?]{2,}', sentence):
            return True
        
        return False
    
    def _has_knowledge_indicators(self, sentence: str) -> bool:
        """Check if a sentence contains knowledge indicators."""
        sentence_lower = sentence.lower()
        
        for pattern in self.knowledge_indicators:
            if re.search(pattern, sentence_lower):
                return True
        
        return False
    
    def _extract_course_references(self, text: str) -> str:
        """Extract course and learning material references."""
        if not text:
            return ""
        
        course_refs = []
        text_lower = text.lower()
        
        for pattern in self.course_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                course_ref = match.group(1).strip()
                if course_ref and len(course_ref) > 3:
                    course_refs.append(course_ref.title())
        
        # Remove duplicates and return as comma-separated string
        unique_refs = list(set(course_refs))
        return ', '.join(unique_refs) if unique_refs else ""
    
    def _extract_image_insights(self, images: List[ImageData]) -> str:
        """Extract insights from image alt text and descriptions."""
        if not images:
            return ""
        
        insights = []
        
        for i, image in enumerate(images, 1):
            image_insight = f"Image {i}: "
            
            # Use alt text if available and meaningful
            if image.alt_text and len(image.alt_text) > 10:
                alt_cleaned = self._clean_image_alt_text(image.alt_text)
                if alt_cleaned:
                    image_insight += alt_cleaned
            else:
                # Fallback to generic description
                image_insight += "Visual content (infographic/chart/diagram)"
            
            insights.append(image_insight)
        
        return '; '.join(insights)
    
    def _clean_image_alt_text(self, alt_text: str) -> str:
        """Clean and process image alt text."""
        if not alt_text:
            return ""
        
        # Remove common LinkedIn image alt text patterns
        alt_text = re.sub(r'No alternative text description for this image', '', alt_text, flags=re.IGNORECASE)
        alt_text = re.sub(r'Image may contain:', '', alt_text, flags=re.IGNORECASE)
        
        # Clean up
        alt_text = re.sub(r'\s+', ' ', alt_text).strip()
        
        # Only return if it's meaningful (more than just "image" or similar)
        if len(alt_text) > 10 and not re.match(r'^(image|photo|picture)s?$', alt_text.lower()):
            return alt_text
        
        return ""
    
    def categorize_content_topic(self, content: str) -> str:
        """Categorize content into topic areas (basic rule-based approach)."""
        if not content:
            return "Other"
        
        content_lower = content.lower()
        
        # Define topic keywords
        topic_keywords = {
            'AI & Machine Learning': [
                'artificial intelligence', 'machine learning', 'ai', 'ml', 'deep learning',
                'neural network', 'algorithm', 'data science', 'automation', 'chatbot',
                'natural language', 'computer vision', 'predictive analytics'
            ],
            'SaaS & Business': [
                'saas', 'software as a service', 'business model', 'startup', 'revenue',
                'subscription', 'customer acquisition', 'retention', 'churn', 'metrics',
                'kpi', 'growth hacking', 'product management'
            ],
            'Marketing & Sales': [
                'marketing', 'sales', 'lead generation', 'conversion', 'funnel',
                'customer journey', 'branding', 'content marketing', 'seo', 'sem',
                'social media', 'email marketing', 'crm', 'pipeline'
            ],
            'Leadership & Management': [
                'leadership', 'management', 'team building', 'culture', 'hiring',
                'performance', 'feedback', 'coaching', 'mentoring', 'strategy',
                'decision making', 'communication', 'delegation'
            ],
            'Technology Trends': [
                'technology', 'innovation', 'digital transformation', 'cloud computing',
                'cybersecurity', 'blockchain', 'cryptocurrency', 'iot', 'api',
                'microservices', 'devops', 'agile', 'scrum'
            ],
            'Course Content': [
                'course', 'training', 'certification', 'learning', 'education',
                'workshop', 'masterclass', 'tutorial', 'lesson', 'curriculum'
            ]
        }
        
        # Score each topic based on keyword matches
        topic_scores = {}
        for topic, keywords in topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                topic_scores[topic] = score
        
        # Return the topic with the highest score
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        
        return "Other"
    
    def extract_key_insights(self, content: str, max_insights: int = 5) -> List[str]:
        """Extract key insights from content."""
        if not content:
            return []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        insights = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:
                continue
            
            # Prioritize sentences with insight indicators
            insight_indicators = [
                'key', 'important', 'crucial', 'essential', 'critical',
                'remember', 'note', 'tip', 'strategy', 'approach',
                'best practice', 'lesson', 'insight', 'takeaway'
            ]
            
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in insight_indicators):
                insights.append(sentence)
            elif len(sentence) > 50 and not self._is_marketing_fluff(sentence):
                # Include longer, substantial sentences
                insights.append(sentence)
        
        # Return top insights (by length and relevance)
        insights.sort(key=len, reverse=True)
        return insights[:max_insights]
    
    def generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate a summary of the content."""
        if not content:
            return ""
        
        # Get key insights
        insights = self.extract_key_insights(content, max_insights=3)
        
        if insights:
            summary = '. '.join(insights)
            if len(summary) <= max_length:
                return summary
            
            # Truncate if too long
            return summary[:max_length-3] + "..."
        
        # Fallback: use first part of content
        if len(content) <= max_length:
            return content
        
        return content[:max_length-3] + "..."
    
    def validate_extracted_content(self, extracted_content: Dict[str, str]) -> bool:
        """Validate that extracted content meets quality standards."""
        knowledge_content = extracted_content.get('knowledge_content', '')
        
        # Check minimum content length
        if len(knowledge_content) < 50:
            logger.warning("Extracted content too short")
            return False
        
        # Check that it's not mostly marketing fluff
        sentences = re.split(r'[.!?]+', knowledge_content)
        fluff_count = sum(1 for sentence in sentences if self._is_marketing_fluff(sentence))
        
        if len(sentences) > 0 and fluff_count / len(sentences) > 0.5:
            logger.warning("Extracted content contains too much marketing fluff")
            return False
        
        return True