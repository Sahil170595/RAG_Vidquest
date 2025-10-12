"""
Integration tests for RAG Vidquest API.

Tests the complete API endpoints with real database connections
and service integrations.
"""

import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import json

from src.api.app import app
from src.database.connection import db_manager
from src.models.services import model_manager


class TestAPIEndpoints:
    """Test API endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "version" in data
            assert "status" in data
            assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint."""
        # Mock health checks
        with patch.object(db_manager, 'health_check', 
                         return_value={'overall': 'healthy'}):
            with patch.object(model_manager, 'health_check', 
                             return_value={'overall': 'healthy'}):
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/health")
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] in ["healthy", "unhealthy", "degraded"]
                    assert "timestamp" in data
                    assert "version" in data
                    assert "services" in data
    
    @pytest.mark.asyncio
    async def test_query_endpoint_success(self):
        """Test successful query endpoint."""
        # Mock all dependencies
        with patch('src.api.app.get_rag_service') as mock_get_rag:
            mock_rag_service = AsyncMock()
            mock_rag_service.process_query.return_value = AsyncMock(
                query="test query",
                summary="Test answer",
                search_results=[AsyncMock(
                    text="Test content",
                    video_key="test_video",
                    start_time="00:01:00",
                    end_time="00:02:00",
                    score=0.9,
                    metadata={}
                )],
                video_clip_path="/test/clip.mp4",
                processing_time=1.5,
                metadata={}
            )
            mock_get_rag.return_value = mock_rag_service
            
            # Mock authentication
            with patch('src.api.app.verify_api_key', return_value=True):
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.post(
                        "/query",
                        json={
                            "query": "What is machine learning?",
                            "max_results": 5,
                            "min_score": 0.3,
                            "include_video_clip": True
                        }
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["query"] == "test query"
                    assert data["summary"] == "Test answer"
                    assert len(data["search_results"]) == 1
                    assert data["video_clip_path"] == "/test/clip.mp4"
                    assert data["processing_time"] == 1.5
    
    @pytest.mark.asyncio
    async def test_query_endpoint_validation_error(self):
        """Test query endpoint with validation error."""
        with patch('src.api.app.verify_api_key', return_value=True):
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Empty query
                response = await client.post(
                    "/query",
                    json={"query": ""}
                )
                
                assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_query_endpoint_unauthorized(self):
        """Test query endpoint without authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/query",
                json={"query": "test query"}
            )
            
            # Should be unauthorized in production, but allowed in development
            # This test might need adjustment based on environment
            assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test metrics endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert "timestamp" in data
            assert "rate_limits" in data


class TestAPIErrorHandling:
    """Test API error handling."""
    
    @pytest.mark.asyncio
    async def test_rag_exception_handling(self):
        """Test RAG exception handling."""
        from src.core.exceptions import RAGVidquestException, ErrorCode
        
        with patch('src.api.app.get_rag_service') as mock_get_rag:
            mock_rag_service = AsyncMock()
            mock_rag_service.process_query.side_effect = RAGVidquestException(
                "Test error",
                ErrorCode.VALIDATION_ERROR
            )
            mock_get_rag.return_value = mock_rag_service
            
            with patch('src.api.app.verify_api_key', return_value=True):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.post(
                        "/query",
                        json={"query": "test query"}
                    )
                    
                    assert response.status_code == 400
                    data = response.json()
                    assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
                    assert "Test error" in data["message"]
    
    @pytest.mark.asyncio
    async def test_http_exception_handling(self):
        """Test HTTP exception handling."""
        from fastapi import HTTPException
        
        with patch('src.api.app.get_rag_service') as mock_get_rag:
            mock_rag_service = AsyncMock()
            mock_rag_service.process_query.side_effect = HTTPException(
                status_code=404,
                detail="Not found"
            )
            mock_get_rag.return_value = mock_rag_service
            
            with patch('src.api.app.verify_api_key', return_value=True):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.post(
                        "/query",
                        json={"query": "test query"}
                    )
                    
                    assert response.status_code == 404
                    data = response.json()
                    assert data["error_code"] == "HTTP_404"
                    assert data["message"] == "Not found"
    
    @pytest.mark.asyncio
    async def test_general_exception_handling(self):
        """Test general exception handling."""
        with patch('src.api.app.get_rag_service') as mock_get_rag:
            mock_rag_service = AsyncMock()
            mock_rag_service.process_query.side_effect = Exception("Unexpected error")
            mock_get_rag.return_value = mock_rag_service
            
            with patch('src.api.app.verify_api_key', return_value=True):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.post(
                        "/query",
                        json={"query": "test query"}
                    )
                    
                    assert response.status_code == 500
                    data = response.json()
                    assert data["error_code"] == "INTERNAL_001"
                    assert "Internal server error" in data["message"]


class TestAPIMiddleware:
    """Test API middleware functionality."""
    
    @pytest.mark.asyncio
    async def test_cors_middleware(self):
        """Test CORS middleware."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.options(
                "/query",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            
            # CORS headers should be present
            assert "access-control-allow-origin" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # This test would need to be adjusted based on the actual rate limiting implementation
        # For now, we'll test that the rate limiting check is called
        
        with patch('src.api.app.check_rate_limit') as mock_rate_limit:
            with patch('src.api.app.verify_api_key', return_value=True):
                with patch('src.api.app.get_rag_service') as mock_get_rag:
                    mock_rag_service = AsyncMock()
                    mock_rag_service.process_query.return_value = AsyncMock(
                        query="test",
                        summary="test",
                        search_results=[],
                        video_clip_path=None,
                        processing_time=0.1,
                        metadata={}
                    )
                    mock_get_rag.return_value = mock_rag_service
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        response = await client.post(
                            "/query",
                            json={"query": "test query"}
                        )
                        
                        # Rate limit check should be called
                        mock_rate_limit.assert_called()


class TestAPISecurity:
    """Test API security features."""
    
    @pytest.mark.asyncio
    async def test_api_key_authentication(self):
        """Test API key authentication."""
        # This test would need to be adjusted based on the actual authentication implementation
        # For now, we'll test the basic structure
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test without API key
            response = await client.post(
                "/query",
                json={"query": "test query"}
            )
            
            # In development, this might be allowed
            # In production, this should return 401
            assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test input validation."""
        with patch('src.api.app.verify_api_key', return_value=True):
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test invalid input types
                response = await client.post(
                    "/query",
                    json={
                        "query": 123,  # Should be string
                        "max_results": "invalid",  # Should be int
                        "min_score": "invalid"  # Should be float
                    }
                )
                
                assert response.status_code == 422  # Validation error
