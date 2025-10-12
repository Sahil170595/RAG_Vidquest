"""
Exception handling and custom exceptions for RAG Vidquest.

Provides comprehensive error handling with proper error codes,
logging, and user-friendly error messages.
"""

from typing import Optional, Dict, Any, Union
from enum import Enum
import traceback
from dataclasses import dataclass

from .logging import get_logger


class ErrorCode(Enum):
    """Standardized error codes for the application."""
    
    # Configuration errors
    CONFIG_VALIDATION_ERROR = "CONFIG_001"
    CONFIG_LOAD_ERROR = "CONFIG_002"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DB_001"
    DATABASE_QUERY_ERROR = "DB_002"
    DATABASE_INSERT_ERROR = "DB_003"
    DATABASE_UPDATE_ERROR = "DB_004"
    
    # Model errors
    MODEL_LOAD_ERROR = "MODEL_001"
    MODEL_INFERENCE_ERROR = "MODEL_002"
    EMBEDDING_ERROR = "MODEL_003"
    
    # Video processing errors
    VIDEO_NOT_FOUND = "VIDEO_001"
    VIDEO_PROCESSING_ERROR = "VIDEO_002"
    VIDEO_FORMAT_ERROR = "VIDEO_003"
    FRAME_EXTRACTION_ERROR = "VIDEO_004"
    
    # Vector database errors
    VECTOR_DB_CONNECTION_ERROR = "VECTOR_001"
    VECTOR_DB_QUERY_ERROR = "VECTOR_002"
    VECTOR_DB_INSERT_ERROR = "VECTOR_003"
    
    # API errors
    API_VALIDATION_ERROR = "API_001"
    API_RATE_LIMIT_ERROR = "API_002"
    API_AUTHENTICATION_ERROR = "API_003"
    API_AUTHORIZATION_ERROR = "API_004"
    
    # External service errors
    OLLAMA_CONNECTION_ERROR = "OLLAMA_001"
    OLLAMA_RESPONSE_ERROR = "OLLAMA_002"
    
    # General errors
    INTERNAL_ERROR = "INTERNAL_001"
    VALIDATION_ERROR = "VALIDATION_001"
    TIMEOUT_ERROR = "TIMEOUT_001"


@dataclass
class ErrorContext:
    """Context information for errors."""
    
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class RAGVidquestException(Exception):
    """Base exception class for RAG Vidquest application."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or ErrorContext()
        self.original_exception = original_exception
        
        # Log the error
        logger = get_logger(self.__class__.__module__)
        logger.error(
            f"Error {error_code.value}: {message}",
            extra={
                'error_code': error_code.value,
                'context': self.context.__dict__,
                'original_exception': str(original_exception) if original_exception else None
            },
            exc_info=True
        )
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            'error_code': self.error_code.value,
            'message': self.message,
            'context': self.context.__dict__ if self.context else None,
            'type': self.__class__.__name__
        }


class ConfigurationError(RAGVidquestException):
    """Raised when configuration validation fails."""
    
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIG_VALIDATION_ERROR,
            original_exception=original_exception
        )


class DatabaseError(RAGVidquestException):
    """Raised when database operations fail."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DATABASE_CONNECTION_ERROR,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            original_exception=original_exception
        )


class ModelError(RAGVidquestException):
    """Raised when model operations fail."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.MODEL_INFERENCE_ERROR,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            original_exception=original_exception
        )


class VideoProcessingError(RAGVidquestException):
    """Raised when video processing operations fail."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.VIDEO_PROCESSING_ERROR,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            original_exception=original_exception
        )


class VectorDatabaseError(RAGVidquestException):
    """Raised when vector database operations fail."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.VECTOR_DB_CONNECTION_ERROR,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            original_exception=original_exception
        )


class APIError(RAGVidquestException):
    """Raised when API operations fail."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.API_VALIDATION_ERROR,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            original_exception=original_exception
        )


class ExternalServiceError(RAGVidquestException):
    """Raised when external service operations fail."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.OLLAMA_CONNECTION_ERROR,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            original_exception=original_exception
        )


def handle_exception(func):
    """Decorator to handle exceptions and convert them to RAGVidquestException."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RAGVidquestException:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Convert other exceptions to our custom exception
            logger = get_logger(func.__module__)
            logger.error(f"Unhandled exception in {func.__name__}: {e}", exc_info=True)
            
            raise RAGVidquestException(
                message=f"Unexpected error in {func.__name__}: {str(e)}",
                error_code=ErrorCode.INTERNAL_ERROR,
                original_exception=e
            )
    
    return wrapper


def validate_not_none(value: Any, name: str) -> None:
    """Validate that a value is not None."""
    if value is None:
        raise ValidationError(f"{name} cannot be None")


def validate_not_empty(value: Union[str, list, dict], name: str) -> None:
    """Validate that a value is not empty."""
    if not value:
        raise ValidationError(f"{name} cannot be empty")


class ValidationError(RAGVidquestException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            original_exception=original_exception
        )
