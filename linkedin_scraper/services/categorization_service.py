"""Content categorization service with AI and rule-based classification."""

import re
from typing import Dict, List, Tuple, Optional
from collections import Counter
import asyncio

from ..models.knowledge_item import Category
from ..models.exceptions import ProcessingError
from ..utils.config import Config
from ..utils.logger import get_logger
from .gemini_client import GeminiClient

logger = get_logger(__name__)


class CategorizationService:
    """Service for categorizing content using AI and rule-based approaches."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the categorization service."""
        self.config = config or Config.from_env()
        self.gemini_client = GeminiClient(config)
        
        # Enhanced keyword mappings for each category
        self.category_keywords = {
            Category.AI_MACHINE_LEARNING: {
                'primary': [
                    'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
                    'ai', 'ml', 'nlp', 'computer vision', 'predictive analytics', 'automation',
                    'chatbot', 'algorithm', 'data science', 'big data', 'analytics'
                ],
                'secondary': [
                    'intelligent', 'automated', 'prediction', 'model', 'training data',
                    'supervised learning', 'unsupervised learning', 'reinforcement learning',
                    'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy'
                ]
            },
            Category.SAAS_BUSINESS: {
                'primary': [
                    'saas', 'software as a service', 'subscription', 'recurring revenue',
                    'business model', 'startup', 'scale', 'growth hacking', 'product management',
                    'customer acquisition', 'retention', 'churn', 'lifetime value'
                ],
                'secondary': [
                    'b2b', 'b2c', 'enterprise', 'freemium', 'pricing strategy',
                    'market fit', 'user onboarding', 'feature adoption', 'metrics',
                    'kpi', 'dashboard', 'analytics', 'conversion funnel'
                ]
            },
            Category.MARKETING_SALES: {
                'primary': [
                    'marketing', 'sales', 'lead generation', 'conversion', 'funnel',
                    'customer journey', 'branding', 'content marketing', 'seo', 'sem',
                    'social media marketing', 'email marketing', 'crm', 'pipeline'
                ],
                'secondary': [
                    'campaign', 'roi', 'ctr', 'cpc', 'cpm', 'attribution', 'segmentation',
                    'personalization', 'a/b testing', 'landing page', 'call to action',
                    'lead scoring', 'nurturing', 'qualification', 'closing'
                ]
            },
            Category.LEADERSHIP_MANAGEMENT: {
                'primary': [
                    'leadership', 'management', 'team building', 'culture', 'hiring',
                    'performance management', 'feedback', 'coaching', 'mentoring',
                    'strategy', 'decision making', 'communication', 'delegation'
                ],
                'secondary': [
                    'employee engagement', 'motivation', 'productivity', 'collaboration',
                    'conflict resolution', 'change management', 'organizational',
                    'remote work', 'team dynamics', 'goal setting', 'accountability'
                ]
            },
            Category.TECHNOLOGY_TRENDS: {
                'primary': [
                    'technology', 'innovation', 'digital transformation', 'cloud computing',
                    'cybersecurity', 'blockchain', 'cryptocurrency', 'iot', 'api',
                    'microservices', 'devops', 'agile', 'scrum', 'containerization'
                ],
                'secondary': [
                    'emerging tech', 'future trends', 'disruption', 'scalability',
                    'infrastructure', 'architecture', 'integration', 'deployment',
                    'monitoring', 'security', 'compliance', 'governance'
                ]
            },
            Category.COURSE_CONTENT: {
                'primary': [
                    'course', 'training', 'certification', 'learning', 'education',
                    'workshop', 'masterclass', 'tutorial', 'lesson', 'curriculum',
                    'bootcamp', 'program', 'academy', 'university', 'degree'
                ],
                'secondary': [
                    'skill development', 'professional development', 'upskilling',
                    'reskilling', 'online learning', 'e-learning', 'mooc',
                    'instructor', 'student', 'assessment', 'certificate', 'diploma'
                ]
            }
        }
        
        # Confidence thresholds for categorization
        self.confidence_thresholds = {
            'high': 0.7,
            'medium': 0.4,
            'low': 0.2
        }
        
        logger.info("Categorization service initialized")
    
    async def categorize_content(
        self,
        content: str,
        use_ai: bool = True,
        fallback_to_rules: bool = True
    ) -> Tuple[Category, float]:
        """Categorize content and return category with confidence score."""
        try:
            if use_ai:
                try:
                    # Try AI-based categorization first
                    ai_category, ai_confidence = await self._categorize_with_ai(content)
                    
                    if ai_confidence >= self.confidence_thresholds['medium']:
                        logger.debug(f"AI categorization successful: {ai_category.value} (confidence: {ai_confidence:.2f})")
                        return ai_category, ai_confidence
                    
                    logger.debug(f"AI confidence too low ({ai_confidence:.2f}), trying rule-based approach")
                    
                except Exception as e:
                    logger.warning(f"AI categorization failed: {e}")
            
            if fallback_to_rules:
                # Fallback to rule-based categorization
                rule_category, rule_confidence = self._categorize_with_rules(content)
                logger.debug(f"Rule-based categorization: {rule_category.value} (confidence: {rule_confidence:.2f})")
                return rule_category, rule_confidence
            
            # Default fallback
            return Category.OTHER, 0.1
            
        except Exception as e:
            logger.error(f"Content categorization failed: {e}")
            raise ProcessingError(f"Categorization failed: {e}", stage="categorization")
    
    async def _categorize_with_ai(self, content: str) -> Tuple[Category, float]:
        """Categorize content using Gemini AI."""
        try:
            # Create categorization prompt
            prompt = self._create_categorization_prompt(content)
            
            # Get AI response
            response = await self.gemini_client.generate_content(prompt)
            
            # Parse response
            category, confidence = self._parse_ai_categorization_response(response)
            
            return category, confidence
            
        except Exception as e:
            logger.error(f"AI categorization error: {e}")
            raise
    
    def _create_categorization_prompt(self, content: str) -> str:
        """Create a prompt for AI categorization."""
        categories_list = [cat.value for cat in Category if cat != Category.OTHER]
        
        prompt = f"""
Analyze the following content and categorize it into one of these categories:

Categories:
{chr(10).join(f"- {cat}" for cat in categories_list)}
- Other

Content to analyze:
{content[:1000]}  # Limit content length for API efficiency

Instructions:
1. Choose the MOST RELEVANT category based on the main topic and focus of the content
2. Provide a confidence score from 0.0 to 1.0
3. Consider the primary subject matter, not just keywords

Response format:
CATEGORY: [category name]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation]
"""
        return prompt
    
    def _parse_ai_categorization_response(self, response: str) -> Tuple[Category, float]:
        """Parse AI categorization response."""
        try:
            lines = response.strip().split('\n')
            category_name = None
            confidence = 0.5
            
            for line in lines:
                line = line.strip()
                if line.startswith('CATEGORY:'):
                    category_name = line.replace('CATEGORY:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    confidence_str = line.replace('CONFIDENCE:', '').strip()
                    try:
                        confidence = float(confidence_str)
                    except ValueError:
                        confidence = 0.5
            
            # Map category name to enum
            if category_name:
                for category in Category:
                    if category.value.lower() == category_name.lower():
                        return category, confidence
                
                # Try partial matching
                for category in Category:
                    if category_name.lower() in category.value.lower() or category.value.lower() in category_name.lower():
                        return category, confidence * 0.8  # Reduce confidence for partial match
            
            # Default to OTHER if no match
            return Category.OTHER, 0.3
            
        except Exception as e:
            logger.error(f"Failed to parse AI categorization response: {e}")
            return Category.OTHER, 0.2
    
    def _categorize_with_rules(self, content: str) -> Tuple[Category, float]:
        """Categorize content using rule-based keyword matching."""
        if not content:
            return Category.OTHER, 0.1
        
        content_lower = content.lower()
        category_scores = {}
        
        # Calculate scores for each category
        for category, keywords in self.category_keywords.items():
            score = 0
            
            # Primary keywords (higher weight)
            for keyword in keywords['primary']:
                if keyword in content_lower:
                    score += 2
            
            # Secondary keywords (lower weight)
            for keyword in keywords['secondary']:
                if keyword in content_lower:
                    score += 1
            
            # Normalize score by content length and keyword count
            total_keywords = len(keywords['primary']) + len(keywords['secondary'])
            normalized_score = score / (total_keywords * 0.1 + len(content_lower.split()) * 0.01)
            
            if normalized_score > 0:
                category_scores[category] = normalized_score
        
        # Find the best category
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_category]
            
            # Convert score to confidence (0.0 to 1.0)
            confidence = min(best_score / 10.0, 1.0)  # Adjust scaling as needed
            
            # Apply minimum confidence threshold
            if confidence < self.confidence_thresholds['low']:
                return Category.OTHER, confidence
            
            return best_category, confidence
        
        return Category.OTHER, 0.1
    
    def extract_course_references(self, content: str) -> List[str]:
        """Extract course and educational content references."""
        if not content:
            return []
        
        course_patterns = [
            # Direct course mentions
            r'(?:course|training|program|certification|masterclass|workshop|bootcamp)\s+(?:on|about|in|for)\s+([^.!?]{3,50})',
            r'([^.!?]{3,50})\s+(?:course|training|program|certification|masterclass|workshop|bootcamp)',
            
            # Learning platforms
            r'(?:coursera|udemy|edx|linkedin learning|pluralsight|skillshare|udacity)\s+([^.!?]{3,50})',
            
            # Educational institutions
            r'(?:university|college|academy|institute)\s+(?:of|for)\s+([^.!?]{3,50})',
            
            # Degree programs
            r'(?:bachelor|master|phd|doctorate)\s+(?:in|of)\s+([^.!?]{3,50})',
            
            # Professional certifications
            r'(?:certified|certification)\s+(?:in|for)\s+([^.!?]{3,50})',
            r'([^.!?]{3,50})\s+(?:certified|certification)',
        ]
        
        courses = []
        content_lower = content.lower()
        
        for pattern in course_patterns:
            matches = re.finditer(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                course = match.group(1).strip()
                
                # Clean and validate course name
                course = re.sub(r'[^\w\s&-]', '', course)  # Remove special chars except &, -
                course = re.sub(r'\s+', ' ', course).strip()
                
                # Filter out common false positives
                if (len(course) >= 3 and len(course) <= 100 and
                    not re.match(r'^\d+$', course) and  # Not just numbers
                    course not in ['the', 'and', 'for', 'with', 'this', 'that', 'how', 'what', 'why']):
                    courses.append(course.title())
        
        # Remove duplicates and return
        return list(set(courses))
    
    def generate_topic_summary(self, content: str, category: Category) -> str:
        """Generate a topic-specific summary based on the category."""
        if not content:
            return ""
        
        # Category-specific extraction patterns
        summary_patterns = {
            Category.AI_MACHINE_LEARNING: [
                r'(?:ai|artificial intelligence|machine learning|ml)\s+(?:can|will|helps?|enables?)\s+([^.!?]+)',
                r'(?:algorithm|model|neural network)\s+(?:achieves?|improves?|reduces?)\s+([^.!?]+)',
                r'(?:predictive|analytics|automation)\s+(?:increases?|decreases?|optimizes?)\s+([^.!?]+)'
            ],
            Category.SAAS_BUSINESS: [
                r'(?:saas|subscription|revenue)\s+(?:grows?|increases?|scales?)\s+([^.!?]+)',
                r'(?:customer|user)\s+(?:acquisition|retention|engagement)\s+([^.!?]+)',
                r'(?:business model|strategy)\s+(?:focuses?|emphasizes?|prioritizes?)\s+([^.!?]+)'
            ],
            Category.MARKETING_SALES: [
                r'(?:marketing|sales|campaign)\s+(?:generates?|converts?|increases?)\s+([^.!?]+)',
                r'(?:lead|conversion|roi)\s+(?:improves?|optimizes?|maximizes?)\s+([^.!?]+)',
                r'(?:customer journey|funnel)\s+(?:includes?|involves?|requires?)\s+([^.!?]+)'
            ],
            Category.LEADERSHIP_MANAGEMENT: [
                r'(?:leader|manager|team)\s+(?:should|must|needs? to)\s+([^.!?]+)',
                r'(?:leadership|management)\s+(?:involves?|requires?|focuses? on)\s+([^.!?]+)',
                r'(?:culture|performance)\s+(?:improves?|benefits? from|requires?)\s+([^.!?]+)'
            ],
            Category.TECHNOLOGY_TRENDS: [
                r'(?:technology|innovation|digital)\s+(?:transforms?|disrupts?|enables?)\s+([^.!?]+)',
                r'(?:cloud|api|microservices?)\s+(?:provides?|offers?|supports?)\s+([^.!?]+)',
                r'(?:future|trend|emerging)\s+(?:technology|innovation)\s+([^.!?]+)'
            ],
            Category.COURSE_CONTENT: [
                r'(?:course|training|learning)\s+(?:covers?|teaches?|includes?)\s+([^.!?]+)',
                r'(?:students?|learners?)\s+(?:will learn|gain|develop)\s+([^.!?]+)',
                r'(?:curriculum|program)\s+(?:focuses? on|emphasizes?|includes?)\s+([^.!?]+)'
            ]
        }
        
        # Extract relevant information based on category
        patterns = summary_patterns.get(category, [])
        insights = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                insight = match.group(1).strip()
                if len(insight) > 10 and len(insight) < 200:
                    insights.append(insight)
        
        # If no specific patterns match, extract general insights
        if not insights:
            sentences = re.split(r'[.!?]+', content)
            for sentence in sentences[:3]:  # Take first 3 sentences
                sentence = sentence.strip()
                if len(sentence) > 20:
                    insights.append(sentence)
        
        # Create summary
        if insights:
            summary = '. '.join(insights[:2])  # Limit to 2 insights
            return summary[:300] + '...' if len(summary) > 300 else summary
        
        return content[:200] + '...' if len(content) > 200 else content
    
    async def batch_categorize(
        self,
        contents: List[str],
        use_ai: bool = True
    ) -> List[Tuple[Category, float]]:
        """Categorize multiple contents in batch."""
        results = []
        
        logger.info(f"Starting batch categorization of {len(contents)} items")
        
        for i, content in enumerate(contents):
            try:
                category, confidence = await self.categorize_content(content, use_ai=use_ai)
                results.append((category, confidence))
                
                # Add small delay between AI requests
                if use_ai and i < len(contents) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Failed to categorize content {i+1}: {e}")
                results.append((Category.OTHER, 0.1))
        
        logger.info(f"Batch categorization completed: {len(results)} items processed")
        return results
    
    def get_category_statistics(self, categories: List[Category]) -> Dict[str, any]:
        """Get statistics about category distribution."""
        if not categories:
            return {}
        
        category_counts = Counter(categories)
        total = len(categories)
        
        stats = {
            'total_items': total,
            'category_distribution': {},
            'most_common_category': None,
            'diversity_score': 0.0
        }
        
        # Calculate distribution
        for category, count in category_counts.items():
            stats['category_distribution'][category.value] = {
                'count': count,
                'percentage': (count / total) * 100
            }
        
        # Most common category
        if category_counts:
            stats['most_common_category'] = category_counts.most_common(1)[0][0].value
        
        # Diversity score (higher = more diverse)
        unique_categories = len(category_counts)
        max_possible_categories = len(Category)
        stats['diversity_score'] = unique_categories / max_possible_categories
        
        return stats
    
    def suggest_category_improvements(self, content: str, current_category: Category, confidence: float) -> List[str]:
        """Suggest improvements for low-confidence categorizations."""
        suggestions = []
        
        if confidence < self.confidence_thresholds['medium']:
            suggestions.append("Consider adding more specific keywords related to the main topic")
            suggestions.append("Ensure the content focuses on a single primary subject")
            
            if confidence < self.confidence_thresholds['low']:
                suggestions.append("The content may be too general or contain mixed topics")
                suggestions.append("Consider splitting into multiple focused pieces")
        
        # Category-specific suggestions
        if current_category == Category.OTHER:
            suggestions.append("Try to identify the primary domain or industry focus")
            suggestions.append("Add more context about the specific field or application")
        
        return suggestions