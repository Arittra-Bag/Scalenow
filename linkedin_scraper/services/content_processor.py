"""AI-powered content processor for knowledge extraction using Gemini."""

import asyncio
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime

from ..models.post_content import PostContent
from ..models.knowledge_item import KnowledgeItem, Category
from ..models.exceptions import ProcessingError, APIError
from ..utils.config import Config
from ..utils.logger import get_logger
from ..utils.validators import URLValidator
from .gemini_client import GeminiClient

logger = get_logger(__name__)


class ContentProcessor:
    """AI-powered content processor for extracting knowledge from LinkedIn posts."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the content processor."""
        self.config = config or Config.from_env()
        self.gemini_client = GeminiClient(config)
        
        # Fallback patterns for when AI is unavailable
        self.fallback_patterns = {
            'knowledge_indicators': [
                r'key\s+(?:insights?|takeaways?|learnings?)',
                r'important\s+to\s+(?:know|understand|remember)',
                r'best\s+practices?\s+(?:for|in)',
                r'tips?\s+(?:for|to)',
                r'strategies?\s+(?:for|to)',
                r'here\'s\s+(?:how|why|what)',
                r'framework\s+(?:for|to)',
                r'methodology\s+(?:for|to)',
            ],
            'marketing_fluff': [
                r'like\s+and\s+share',
                r'follow\s+(?:me|us)\s+for\s+more',
                r'don\'t\s+forget\s+to\s+(?:like|share|follow)',
                r'what\s+do\s+you\s+think\?',
                r'let\s+me\s+know\s+in\s+the\s+comments',
                r'tag\s+someone\s+who',
                r'double\s+tap\s+if',
            ]
        }
        
        logger.info("Content processor initialized with Gemini AI")
    
    async def process_post_content(self, post_content: PostContent) -> KnowledgeItem:
        """Process a LinkedIn post and extract knowledge using AI."""
        try:
            logger.info(f"Processing post content: {post_content.url}")
            
            # Sanitize content if enabled
            if self.config.sanitize_content:
                sanitized_text = self._sanitize_content(post_content.body_text)
            else:
                sanitized_text = post_content.body_text
            
            # Extract knowledge using AI
            knowledge_data = await self._extract_knowledge_with_ai(sanitized_text)
            
            # Process images for additional insights
            image_insights = self._process_images(post_content.images)
            
            # Create knowledge item
            knowledge_item = KnowledgeItem(
                topic=knowledge_data.get('topic', 'General'),
                post_title=post_content.title,
                key_knowledge_content=knowledge_data.get('knowledge', sanitized_text),
                infographic_summary=image_insights,
                source_link=post_content.url,
                notes_applications=knowledge_data.get('summary', ''),
                category=Category.from_string(knowledge_data.get('category', 'Other')),
                course_references=self._parse_course_references(knowledge_data.get('courses', ''))
            )
            
            logger.info(f"Successfully processed post into knowledge item: {knowledge_item.id}")
            return knowledge_item
            
        except Exception as e:
            logger.error(f"Failed to process post content: {e}")
            raise ProcessingError(f"Content processing failed: {e}", stage="ai_processing")
    
    async def _extract_knowledge_with_ai(self, content: str) -> Dict[str, str]:
        """Extract knowledge using Gemini AI with fallback to rule-based processing."""
        try:
            # Create the knowledge extraction prompt
            prompt = self.gemini_client.create_prompt_template("knowledge_extraction").format(
                content=content
            )
            
            # Get AI response
            response = await self.gemini_client.generate_content(prompt)
            
            # Parse the structured response
            knowledge_data = self._parse_ai_response(response)
            
            # Validate the extracted knowledge
            if self._validate_knowledge_extraction(knowledge_data):
                logger.debug("AI knowledge extraction successful")
                return knowledge_data
            else:
                logger.warning("AI extraction validation failed, using fallback")
                return self._fallback_knowledge_extraction(content)
                
        except APIError as e:
            logger.warning(f"AI extraction failed: {e}, using fallback method")
            return self._fallback_knowledge_extraction(content)
        except Exception as e:
            logger.error(f"Unexpected error in AI extraction: {e}")
            return self._fallback_knowledge_extraction(content)
    
    def _parse_ai_response(self, response: str) -> Dict[str, str]:
        """Parse structured AI response into components."""
        knowledge_data = {
            'knowledge': '',
            'topic': 'General',
            'category': 'Other',
            'courses': '',
            'summary': ''
        }
        
        try:
            # Parse structured response format
            lines = response.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for section headers
                if line.startswith('KNOWLEDGE:'):
                    current_section = 'knowledge'
                    knowledge_data['knowledge'] = line.replace('KNOWLEDGE:', '').strip()
                elif line.startswith('TOPIC:'):
                    current_section = 'topic'
                    knowledge_data['topic'] = line.replace('TOPIC:', '').strip()
                elif line.startswith('COURSES:'):
                    current_section = 'courses'
                    knowledge_data['courses'] = line.replace('COURSES:', '').strip()
                elif line.startswith('SUMMARY:'):
                    current_section = 'summary'
                    knowledge_data['summary'] = line.replace('SUMMARY:', '').strip()
                elif current_section and not line.startswith(('KNOWLEDGE:', 'TOPIC:', 'COURSES:', 'SUMMARY:')):
                    # Continue previous section
                    knowledge_data[current_section] += ' ' + line
            
            # Map topic to category
            knowledge_data['category'] = self._map_topic_to_category(knowledge_data['topic'])
            
            # Clean up extracted content
            for key in knowledge_data:
                knowledge_data[key] = knowledge_data[key].strip()
            
            return knowledge_data
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            # Return fallback with original response as knowledge
            return {
                'knowledge': response[:500] if response else '',
                'topic': 'General',
                'category': 'Other',
                'courses': '',
                'summary': response[:200] if response else ''
            }
    
    def _map_topic_to_category(self, topic: str) -> str:
        """Map AI-detected topic to predefined categories."""
        if not topic:
            return 'Other'
        
        topic_lower = topic.lower()
        
        # Category mapping
        category_mappings = {
            'AI & Machine Learning': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 'neural', 'algorithm'],
            'SaaS & Business': ['saas', 'software', 'business', 'startup', 'revenue', 'subscription', 'growth'],
            'Marketing & Sales': ['marketing', 'sales', 'lead generation', 'conversion', 'branding', 'seo', 'social media'],
            'Leadership & Management': ['leadership', 'management', 'team', 'culture', 'hiring', 'strategy', 'communication'],
            'Technology Trends': ['technology', 'innovation', 'digital', 'cloud', 'cybersecurity', 'blockchain', 'iot'],
            'Course Content': ['course', 'training', 'certification', 'learning', 'education', 'workshop', 'tutorial']
        }
        
        for category, keywords in category_mappings.items():
            if any(keyword in topic_lower for keyword in keywords):
                return category
        
        return 'Other'
    
    def _fallback_knowledge_extraction(self, content: str) -> Dict[str, str]:
        """Fallback rule-based knowledge extraction when AI is unavailable."""
        logger.info("Using fallback rule-based knowledge extraction")
        
        # Clean content
        cleaned_content = self._clean_content_fallback(content)
        
        # Extract knowledge sentences
        knowledge_sentences = self._extract_knowledge_sentences(cleaned_content)
        
        # Detect topic
        topic = self._detect_topic_fallback(cleaned_content)
        
        # Extract course references
        courses = self._extract_courses_fallback(cleaned_content)
        
        # Generate summary
        summary = self._generate_summary_fallback(knowledge_sentences)
        
        return {
            'knowledge': ' '.join(knowledge_sentences),
            'topic': topic,
            'category': self._map_topic_to_category(topic),
            'courses': courses,
            'summary': summary
        }
    
    def _clean_content_fallback(self, content: str) -> str:
        """Clean content using rule-based approach."""
        if not content:
            return ""
        
        # Remove URLs
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        
        # Remove hashtags and mentions
        content = re.sub(r'#\w+', '', content)
        content = re.sub(r'@\w+', '', content)
        
        # Clean whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _extract_knowledge_sentences(self, content: str) -> List[str]:
        """Extract sentences that contain knowledge using patterns."""
        if not content:
            return []
        
        sentences = re.split(r'[.!?]+', content)
        knowledge_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short sentences
                continue
            
            sentence_lower = sentence.lower()
            
            # Skip marketing fluff
            is_fluff = any(re.search(pattern, sentence_lower) for pattern in self.fallback_patterns['marketing_fluff'])
            if is_fluff:
                continue
            
            # Prioritize knowledge indicators
            has_knowledge = any(re.search(pattern, sentence_lower) for pattern in self.fallback_patterns['knowledge_indicators'])
            
            if has_knowledge or len(sentence) > 50:  # Include longer sentences or those with knowledge indicators
                knowledge_sentences.append(sentence)
        
        return knowledge_sentences[:5]  # Limit to top 5 sentences
    
    def _detect_topic_fallback(self, content: str) -> str:
        """Detect topic using keyword matching."""
        if not content:
            return "General"
        
        content_lower = content.lower()
        
        topic_keywords = {
            'AI & Machine Learning': ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural network', 'algorithm'],
            'SaaS & Business': ['saas', 'software as a service', 'business model', 'startup', 'revenue', 'subscription'],
            'Marketing & Sales': ['marketing', 'sales', 'lead generation', 'conversion', 'branding', 'seo'],
            'Leadership & Management': ['leadership', 'management', 'team building', 'culture', 'strategy'],
            'Technology Trends': ['technology', 'innovation', 'digital transformation', 'cloud computing', 'cybersecurity'],
            'Course Content': ['course', 'training', 'certification', 'learning', 'education', 'workshop']
        }
        
        topic_scores = {}
        for topic, keywords in topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        
        return "General"
    
    def _extract_courses_fallback(self, content: str) -> str:
        """Extract course references using patterns."""
        if not content:
            return ""
        
        course_patterns = [
            r'course\s+(?:on|about|in)\s+([^.!?]+)',
            r'learn\s+([^.!?]+)\s+(?:course|training|program)',
            r'certification\s+(?:in|for)\s+([^.!?]+)',
            r'masterclass\s+(?:on|in)\s+([^.!?]+)',
            r'workshop\s+(?:on|about)\s+([^.!?]+)',
        ]
        
        courses = []
        content_lower = content.lower()
        
        for pattern in course_patterns:
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                course = match.group(1).strip()
                if len(course) > 3 and len(course) < 100:
                    courses.append(course.title())
        
        return ', '.join(list(set(courses))) if courses else ""
    
    def _generate_summary_fallback(self, knowledge_sentences: List[str]) -> str:
        """Generate summary from knowledge sentences."""
        if not knowledge_sentences:
            return ""
        
        # Take first 2-3 sentences or up to 200 characters
        summary_parts = []
        total_length = 0
        
        for sentence in knowledge_sentences[:3]:
            if total_length + len(sentence) > 200:
                break
            summary_parts.append(sentence)
            total_length += len(sentence)
        
        return '. '.join(summary_parts) + '.' if summary_parts else ""
    
    def _validate_knowledge_extraction(self, knowledge_data: Dict[str, str]) -> bool:
        """Validate that AI extraction produced meaningful results."""
        knowledge = knowledge_data.get('knowledge', '')
        
        # Check minimum length
        if len(knowledge) < 30:
            return False
        
        # Check that it's not just the original content repeated
        if knowledge_data.get('summary', '') == knowledge:
            return False
        
        # Check for meaningful topic
        topic = knowledge_data.get('topic', '')
        if not topic or topic.lower() in ['general', 'unknown', 'none']:
            return False
        
        return True
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content for privacy and security."""
        if not content:
            return ""
        
        if self.config.enable_pii_detection:
            # Use validator to detect and sanitize PII
            sanitized = URLValidator.sanitize_pii(content)
            
            if sanitized != content:
                logger.info("PII detected and sanitized in content")
            
            return sanitized
        
        return content
    
    def _process_images(self, images: List) -> str:
        """Process image information for knowledge extraction."""
        if not images:
            return ""
        
        image_insights = []
        
        for i, image in enumerate(images, 1):
            insight = f"Image {i}: "
            
            if hasattr(image, 'alt_text') and image.alt_text:
                # Clean alt text
                alt_cleaned = re.sub(r'[^\w\s]', ' ', image.alt_text)
                alt_cleaned = re.sub(r'\s+', ' ', alt_cleaned).strip()
                
                if len(alt_cleaned) > 10:
                    insight += alt_cleaned
                else:
                    insight += "Visual content (chart/infographic/diagram)"
            else:
                insight += "Visual content (chart/infographic/diagram)"
            
            image_insights.append(insight)
        
        return '; '.join(image_insights)
    
    def _parse_course_references(self, courses_text: str) -> List[str]:
        """Parse course references from text into a list."""
        if not courses_text or courses_text.lower() in ['none', 'n/a', '']:
            return []
        
        # Split by common separators
        courses = re.split(r'[,;]', courses_text)
        
        # Clean and filter courses
        cleaned_courses = []
        for course in courses:
            course = course.strip()
            if len(course) > 3 and len(course) < 100:
                cleaned_courses.append(course)
        
        return cleaned_courses
    
    async def batch_process_posts(self, posts: List[PostContent]) -> List[KnowledgeItem]:
        """Process multiple posts in batch with rate limiting."""
        knowledge_items = []
        
        logger.info(f"Starting batch processing of {len(posts)} posts")
        
        for i, post in enumerate(posts):
            try:
                logger.info(f"Processing post {i+1}/{len(posts)}: {post.url}")
                
                knowledge_item = await self.process_post_content(post)
                knowledge_items.append(knowledge_item)
                
                # Add delay between posts to respect rate limits
                if i < len(posts) - 1:
                    await asyncio.sleep(1.0)
                    
            except Exception as e:
                logger.error(f"Failed to process post {i+1}: {e}")
                # Continue with other posts
                continue
        
        logger.info(f"Batch processing completed: {len(knowledge_items)}/{len(posts)} successful")
        return knowledge_items
    
    async def get_processing_stats(self) -> Dict[str, any]:
        """Get processing statistics and health status."""
        stats = {
            'gemini_status': await self.gemini_client.health_check(),
            'rate_limits': self.gemini_client.get_rate_limit_status(),
            'config': {
                'sanitize_content': self.config.sanitize_content,
                'enable_pii_detection': self.config.enable_pii_detection,
                'batch_size': self.config.batch_size
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return stats