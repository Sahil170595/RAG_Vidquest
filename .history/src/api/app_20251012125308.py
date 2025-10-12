"""
FastAPI application for RAG Vidquest.

Provides REST API endpoints with proper authentication, validation,
rate limiting, and comprehensive error handling.
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import time
import uuid
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from ..config.settings import config
from ..core.exceptions import RAGVidquestException, ErrorCode, ErrorContext
from ..config.logging import get_logger, LoggerMixin
from ..database.connection import db_manager, VectorRepository, VideoRepository
from ..models.services import model_manager
from ..services.rag import RAGService


# Initialize logger
logger = get_logger(__name__)

# Security
security = HTTPBearer(auto_error=False)

# Rate limiting storage (in production, use Redis)
rate_limit_storage: Dict[str, List[float]] = {}


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    
    query: str = Field(..., min_length=1, max_length=1000, description="The question to ask")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of results to return")
    min_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum similarity score")
    include_video_clip: bool = Field(default=True, description="Whether to include video clip")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    
    query: str
    summary: str
    search_results: List[Dict[str, Any]]
    video_clip_path: Optional[str]
    processing_time: float
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str
    timestamp: str
    version: str
    services: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting RAG Vidquest API...")
    
    try:
        # Initialize database connections
        await db_manager.connect()
        
        # Initialize model services
        await model_manager.initialize()
        
        logger.info("RAG Vidquest API started successfully")
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG Vidquest API...")
    
    try:
        await db_manager.disconnect()
        logger.info("RAG Vidquest API shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Initialize FastAPI app
app = FastAPI(
    title="RAG Vidquest API",
    description="Enterprise-grade Video RAG System API",
    version=config.app_version,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if config.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )


# Dependency injection
async def get_db_manager():
    """Get database manager instance."""
    return db_manager


async def get_rag_service(db_manager=Depends(get_db_manager)):
    """Get RAG service instance."""
    vector_repo = VectorRepository(db_manager)
    video_repo = VideoRepository(db_manager)
    return RAGService(vector_repo, video_repo)


# Authentication
async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verify API key (simplified for demo - use proper auth in production)."""
    if config.environment == "development":
        return True
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # In production, verify against database or external service
    if credentials.credentials != "your-api-key-here":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return True


# Rate limiting
def check_rate_limit(request: Request):
    """Check rate limit for the request."""
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old entries
    if client_ip in rate_limit_storage:
        rate_limit_storage[client_ip] = [
            timestamp for timestamp in rate_limit_storage[client_ip]
            if current_time - timestamp < 60  # Keep only last minute
        ]
    else:
        rate_limit_storage[client_ip] = []
    
    # Check limit
    if len(rate_limit_storage[client_ip]) >= config.security.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Add current request
    rate_limit_storage[client_ip].append(current_time)


# Exception handlers
@app.exception_handler(RAGVidquestException)
async def rag_exception_handler(request: Request, exc: RAGVidquestException):
    """Handle custom RAG exceptions."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error_code=exc.error_code.value,
            message=exc.message,
            details=exc.to_dict(),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR.value,
            message="Internal server error",
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting RAG Vidquest API...")
    
    try:
        # Initialize database connections
        await db_manager.connect()
        
        # Initialize model services
        await model_manager.initialize()
        
        logger.info("RAG Vidquest API started successfully")
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG Vidquest API...")
    
    try:
        await db_manager.disconnect()
        logger.info("RAG Vidquest API shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with basic information."""
    return {
        "name": config.app_name,
        "version": config.app_version,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Check database health
        db_health = await db_manager.health_check()
        
        # Check model health
        model_health = await model_manager.health_check()
        
        # Check RAG service health
        rag_service = await get_rag_service()
        rag_health = await rag_service.health_check()
        
        # Determine overall status
        overall_status = "healthy"
        if (db_health["overall"] != "healthy" or 
            model_health["overall"] != "healthy" or 
            rag_health["overall"] != "healthy"):
            overall_status = "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            version=config.app_version,
            services={
                "database": db_health,
                "models": model_health,
                "rag": rag_health
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            version=config.app_version,
            services={"error": str(e)}
        )


@app.post("/query", response_model=QueryResponse)
async def query_videos(
    request: QueryRequest,
    rag_service=Depends(get_rag_service),
    _: bool = Depends(verify_api_key)
):
    """Query videos using RAG pipeline."""
    # Check rate limit
    check_rate_limit(Request)
    
    try:
        # Process query through RAG pipeline
        response = await rag_service.process_query(
            query=request.query,
            max_results=request.max_results,
            min_score=request.min_score,
            include_video_clip=request.include_video_clip
        )
        
        # Convert to response format
        return QueryResponse(
            query=response.query,
            summary=response.summary,
            search_results=[
                {
                    "text": result.text,
                    "video_key": result.video_key,
                    "start_time": result.start_time,
                    "end_time": result.end_time,
                    "score": result.score,
                    "metadata": result.metadata
                }
                for result in response.search_results
            ],
            video_clip_path=response.video_clip_path,
            processing_time=response.processing_time,
            metadata=response.metadata or {}
        )
        
    except RAGVidquestException:
        # Re-raise custom exceptions (handled by exception handler)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in query endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/metrics")
async def get_metrics():
    """Get application metrics (basic implementation)."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "rate_limits": {
            "active_clients": len(rate_limit_storage),
            "total_requests_last_minute": sum(len(requests) for requests in rate_limit_storage.values())
        },
        "cache_stats": {
            "search_cache_size": len(getattr(rag_service, '_search_cache', {})) if 'rag_service' in locals() else 0
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
        log_level=config.logging.level.lower()
    )
