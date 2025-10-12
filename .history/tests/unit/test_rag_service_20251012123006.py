"""
Unit tests for RAG service.

Tests the core RAG functionality including semantic search,
content retrieval, and response generation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.rag import RAGService, SemanticSearchService, ContentRetrievalService, ResponseGenerationService
from src.core.exceptions import RAGVidquestException, ErrorCode


class TestSemanticSearchService:
    """Test semantic search service."""
    
    @pytest.mark.asyncio
    async def test_search_similar_content_success(self, mock_vector_repository, mock_model_manager):
        """Test successful semantic search."""
        # Setup
        service = SemanticSearchService(mock_vector_repository)
        
        # Mock embedding generation
        with patch.object(mock_model_manager.embedding_service, 'encode_query', 
                         return_value=[0.1] * 384):
            
            # Execute
            results = await service.search_similar_content("test query", limit=5)
            
            # Assert
            assert len(results) == 1
            assert results[0].text == "Test content about machine learning"
            assert results[0].score == 0.95
            assert results[0].video_key == "test_video"
    
    @pytest.mark.asyncio
    async def test_search_similar_content_empty_results(self, mock_vector_repository, mock_model_manager):
        """Test semantic search with empty results."""
        # Setup
        service = SemanticSearchService(mock_vector_repository)
        mock_vector_repository.search_similar.return_value = []
        
        # Mock embedding generation
        with patch.object(mock_model_manager.embedding_service, 'encode_query', 
                         return_value=[0.1] * 384):
            
            # Execute
            results = await service.search_similar_content("test query")
            
            # Assert
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_similar_content_min_score_filter(self, mock_vector_repository, mock_model_manager):
        """Test semantic search with minimum score filtering."""
        # Setup
        service = SemanticSearchService(mock_vector_repository)
        mock_vector_repository.search_similar.return_value = [
            {'id': 1, 'score': 0.9, 'payload': {'text': 'High score', 'video_key': 'vid1', 'start': '00:01:00', 'end': '00:02:00'}},
            {'id': 2, 'score': 0.2, 'payload': {'text': 'Low score', 'video_key': 'vid2', 'start': '00:01:00', 'end': '00:02:00'}}
        ]
        
        # Mock embedding generation
        with patch.object(mock_model_manager.embedding_service, 'encode_query', 
                         return_value=[0.1] * 384):
            
            # Execute
            results = await service.search_similar_content("test query", min_score=0.5)
            
            # Assert
            assert len(results) == 1
            assert results[0].score == 0.9
    
    @pytest.mark.asyncio
    async def test_search_similar_content_caching(self, mock_vector_repository, mock_model_manager):
        """Test semantic search caching."""
        # Setup
        service = SemanticSearchService(mock_vector_repository)
        
        # Mock embedding generation
        with patch.object(mock_model_manager.embedding_service, 'encode_query', 
                         return_value=[0.1] * 384):
            
            # Execute first search
            results1 = await service.search_similar_content("test query")
            
            # Execute second search (should use cache)
            results2 = await service.search_similar_content("test query")
            
            # Assert
            assert results1 == results2
            # Verify search was only called once due to caching
            assert mock_vector_repository.search_similar.call_count == 1


class TestContentRetrievalService:
    """Test content retrieval service."""
    
    @pytest.mark.asyncio
    async def test_get_video_clip_existing(self, mock_video_repository, mock_video_service):
        """Test getting existing video clip."""
        # Setup
        service = ContentRetrievalService(mock_video_repository)
        
        # Mock existing clip
        with patch('pathlib.Path.exists', return_value=True):
            result = await service.get_video_clip("test_video", "00:01:00", "00:02:00")
            
            # Assert
            assert result is not None
            assert "test_video" in result
    
    @pytest.mark.asyncio
    async def test_get_video_clip_create_new(self, mock_video_repository, mock_video_service):
        """Test creating new video clip."""
        # Setup
        service = ContentRetrievalService(mock_video_repository)
        
        # Mock non-existing clip
        with patch('pathlib.Path.exists', return_value=False):
            with patch.object(mock_video_service, 'create_clip', 
                             return_value="/test/path/new_clip.mp4"):
                result = await service.get_video_clip("test_video", "00:01:00", "00:02:00")
                
                # Assert
                assert result == "/test/path/new_clip.mp4"
    
    @pytest.mark.asyncio
    async def test_get_context_for_results(self, mock_video_repository, sample_search_results):
        """Test context generation from search results."""
        # Setup
        service = ContentRetrievalService(mock_video_repository)
        
        # Execute
        context = await service.get_context_for_results(sample_search_results)
        
        # Assert
        assert "neural networks and deep learning" in context
        assert "Convolutional neural networks" in context
        assert "ml_video_1" in context
        assert "ml_video_2" in context


class TestResponseGenerationService:
    """Test response generation service."""
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, mock_model_manager):
        """Test successful response generation."""
        # Setup
        service = ResponseGenerationService()
        
        # Mock LLM service
        mock_model_manager.llm_service.generate_response.return_value = Mock(
            content="This is a comprehensive answer about machine learning.",
            model_name="test-model",
            processing_time=0.5
        )
        
        # Execute
        response = await service.generate_response(
            query="What is machine learning?",
            context="Machine learning is a subset of AI..."
        )
        
        # Assert
        assert "comprehensive answer about machine learning" in response
        mock_model_manager.llm_service.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_with_additional_context(self, mock_model_manager):
        """Test response generation with additional context."""
        # Setup
        service = ResponseGenerationService()
        
        # Mock LLM service
        mock_model_manager.llm_service.generate_response.return_value = Mock(
            content="Answer with additional context.",
            model_name="test-model",
            processing_time=0.5
        )
        
        # Execute
        response = await service.generate_response(
            query="Test question",
            context="Main context",
            additional_context="Additional context"
        )
        
        # Assert
        assert "Answer with additional context" in response
        # Verify additional context was included in the prompt
        call_args = mock_model_manager.llm_service.generate_response.call_args
        assert "Additional context" in call_args[1]['prompt']


class TestRAGService:
    """Test main RAG service."""
    
    @pytest.mark.asyncio
    async def test_process_query_success(self, mock_vector_repository, mock_video_repository, mock_model_manager, mock_video_service):
        """Test successful query processing."""
        # Setup
        rag_service = RAGService(mock_vector_repository, mock_video_repository)
        
        # Mock all dependencies
        with patch.object(rag_service.semantic_search, 'search_similar_content', 
                         return_value=[Mock(
                             text="Test content",
                             video_key="test_video",
                             start_time="00:01:00",
                             end_time="00:02:00",
                             score=0.9
                         )]):
            with patch.object(rag_service.content_retrieval, 'get_context_for_results', 
                             return_value="Test context"):
                with patch.object(rag_service.response_generation, 'generate_response', 
                                 return_value="Test answer"):
                    with patch.object(rag_service.content_retrieval, 'get_video_clip', 
                                     return_value="/test/clip.mp4"):
                        
                        # Execute
                        response = await rag_service.process_query("test query")
                        
                        # Assert
                        assert response.query == "test query"
                        assert response.summary == "Test answer"
                        assert response.video_clip_path == "/test/clip.mp4"
                        assert response.processing_time > 0
                        assert len(response.search_results) == 1
    
    @pytest.mark.asyncio
    async def test_process_query_no_results(self, mock_vector_repository, mock_video_repository):
        """Test query processing with no results."""
        # Setup
        rag_service = RAGService(mock_vector_repository, mock_video_repository)
        
        # Mock empty search results
        with patch.object(rag_service.semantic_search, 'search_similar_content', 
                         return_value=[]):
            
            # Execute
            response = await rag_service.process_query("test query")
            
            # Assert
            assert response.query == "test query"
            assert "No relevant content found" in response.summary
            assert response.video_clip_path is None
            assert len(response.search_results) == 0
    
    @pytest.mark.asyncio
    async def test_process_query_empty_query(self, mock_vector_repository, mock_video_repository):
        """Test query processing with empty query."""
        # Setup
        rag_service = RAGService(mock_vector_repository, mock_video_repository)
        
        # Execute and assert
        with pytest.raises(RAGVidquestException) as exc_info:
            await rag_service.process_query("")
        
        assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR
    
    @pytest.mark.asyncio
    async def test_process_query_without_video_clip(self, mock_vector_repository, mock_video_repository):
        """Test query processing without video clip."""
        # Setup
        rag_service = RAGService(mock_vector_repository, mock_video_repository)
        
        # Mock search results
        with patch.object(rag_service.semantic_search, 'search_similar_content', 
                         return_value=[Mock(
                             text="Test content",
                             video_key="test_video",
                             start_time="00:01:00",
                             end_time="00:02:00",
                             score=0.9
                         )]):
            with patch.object(rag_service.content_retrieval, 'get_context_for_results', 
                             return_value="Test context"):
                with patch.object(rag_service.response_generation, 'generate_response', 
                                 return_value="Test answer"):
                    
                    # Execute
                    response = await rag_service.process_query(
                        "test query", 
                        include_video_clip=False
                    )
                    
                    # Assert
                    assert response.video_clip_path is None
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_vector_repository, mock_video_repository):
        """Test health check functionality."""
        # Setup
        rag_service = RAGService(mock_vector_repository, mock_video_repository)
        
        # Mock health checks
        with patch.object(rag_service.semantic_search, 'search_similar_content', 
                         return_value=[]):
            with patch.object(rag_service.response_generation, 'generate_response', 
                             return_value="test"):
                
                # Execute
                health = await rag_service.health_check()
                
                # Assert
                assert 'overall' in health
                assert 'semantic_search' in health
                assert 'content_retrieval' in health
                assert 'response_generation' in health
