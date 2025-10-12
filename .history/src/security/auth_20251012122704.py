"""
Security utilities for RAG Vidquest.

Provides authentication, authorization, input validation,
and security best practices for enterprise deployment.
"""

import hashlib
import hmac
import secrets
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bleach

from ..config.settings import config
from ..config.logging import get_logger, LoggerMixin
from ..core.exceptions import APIError, ErrorCode


logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security_scheme = HTTPBearer(auto_error=False)


class SecurityManager(LoggerMixin):
    """Manages security operations and validation."""
    
    def __init__(self):
        self.secret_key = config.security.secret_key
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.rate_limit_storage: Dict[str, List[datetime]] = {}
        self.blocked_ips: set = set()
    
    def generate_api_key(self, user_id: str, permissions: List[str] = None) -> str:
        """Generate a new API key for a user."""
        try:
            # Generate random key
            key = secrets.token_urlsafe(32)
            
            # Hash the key for storage
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            
            # Store key metadata
            self.api_keys[key_hash] = {
                'user_id': user_id,
                'permissions': permissions or ['read'],
                'created_at': datetime.utcnow(),
                'last_used': None,
                'is_active': True
            }
            
            self.logger.info(f"Generated API key for user: {user_id}")
            return key
            
        except Exception as e:
            self.logger.error(f"Failed to generate API key: {e}")
            raise APIError(
                "Failed to generate API key",
                ErrorCode.API_AUTHENTICATION_ERROR,
                original_exception=e
            )
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return user info."""
        try:
            if not api_key:
                return None
            
            # Hash the provided key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Check if key exists and is active
            if key_hash not in self.api_keys:
                return None
            
            key_info = self.api_keys[key_hash]
            if not key_info['is_active']:
                return None
            
            # Update last used timestamp
            key_info['last_used'] = datetime.utcnow()
            
            return {
                'user_id': key_info['user_id'],
                'permissions': key_info['permissions'],
                'created_at': key_info['created_at']
            }
            
        except Exception as e:
            self.logger.error(f"API key validation error: {e}")
            return None
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            if key_hash in self.api_keys:
                self.api_keys[key_hash]['is_active'] = False
                self.logger.info(f"Revoked API key for user: {self.api_keys[key_hash]['user_id']}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to revoke API key: {e}")
            return False
    
    def check_permissions(self, user_info: Dict[str, Any], required_permission: str) -> bool:
        """Check if user has required permission."""
        if not user_info or 'permissions' not in user_info:
            return False
        
        return required_permission in user_info['permissions'] or 'admin' in user_info['permissions']


class InputValidator(LoggerMixin):
    """Validates and sanitizes user input."""
    
    def __init__(self):
        # Allowed HTML tags for content (if any)
        self.allowed_tags = []
        self.allowed_attributes = {}
        
        # Query validation patterns
        self.query_pattern = re.compile(r'^[a-zA-Z0-9\s\?\.\,\!\-\_\(\)]+$')
        self.max_query_length = 1000
        self.min_query_length = 1
    
    def validate_query(self, query: str) -> str:
        """Validate and sanitize query input."""
        if not query:
            raise APIError(
                "Query cannot be empty",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        # Check length
        if len(query) < self.min_query_length:
            raise APIError(
                f"Query too short (minimum {self.min_query_length} characters)",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        if len(query) > self.max_query_length:
            raise APIError(
                f"Query too long (maximum {self.max_query_length} characters)",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        # Check for malicious patterns
        if not self.query_pattern.match(query.strip()):
            raise APIError(
                "Query contains invalid characters",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        # Sanitize HTML
        sanitized_query = bleach.clean(query.strip(), tags=self.allowed_tags, attributes=self.allowed_attributes)
        
        return sanitized_query
    
    def validate_max_results(self, max_results: int) -> int:
        """Validate max_results parameter."""
        if not isinstance(max_results, int):
            raise APIError(
                "max_results must be an integer",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        if max_results < 1:
            raise APIError(
                "max_results must be at least 1",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        if max_results > 50:
            raise APIError(
                "max_results cannot exceed 50",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        return max_results
    
    def validate_min_score(self, min_score: float) -> float:
        """Validate min_score parameter."""
        if not isinstance(min_score, (int, float)):
            raise APIError(
                "min_score must be a number",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        if min_score < 0.0:
            raise APIError(
                "min_score must be at least 0.0",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        if min_score > 1.0:
            raise APIError(
                "min_score cannot exceed 1.0",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        return float(min_score)
    
    def validate_file_path(self, file_path: str) -> str:
        """Validate file path for security."""
        if not file_path:
            raise APIError(
                "File path cannot be empty",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        # Check for path traversal attempts
        if '..' in file_path or file_path.startswith('/'):
            raise APIError(
                "Invalid file path",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        # Check for allowed extensions
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.vtt', '.srt'}
        if not any(file_path.lower().endswith(ext) for ext in allowed_extensions):
            raise APIError(
                "File type not allowed",
                ErrorCode.API_VALIDATION_ERROR
            )
        
        return file_path


class RateLimiter(LoggerMixin):
    """Rate limiting implementation."""
    
    def __init__(self):
        self.limit_per_minute = config.security.rate_limit_per_minute
        self.limit_per_hour = self.limit_per_minute * 60
        self.requests: Dict[str, List[datetime]] = {}
    
    def is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited."""
        now = datetime.utcnow()
        
        # Clean old requests
        if client_ip in self.requests:
            # Keep only requests from last hour
            cutoff_time = now - timedelta(hours=1)
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if req_time > cutoff_time
            ]
        else:
            self.requests[client_ip] = []
        
        # Check minute limit
        minute_cutoff = now - timedelta(minutes=1)
        recent_requests = [
            req_time for req_time in self.requests[client_ip]
            if req_time > minute_cutoff
        ]
        
        if len(recent_requests) >= self.limit_per_minute:
            self.logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return True
        
        # Check hour limit
        if len(self.requests[client_ip]) >= self.limit_per_hour:
            self.logger.warning(f"Hourly rate limit exceeded for IP: {client_ip}")
            return True
        
        # Record this request
        self.requests[client_ip].append(now)
        return False
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Get remaining requests for client."""
        now = datetime.utcnow()
        
        if client_ip not in self.requests:
            return self.limit_per_minute
        
        minute_cutoff = now - timedelta(minutes=1)
        recent_requests = [
            req_time for req_time in self.requests[client_ip]
            if req_time > minute_cutoff
        ]
        
        return max(0, self.limit_per_minute - len(recent_requests))


class SecurityHeaders:
    """Manages security headers for responses."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers for responses."""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }


# Global security instances
security_manager = SecurityManager()
input_validator = InputValidator()
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded headers (proxy/load balancer)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    return request.client.host if request.client else 'unknown'


def require_auth(required_permission: str = 'read'):
    """Decorator to require authentication."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args (assuming it's the first argument)
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get API key from header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication header"
                )
            
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Validate API key
            user_info = security_manager.validate_api_key(api_key)
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            
            # Check permissions
            if not security_manager.check_permissions(user_info, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            # Check rate limit
            client_ip = get_client_ip(request)
            if rate_limiter.is_rate_limited(client_ip):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            # Add user info to kwargs for use in the function
            kwargs['user_info'] = user_info
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_input(func):
    """Decorator to validate input parameters."""
    async def wrapper(*args, **kwargs):
        # Validate query if present
        if 'query' in kwargs:
            kwargs['query'] = input_validator.validate_query(kwargs['query'])
        
        # Validate other parameters
        if 'max_results' in kwargs:
            kwargs['max_results'] = input_validator.validate_max_results(kwargs['max_results'])
        
        if 'min_score' in kwargs:
            kwargs['min_score'] = input_validator.validate_min_score(kwargs['min_score'])
        
        return await func(*args, **kwargs)
    
    return wrapper
