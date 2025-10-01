"""Custom exceptions for the LinkedIn Knowledge Management System."""


class LinkedInKMSError(Exception):
    """Base exception for LinkedIn KMS errors."""
    pass


class ScrapingError(LinkedInKMSError):
    """Raised when web scraping operations fail."""
    
    def __init__(self, message: str, url: str = None, status_code: int = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code
    
    def __str__(self):
        base_msg = super().__str__()
        if self.url:
            base_msg += f" (URL: {self.url})"
        if self.status_code:
            base_msg += f" (Status: {self.status_code})"
        return base_msg


class ProcessingError(LinkedInKMSError):
    """Raised when content processing operations fail."""
    
    def __init__(self, message: str, content_id: str = None, stage: str = None):
        super().__init__(message)
        self.content_id = content_id
        self.stage = stage
    
    def __str__(self):
        base_msg = super().__str__()
        if self.stage:
            base_msg += f" (Stage: {self.stage})"
        if self.content_id:
            base_msg += f" (Content ID: {self.content_id})"
        return base_msg


class StorageError(LinkedInKMSError):
    """Raised when storage operations fail."""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation
    
    def __str__(self):
        base_msg = super().__str__()
        if self.operation:
            base_msg += f" (Operation: {self.operation})"
        if self.file_path:
            base_msg += f" (File: {self.file_path})"
        return base_msg


class ConfigurationError(LinkedInKMSError):
    """Raised when configuration is invalid or missing."""
    pass


class APIError(LinkedInKMSError):
    """Raised when external API calls fail."""
    
    def __init__(self, message: str, api_name: str = None, error_code: str = None):
        super().__init__(message)
        self.api_name = api_name
        self.error_code = error_code
    
    def __str__(self):
        base_msg = super().__str__()
        if self.api_name:
            base_msg += f" (API: {self.api_name})"
        if self.error_code:
            base_msg += f" (Code: {self.error_code})"
        return base_msg


class ValidationError(LinkedInKMSError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(message)
        self.field = field
        self.value = value
    
    def __str__(self):
        base_msg = super().__str__()
        if self.field:
            base_msg += f" (Field: {self.field})"
        if self.value:
            base_msg += f" (Value: {self.value})"
        return base_msg