"""
PII (Personally Identifiable Information) Detection and Sanitization System.
"""

import re
import hashlib
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum


class PIIType(Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    URL = "url"
    PERSON_NAME = "person_name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    LINKEDIN_PROFILE = "linkedin_profile"
    CUSTOM = "custom"


@dataclass
class PIIMatch:
    """Represents a detected PII match."""
    pii_type: PIIType
    original_text: str
    start_pos: int
    end_pos: int
    confidence: float
    context: str = ""
    
    def __str__(self) -> str:
        return f"{self.pii_type.value}: {self.original_text} (confidence: {self.confidence:.2f})"


class PIIDetector:
    """Advanced PII detection system with configurable patterns and rules."""
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.whitelist_domains = {
            'example.com', 'test.com', 'sample.com', 'demo.com',
            'placeholder.com', 'yourcompany.com', 'company.com'
        }
        self.common_names = self._load_common_names()
    
    def _initialize_patterns(self) -> Dict[PIIType, List[Dict]]:
        """Initialize regex patterns for different PII types."""
        return {
            PIIType.EMAIL: [
                {
                    'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    'confidence': 0.9,
                    'description': 'Standard email format'
                }
            ],
            
            PIIType.PHONE: [
                {
                    'pattern': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                    'confidence': 0.8,
                    'description': 'US phone number'
                },
                {
                    'pattern': r'\b\+?[1-9]\d{1,14}\b',
                    'confidence': 0.6,
                    'description': 'International phone number'
                }
            ],
            
            PIIType.SSN: [
                {
                    'pattern': r'\b\d{3}-\d{2}-\d{4}\b',
                    'confidence': 0.95,
                    'description': 'US SSN format (XXX-XX-XXXX)'
                },
                {
                    'pattern': r'\b\d{9}\b',
                    'confidence': 0.3,
                    'description': 'Possible SSN (9 digits)'
                }
            ],
            
            PIIType.CREDIT_CARD: [
                {
                    'pattern': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
                    'confidence': 0.9,
                    'description': 'Credit card number'
                }
            ],
            
            PIIType.IP_ADDRESS: [
                {
                    'pattern': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                    'confidence': 0.7,
                    'description': 'IPv4 address'
                },
                {
                    'pattern': r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
                    'confidence': 0.8,
                    'description': 'IPv6 address'
                }
            ],
            
            PIIType.LINKEDIN_PROFILE: [
                {
                    'pattern': r'linkedin\.com/in/[a-zA-Z0-9-]+',
                    'confidence': 0.95,
                    'description': 'LinkedIn profile URL'
                }
            ],
            
            PIIType.DATE_OF_BIRTH: [
                {
                    'pattern': r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',
                    'confidence': 0.6,
                    'description': 'Date in MM/DD/YYYY format'
                },
                {
                    'pattern': r'\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b',
                    'confidence': 0.6,
                    'description': 'Date in YYYY/MM/DD format'
                }
            ],
            
            PIIType.PERSON_NAME: [
                {
                    'pattern': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
                    'confidence': 0.4,
                    'description': 'Possible person name (First Last)'
                }
            ]
        }
    
    def _load_common_names(self) -> Set[str]:
        """Load common first and last names for better person name detection."""
        # This would typically load from a file or database
        # For now, using a small sample
        return {
            'john', 'jane', 'michael', 'sarah', 'david', 'lisa', 'robert', 'mary',
            'james', 'patricia', 'william', 'jennifer', 'richard', 'elizabeth',
            'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller',
            'davis', 'rodriguez', 'martinez', 'hernandez', 'lopez', 'gonzalez'
        }
    
    def detect_pii(self, text: str, context: str = "") -> List[PIIMatch]:
        """Detect PII in the given text."""
        matches = []
        
        for pii_type, pattern_configs in self.patterns.items():
            for config in pattern_configs:
                pattern = config['pattern']
                base_confidence = config['confidence']
                
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    original_text = match.group()
                    
                    # Apply additional validation and confidence adjustment
                    confidence = self._calculate_confidence(
                        pii_type, original_text, base_confidence, text, match.start()
                    )
                    
                    if confidence > 0.1:  # Minimum confidence threshold
                        pii_match = PIIMatch(
                            pii_type=pii_type,
                            original_text=original_text,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=confidence,
                            context=context
                        )
                        matches.append(pii_match)
        
        # Remove duplicates and overlapping matches
        return self._deduplicate_matches(matches)
    
    def _calculate_confidence(self, pii_type: PIIType, text: str, base_confidence: float, 
                            full_text: str, position: int) -> float:
        """Calculate confidence score for a PII match."""
        confidence = base_confidence
        
        # Type-specific confidence adjustments
        if pii_type == PIIType.EMAIL:
            # Check if it's a placeholder email
            if any(domain in text.lower() for domain in self.whitelist_domains):
                confidence *= 0.1
            
            # Check for common placeholder patterns
            if any(placeholder in text.lower() for placeholder in ['example', 'test', 'sample']):
                confidence *= 0.1
        
        elif pii_type == PIIType.PHONE:
            # Check for obviously fake numbers
            if text in ['123-456-7890', '555-555-5555', '000-000-0000']:
                confidence *= 0.1
            
            # Check for repeated digits
            digits_only = re.sub(r'[^\d]', '', text)
            if len(set(digits_only)) <= 2:  # Too few unique digits
                confidence *= 0.3
        
        elif pii_type == PIIType.PERSON_NAME:
            # Check if it's a common name combination
            name_parts = text.lower().split()
            if len(name_parts) == 2:
                first_name, last_name = name_parts
                if first_name in self.common_names and last_name in self.common_names:
                    confidence *= 1.5  # Increase confidence for common names
                else:
                    confidence *= 0.8  # Decrease for uncommon combinations
        
        elif pii_type == PIIType.IP_ADDRESS:
            # Check for private/local IP ranges
            if text.startswith(('192.168.', '10.', '172.16.', '127.')):
                confidence *= 0.5  # Lower confidence for private IPs
        
        # Context-based adjustments
        context_window = full_text[max(0, position-50):position+len(text)+50]
        
        # Look for context clues that indicate PII
        pii_indicators = ['contact', 'email', 'phone', 'call', 'reach', 'address']
        if any(indicator in context_window.lower() for indicator in pii_indicators):
            confidence *= 1.2
        
        # Look for context clues that indicate non-PII
        non_pii_indicators = ['example', 'sample', 'demo', 'test', 'placeholder']
        if any(indicator in context_window.lower() for indicator in non_pii_indicators):
            confidence *= 0.3
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _deduplicate_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove duplicate and overlapping matches."""
        if not matches:
            return matches
        
        # Sort by position
        matches.sort(key=lambda x: (x.start_pos, x.end_pos))
        
        deduplicated = []
        for match in matches:
            # Check for overlap with existing matches
            overlaps = False
            for existing in deduplicated:
                if (match.start_pos < existing.end_pos and 
                    match.end_pos > existing.start_pos):
                    # Overlapping - keep the one with higher confidence
                    if match.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(match)
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(match)
        
        return deduplicated


class PIISanitizer:
    """PII sanitization system with multiple sanitization strategies."""
    
    def __init__(self, preserve_format: bool = True):
        self.preserve_format = preserve_format
        self.replacement_cache = {}  # For consistent replacements
    
    def sanitize_text(self, text: str, pii_matches: List[PIIMatch], 
                     strategy: str = "mask") -> Tuple[str, Dict]:
        """Sanitize text by replacing PII with safe alternatives."""
        if not pii_matches:
            return text, {}
        
        # Sort matches by position (reverse order to maintain positions)
        sorted_matches = sorted(pii_matches, key=lambda x: x.start_pos, reverse=True)
        
        sanitized_text = text
        replacements = {}
        
        for match in sorted_matches:
            if match.confidence < 0.5:  # Skip low-confidence matches
                continue
            
            replacement = self._get_replacement(match, strategy)
            
            # Replace in text
            sanitized_text = (
                sanitized_text[:match.start_pos] + 
                replacement + 
                sanitized_text[match.end_pos:]
            )
            
            # Track replacement
            replacements[match.original_text] = {
                'replacement': replacement,
                'pii_type': match.pii_type.value,
                'confidence': match.confidence,
                'strategy': strategy
            }
        
        return sanitized_text, replacements
    
    def _get_replacement(self, match: PIIMatch, strategy: str) -> str:
        """Get replacement text for a PII match."""
        if strategy == "remove":
            return ""
        
        elif strategy == "mask":
            return self._mask_pii(match)
        
        elif strategy == "hash":
            return self._hash_pii(match)
        
        elif strategy == "placeholder":
            return self._placeholder_pii(match)
        
        elif strategy == "consistent":
            return self._consistent_replacement(match)
        
        else:
            return self._mask_pii(match)  # Default to masking
    
    def _mask_pii(self, match: PIIMatch) -> str:
        """Mask PII with asterisks while preserving format."""
        text = match.original_text
        
        if match.pii_type == PIIType.EMAIL:
            # Mask email: j***@e*****.com
            parts = text.split('@')
            if len(parts) == 2:
                username = parts[0]
                domain = parts[1]
                
                masked_username = username[0] + '*' * (len(username) - 1) if len(username) > 1 else '*'
                
                domain_parts = domain.split('.')
                if len(domain_parts) >= 2:
                    masked_domain = domain_parts[0][0] + '*' * (len(domain_parts[0]) - 1)
                    masked_domain += '.' + '.'.join(domain_parts[1:])
                else:
                    masked_domain = '*' * len(domain)
                
                return f"{masked_username}@{masked_domain}"
        
        elif match.pii_type == PIIType.PHONE:
            # Mask phone: (***) ***-1234
            digits = re.sub(r'[^\d]', '', text)
            if len(digits) >= 4:
                masked = '*' * (len(digits) - 4) + digits[-4:]
                # Preserve original format
                result = text
                digit_pos = 0
                for i, char in enumerate(text):
                    if char.isdigit():
                        if digit_pos < len(masked):
                            result = result[:i] + masked[digit_pos] + result[i+1:]
                        digit_pos += 1
                return result
        
        elif match.pii_type == PIIType.PERSON_NAME:
            # Mask name: J*** S***
            parts = text.split()
            masked_parts = []
            for part in parts:
                if len(part) > 1:
                    masked_parts.append(part[0] + '*' * (len(part) - 1))
                else:
                    masked_parts.append('*')
            return ' '.join(masked_parts)
        
        # Default masking
        if len(text) <= 2:
            return '*' * len(text)
        else:
            return text[0] + '*' * (len(text) - 2) + text[-1]
    
    def _hash_pii(self, match: PIIMatch) -> str:
        """Replace PII with a hash."""
        hash_obj = hashlib.sha256(match.original_text.encode())
        hash_hex = hash_obj.hexdigest()[:8]  # Use first 8 characters
        return f"[{match.pii_type.value.upper()}_{hash_hex}]"
    
    def _placeholder_pii(self, match: PIIMatch) -> str:
        """Replace PII with descriptive placeholders."""
        placeholders = {
            PIIType.EMAIL: "[EMAIL_ADDRESS]",
            PIIType.PHONE: "[PHONE_NUMBER]",
            PIIType.SSN: "[SSN]",
            PIIType.CREDIT_CARD: "[CREDIT_CARD]",
            PIIType.IP_ADDRESS: "[IP_ADDRESS]",
            PIIType.PERSON_NAME: "[PERSON_NAME]",
            PIIType.LINKEDIN_PROFILE: "[LINKEDIN_PROFILE]",
            PIIType.DATE_OF_BIRTH: "[DATE_OF_BIRTH]"
        }
        return placeholders.get(match.pii_type, "[PII]")
    
    def _consistent_replacement(self, match: PIIMatch) -> str:
        """Provide consistent replacement for the same PII across text."""
        cache_key = f"{match.pii_type.value}:{match.original_text}"
        
        if cache_key in self.replacement_cache:
            return self.replacement_cache[cache_key]
        
        # Generate consistent replacement
        if match.pii_type == PIIType.EMAIL:
            replacement = f"user{len(self.replacement_cache) + 1}@example.com"
        elif match.pii_type == PIIType.PHONE:
            replacement = f"555-{(len(self.replacement_cache) + 1):03d}-0000"
        elif match.pii_type == PIIType.PERSON_NAME:
            replacement = f"Person {len(self.replacement_cache) + 1}"
        else:
            replacement = self._placeholder_pii(match)
        
        self.replacement_cache[cache_key] = replacement
        return replacement


class PIIAnalyzer:
    """Analyze PII detection results and provide insights."""
    
    @staticmethod
    def analyze_pii_matches(matches: List[PIIMatch]) -> Dict:
        """Analyze PII matches and provide summary statistics."""
        if not matches:
            return {
                "total_matches": 0,
                "pii_types_found": [],
                "risk_level": "low",
                "recommendations": []
            }
        
        # Count by type
        type_counts = {}
        high_confidence_matches = 0
        
        for match in matches:
            pii_type = match.pii_type.value
            type_counts[pii_type] = type_counts.get(pii_type, 0) + 1
            
            if match.confidence >= 0.8:
                high_confidence_matches += 1
        
        # Determine risk level
        risk_level = "low"
        if high_confidence_matches > 0:
            risk_level = "high"
        elif len(matches) > 3:
            risk_level = "medium"
        
        # Generate recommendations
        recommendations = []
        if PIIType.EMAIL.value in type_counts:
            recommendations.append("Consider masking or removing email addresses")
        if PIIType.PHONE.value in type_counts:
            recommendations.append("Phone numbers should be sanitized before storage")
        if PIIType.SSN.value in type_counts:
            recommendations.append("SSNs detected - immediate sanitization required")
        if PIIType.CREDIT_CARD.value in type_counts:
            recommendations.append("Credit card numbers detected - remove immediately")
        
        return {
            "total_matches": len(matches),
            "high_confidence_matches": high_confidence_matches,
            "pii_types_found": list(type_counts.keys()),
            "type_counts": type_counts,
            "risk_level": risk_level,
            "recommendations": recommendations,
            "confidence_distribution": {
                "high": len([m for m in matches if m.confidence >= 0.8]),
                "medium": len([m for m in matches if 0.5 <= m.confidence < 0.8]),
                "low": len([m for m in matches if m.confidence < 0.5])
            }
        }


# Convenience functions
def detect_and_sanitize_pii(text: str, strategy: str = "mask", 
                           min_confidence: float = 0.5) -> Tuple[str, Dict]:
    """Convenience function to detect and sanitize PII in one step."""
    detector = PIIDetector()
    sanitizer = PIISanitizer()
    
    # Detect PII
    matches = detector.detect_pii(text)
    
    # Filter by confidence
    high_confidence_matches = [m for m in matches if m.confidence >= min_confidence]
    
    # Sanitize
    sanitized_text, replacements = sanitizer.sanitize_text(text, high_confidence_matches, strategy)
    
    # Analyze
    analysis = PIIAnalyzer.analyze_pii_matches(matches)
    
    return sanitized_text, {
        "original_text": text,
        "sanitized_text": sanitized_text,
        "replacements": replacements,
        "analysis": analysis,
        "matches_found": len(matches),
        "matches_sanitized": len(high_confidence_matches)
    }


def is_text_safe(text: str, max_pii_matches: int = 0) -> Tuple[bool, Dict]:
    """Check if text is safe (contains no high-confidence PII)."""
    detector = PIIDetector()
    matches = detector.detect_pii(text)
    
    high_confidence_matches = [m for m in matches if m.confidence >= 0.8]
    analysis = PIIAnalyzer.analyze_pii_matches(matches)
    
    is_safe = len(high_confidence_matches) <= max_pii_matches
    
    return is_safe, {
        "is_safe": is_safe,
        "total_matches": len(matches),
        "high_confidence_matches": len(high_confidence_matches),
        "analysis": analysis
    }