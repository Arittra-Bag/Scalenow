"""
Content sanitization service for the LinkedIn Knowledge Management System.
Integrates PII detection and sanitization into the content processing pipeline.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

from ..utils.pii_detector import (
    PIIDetector, PIISanitizer, PIIAnalyzer, PIIMatch, PIIType,
    detect_and_sanitize_pii, is_text_safe
)
from ..utils.privacy_logger import get_privacy_logger
from ..utils.config import Config
from ..models.knowledge_item import KnowledgeItem


@dataclass
class SanitizationResult:
    """Result of content sanitization process."""
    original_content: str
    sanitized_content: str
    pii_detected: bool
    pii_matches: List[PIIMatch]
    replacements_made: Dict[str, Any]
    risk_level: str
    sanitization_strategy: str
    processing_time: float
    recommendations: List[str]


class ContentSanitizer:
    """Service for sanitizing content and removing PII before storage."""
    
    def __init__(self, config: Config):
        self.config = config
        self.detector = PIIDetector()
        self.sanitizer = PIISanitizer(preserve_format=True)
        self.analyzer = PIIAnalyzer()
        self.logger = get_privacy_logger(__name__, config)
        
        # Sanitization settings
        self.min_confidence_threshold = 0.6
        self.default_strategy = "mask"  # mask, hash, placeholder, remove
        
        # Statistics tracking
        self.stats = {
            "total_processed": 0,
            "pii_detected_count": 0,
            "sanitizations_performed": 0,
            "high_risk_content": 0
        }
    
    def sanitize_knowledge_item(self, knowledge_item: KnowledgeItem) -> Tuple[KnowledgeItem, SanitizationResult]:
        """Sanitize a complete knowledge item."""
        start_time = datetime.now()
        
        # Combine all text content for analysis
        combined_content = self._extract_text_content(knowledge_item)
        
        # Detect PII
        pii_matches = self.detector.detect_pii(combined_content, context="knowledge_item")
        
        # Analyze risk
        analysis = self.analyzer.analyze_pii_matches(pii_matches)
        
        # Determine if sanitization is needed
        needs_sanitization = self._should_sanitize(pii_matches, analysis)
        
        sanitized_item = knowledge_item
        replacements = {}
        
        if needs_sanitization:
            sanitized_item, replacements = self._sanitize_item_content(knowledge_item, pii_matches)
            self.stats["sanitizations_performed"] += 1
        
        # Update statistics
        self.stats["total_processed"] += 1
        if pii_matches:
            self.stats["pii_detected_count"] += 1
        if analysis["risk_level"] == "high":
            self.stats["high_risk_content"] += 1
        
        # Create result
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = SanitizationResult(
            original_content=combined_content,
            sanitized_content=self._extract_text_content(sanitized_item),
            pii_detected=len(pii_matches) > 0,
            pii_matches=pii_matches,
            replacements_made=replacements,
            risk_level=analysis["risk_level"],
            sanitization_strategy=self.default_strategy,
            processing_time=processing_time,
            recommendations=analysis["recommendations"]
        )
        
        # Log sanitization event
        self._log_sanitization_event(result)
        
        return sanitized_item, result
    
    def sanitize_text_content(self, text: str, context: str = "") -> Tuple[str, SanitizationResult]:
        """Sanitize arbitrary text content."""
        start_time = datetime.now()
        
        # Detect PII
        pii_matches = self.detector.detect_pii(text, context=context)
        
        # Analyze risk
        analysis = self.analyzer.analyze_pii_matches(pii_matches)
        
        # Sanitize if needed
        sanitized_text = text
        replacements = {}
        
        if self._should_sanitize(pii_matches, analysis):
            high_confidence_matches = [m for m in pii_matches if m.confidence >= self.min_confidence_threshold]
            sanitized_text, replacements = self.sanitizer.sanitize_text(
                text, high_confidence_matches, self.default_strategy
            )
        
        # Create result
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = SanitizationResult(
            original_content=text,
            sanitized_content=sanitized_text,
            pii_detected=len(pii_matches) > 0,
            pii_matches=pii_matches,
            replacements_made=replacements,
            risk_level=analysis["risk_level"],
            sanitization_strategy=self.default_strategy,
            processing_time=processing_time,
            recommendations=analysis["recommendations"]
        )
        
        return sanitized_text, result
    
    def validate_content_safety(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate if content is safe for storage/processing."""
        is_safe, safety_info = is_text_safe(text, max_pii_matches=0)
        
        # Add additional safety checks
        safety_info["content_length"] = len(text)
        safety_info["validation_timestamp"] = datetime.now().isoformat()
        
        # Check for specific high-risk PII types
        high_risk_types = [PIIType.SSN, PIIType.CREDIT_CARD]
        pii_matches = self.detector.detect_pii(text)
        
        has_high_risk_pii = any(
            match.pii_type in high_risk_types and match.confidence >= 0.7
            for match in pii_matches
        )
        
        if has_high_risk_pii:
            is_safe = False
            safety_info["high_risk_pii_detected"] = True
            safety_info["requires_immediate_sanitization"] = True
        
        return is_safe, safety_info
    
    def _extract_text_content(self, knowledge_item: KnowledgeItem) -> str:
        """Extract all text content from a knowledge item for analysis."""
        content_parts = []
        
        if knowledge_item.post_title:
            content_parts.append(knowledge_item.post_title)
        
        if knowledge_item.key_knowledge_content:
            content_parts.append(knowledge_item.key_knowledge_content)
        
        if knowledge_item.topic:
            content_parts.append(knowledge_item.topic)
        
        if knowledge_item.course_references:
            content_parts.extend(knowledge_item.course_references)
        
        return " | ".join(content_parts)
    
    def _sanitize_item_content(self, knowledge_item: KnowledgeItem, 
                             pii_matches: List[PIIMatch]) -> Tuple[KnowledgeItem, Dict]:
        """Sanitize content within a knowledge item."""
        replacements = {}
        
        # Filter matches by confidence
        high_confidence_matches = [m for m in pii_matches if m.confidence >= self.min_confidence_threshold]
        
        # Sanitize title
        if knowledge_item.post_title:
            title_matches = [m for m in high_confidence_matches 
                           if m.start_pos < len(knowledge_item.post_title)]
            if title_matches:
                sanitized_title, title_replacements = self.sanitizer.sanitize_text(
                    knowledge_item.post_title, title_matches, self.default_strategy
                )
                knowledge_item.post_title = sanitized_title
                replacements.update(title_replacements)
        
        # Sanitize main content
        if knowledge_item.key_knowledge_content:
            content_matches = [m for m in high_confidence_matches]  # All matches apply to combined content
            sanitized_content, content_replacements = self.sanitizer.sanitize_text(
                knowledge_item.key_knowledge_content, content_matches, self.default_strategy
            )
            knowledge_item.key_knowledge_content = sanitized_content
            replacements.update(content_replacements)
        
        # Sanitize topic (less likely to contain PII, but check anyway)
        if knowledge_item.topic:
            topic_matches = [m for m in high_confidence_matches 
                           if knowledge_item.topic.lower() in m.original_text.lower()]
            if topic_matches:
                sanitized_topic, topic_replacements = self.sanitizer.sanitize_text(
                    knowledge_item.topic, topic_matches, self.default_strategy
                )
                knowledge_item.topic = sanitized_topic
                replacements.update(topic_replacements)
        
        # Sanitize course references
        if knowledge_item.course_references:
            sanitized_courses = []
            for course in knowledge_item.course_references:
                course_matches = [m for m in high_confidence_matches 
                                if course.lower() in m.original_text.lower()]
                if course_matches:
                    sanitized_course, course_replacements = self.sanitizer.sanitize_text(
                        course, course_matches, self.default_strategy
                    )
                    sanitized_courses.append(sanitized_course)
                    replacements.update(course_replacements)
                else:
                    sanitized_courses.append(course)
            knowledge_item.course_references = sanitized_courses
        
        return knowledge_item, replacements
    
    def _should_sanitize(self, pii_matches: List[PIIMatch], analysis: Dict) -> bool:
        """Determine if content should be sanitized based on PII analysis."""
        if not self.config.sanitize_content:
            return False
        
        # Always sanitize high-risk PII
        high_risk_types = [PIIType.SSN, PIIType.CREDIT_CARD]
        has_high_risk = any(
            match.pii_type in high_risk_types and match.confidence >= 0.5
            for match in pii_matches
        )
        
        if has_high_risk:
            return True
        
        # Sanitize based on risk level and confidence
        if analysis["risk_level"] == "high":
            return True
        
        # Sanitize if we have high-confidence matches
        high_confidence_matches = [m for m in pii_matches if m.confidence >= self.min_confidence_threshold]
        return len(high_confidence_matches) > 0
    
    def _log_sanitization_event(self, result: SanitizationResult):
        """Log sanitization events for monitoring and compliance."""
        if result.pii_detected:
            self.logger.log_pii_detection(
                result.original_content,
                len(result.pii_matches),
                sanitized=len(result.replacements_made) > 0
            )
            
            # Log detailed sanitization info
            self.logger.info(
                f"Content sanitization completed",
                extra_data={
                    "pii_matches_found": len(result.pii_matches),
                    "replacements_made": len(result.replacements_made),
                    "risk_level": result.risk_level,
                    "strategy": result.sanitization_strategy,
                    "processing_time_ms": round(result.processing_time * 1000, 2),
                    "content_length": len(result.original_content)
                },
                sanitize=True
            )
    
    def get_sanitization_stats(self) -> Dict[str, Any]:
        """Get sanitization statistics."""
        return {
            **self.stats,
            "sanitization_rate": (
                self.stats["sanitizations_performed"] / max(self.stats["total_processed"], 1)
            ) * 100,
            "pii_detection_rate": (
                self.stats["pii_detected_count"] / max(self.stats["total_processed"], 1)
            ) * 100,
            "high_risk_rate": (
                self.stats["high_risk_content"] / max(self.stats["total_processed"], 1)
            ) * 100
        }
    
    def reset_stats(self):
        """Reset sanitization statistics."""
        self.stats = {
            "total_processed": 0,
            "pii_detected_count": 0,
            "sanitizations_performed": 0,
            "high_risk_content": 0
        }
    
    def configure_sanitization(self, strategy: str = None, min_confidence: float = None):
        """Configure sanitization parameters."""
        if strategy and strategy in ["mask", "hash", "placeholder", "remove", "consistent"]:
            self.default_strategy = strategy
        
        if min_confidence is not None and 0.0 <= min_confidence <= 1.0:
            self.min_confidence_threshold = min_confidence
    
    def export_sanitization_report(self) -> Dict[str, Any]:
        """Export a comprehensive sanitization report."""
        stats = self.get_sanitization_stats()
        
        return {
            "report_timestamp": datetime.now().isoformat(),
            "configuration": {
                "pii_detection_enabled": self.config.enable_pii_detection,
                "content_sanitization_enabled": self.config.sanitize_content,
                "min_confidence_threshold": self.min_confidence_threshold,
                "default_strategy": self.default_strategy
            },
            "statistics": stats,
            "recommendations": self._generate_recommendations(stats)
        }
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on sanitization statistics."""
        recommendations = []
        
        if stats["pii_detection_rate"] > 10:
            recommendations.append(
                "High PII detection rate detected. Consider reviewing content sources."
            )
        
        if stats["high_risk_rate"] > 5:
            recommendations.append(
                "High-risk PII detected frequently. Implement additional content filtering."
            )
        
        if stats["sanitization_rate"] < 50 and stats["pii_detection_rate"] > 5:
            recommendations.append(
                "Consider lowering confidence threshold for more aggressive sanitization."
            )
        
        if stats["total_processed"] > 100 and stats["sanitization_rate"] == 0:
            recommendations.append(
                "No sanitizations performed. Verify PII detection is working correctly."
            )
        
        return recommendations


# Convenience functions for integration
def sanitize_knowledge_item(knowledge_item: KnowledgeItem, config: Config) -> Tuple[KnowledgeItem, SanitizationResult]:
    """Convenience function to sanitize a knowledge item."""
    sanitizer = ContentSanitizer(config)
    return sanitizer.sanitize_knowledge_item(knowledge_item)


def validate_content_for_storage(text: str, config: Config) -> Tuple[bool, Dict[str, Any]]:
    """Convenience function to validate content safety before storage."""
    sanitizer = ContentSanitizer(config)
    return sanitizer.validate_content_safety(text)


def sanitize_text_for_logging(text: str, config: Config) -> str:
    """Convenience function to sanitize text for safe logging."""
    if not config.enable_pii_detection:
        return text
    
    sanitizer = ContentSanitizer(config)
    sanitized_text, _ = sanitizer.sanitize_text_content(text, context="logging")
    return sanitized_text