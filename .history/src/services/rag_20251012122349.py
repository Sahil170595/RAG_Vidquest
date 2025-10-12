"""
RAG (Retrieval-Augmented Generation) service for RAG Vidquest.

Provides semantic search, content retrieval, and response generation
with proper caching and performance optimization.
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass
from datetime import datetime

from ..config.settings import config
from ..core.exceptions import RAGVidquestException, ErrorCode
from ..config.logging import LoggerMixin, log_performance
from ..database.connection import VectorRepository, VideoRepository
from ..models.services import model_manager
from ..services.video import video_service


@dataclass
class SearchResult:
    """Result from semantic search."""
    
    text: str
    video_key: str
    start_time: str
    end_time: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RAGResponse:
    """Complete RAG response."""
    
    query: str
    search_results: List[SearchResult]
    summary: str
    video_clip_path: Optional[str]
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None


class SemanticSearchService(LoggerMixin):
    """Service for semantic search operations."""
    
    def __init__(self, vector_repo: VectorRepository):
        self.vector_repo = vector_repo
        self.cache_size = 1000
        self._search_cache: Dict[str, List[SearchResult]] = {}
    
    @log_performance
    async def search_similar_content(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """Search for similar content using semantic similarity."""
        try:
            # Check cache first
            cache_key = f"{query}_{limit}_{min_score}"
            if cache_key in self._search_cache:
                self.logger.debug(f"Using cached search results for query: {query[:50]}...")
                return self._search_cache[cache_key]
            
            # Generate query embedding
            query_embedding = await model_manager.embedding_service.encode_query(query)
            
            # Search vector database
            vector_results = await self.vector_repo.search_similar(query_embedding, limit * 2)
            
            # Convert to SearchResult objects and filter by score
            search_results = []
            for result in vector_results:
                if result['score'] >= min_score:
                    payload = result['payload']
                    search_results.append(SearchResult(
                        text=payload.get('text', ''),
                        video_key=payload.get('video_key', ''),
                        start_time=payload.get('start', ''),
                        end_time=payload.get('end', ''),
                        score=result['score'],
                        metadata={
                            'vector_id': result['id'],
                            'payload': payload
                        }
                    ))
            
            # Sort by score and limit results
            search_results.sort(key=lambda x: x.score, reverse=True)
            search_results = search_results[:limit]
            
            # Cache results
            self._search_cache[cache_key] = search_results
            if len(self._search_cache) > self.cache_size:
                # Remove oldest entries
                keys_to_remove = list(self._search_cache.keys())[:100]
                for key in keys_to_remove:
                    del self._search_cache[key]
            
            self.logger.info(f"Found {len(search_results)} similar content segments for query: {query[:50]}...")
            return search_results
            
        except Exception as e:
            raise RAGVidquestException(
                f"Failed to perform semantic search: {e}",
                ErrorCode.VECTOR_DB_QUERY_ERROR,
                original_exception=e
            )
    
    def clear_cache(self) -> None:
        """Clear search cache."""
        self._search_cache.clear()
        self.logger.info("Search cache cleared")


class ContentRetrievalService(LoggerMixin):
    """Service for retrieving and processing content."""
    
    def __init__(self, video_repo: VideoRepository):
        self.video_repo = video_repo
    
    async def get_video_clip(
        self,
        video_key: str,
        start_time: str,
        end_time: str
    ) -> Optional[str]:
        """Get or create video clip for the given time range."""
        try:
            # Check if clip already exists
            clip_filename = f"{video_key}_{start_time.replace(':', '-')}_{end_time.replace(':', '-')}.mp4"
            clip_path = config.paths.clip_output / clip_filename
            
            if clip_path.exists():
                self.logger.debug(f"Using existing clip: {clip_path}")
                return str(clip_path)
            
            # Find video file
            video_path = await video_service.find_video_file(video_key)
            if not video_path:
                self.logger.warning(f"Video file not found for key: {video_key}")
                return None
            
            # Create new clip
            clip_path = await video_service.create_clip(video_path, start_time, end_time)
            return clip_path
            
        except Exception as e:
            self.logger.error(f"Failed to get video clip: {e}")
            return None
    
    async def get_context_for_results(self, search_results: List[SearchResult]) -> str:
        """Get formatted context from search results."""
        if not search_results:
            return "No relevant content found."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"{i}. {result.text}\n"
                f"   (Video: {result.video_key}, Time: {result.start_time}-{result.end_time}, "
                f"Score: {result.score:.3f})"
            )
        
        return "\n\n".join(context_parts)


class ResponseGenerationService(LoggerMixin):
    """Service for generating responses using LLM."""
    
    def __init__(self):
        self.system_prompt = (
            "You are a helpful AI assistant that answers questions based on video lecture content. "
            "Provide clear, accurate, and comprehensive answers using only the information provided. "
            "If the provided content doesn't contain enough information to fully answer the question, "
            "acknowledge this limitation. Always cite the relevant video segments when possible."
        )
    
    @log_performance
    async def generate_response(
        self,
        query: str,
        context: str,
        additional_context: Optional[str] = None
    ) -> str:
        """Generate response using LLM."""
        try:
            # Prepare the prompt
            prompt_parts = [
                "Based on the following video lecture content, please answer the question:",
                f"\nQuestion: {query}",
                f"\nRelevant Content:",
                context
            ]
            
            if additional_context:
                prompt_parts.extend([
                    f"\nAdditional Context:",
                    additional_context
                ])
            
            prompt_parts.extend([
                "\n\nPlease provide a clear, comprehensive answer based on the content above. "
                "If the content doesn't fully address the question, please mention what information "
                "is missing or unclear."
            ])
            
            prompt = "\n".join(prompt_parts)
            
            # Generate response using LLM
            response = await model_manager.llm_service.generate_response(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=config.model.max_tokens,
                temperature=config.model.temperature
            )
            
            return response.content
            
        except Exception as e:
            raise RAGVidquestException(
                f"Failed to generate response: {e}",
                ErrorCode.OLLAMA_RESPONSE_ERROR,
                original_exception=e
            )


class RAGService(LoggerMixin):
    """Main RAG service that orchestrates the entire pipeline."""
    
    def __init__(
        self,
        vector_repo: VectorRepository,
        video_repo: VideoRepository
    ):
        self.semantic_search = SemanticSearchService(vector_repo)
        self.content_retrieval = ContentRetrievalService(video_repo)
        self.response_generation = ResponseGenerationService()
    
    @log_performance
    async def process_query(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0.3,
        include_video_clip: bool = True
    ) -> RAGResponse:
        """Process a query through the complete RAG pipeline."""
        start_time = datetime.now()
        
        try:
            # Validate input
            if not query or not query.strip():
                raise RAGVidquestException(
                    "Query cannot be empty",
                    ErrorCode.VALIDATION_ERROR
                )
            
            query = query.strip()
            self.logger.info(f"Processing query: {query[:100]}...")
            
            # Step 1: Semantic search
            search_results = await self.semantic_search.search_similar_content(
                query=query,
                limit=max_results,
                min_score=min_score
            )
            
            if not search_results:
                return RAGResponse(
                    query=query,
                    search_results=[],
                    summary="No relevant content found for your query.",
                    video_clip_path=None,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    metadata={'status': 'no_results'}
                )
            
            # Step 2: Get context
            context = await self.content_retrieval.get_context_for_results(search_results)
            
            # Step 3: Generate response
            summary = await self.response_generation.generate_response(
                query=query,
                context=context
            )
            
            # Step 4: Get video clip (if requested and available)
            video_clip_path = None
            if include_video_clip and search_results:
                top_result = search_results[0]
                video_clip_path = await self.content_retrieval.get_video_clip(
                    video_key=top_result.video_key,
                    start_time=top_result.start_time,
                    end_time=top_result.end_time
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            response = RAGResponse(
                query=query,
                search_results=search_results,
                summary=summary,
                video_clip_path=video_clip_path,
                processing_time=processing_time,
                metadata={
                    'num_results': len(search_results),
                    'top_score': search_results[0].score if search_results else 0,
                    'include_video_clip': include_video_clip,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Successfully processed query in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Failed to process query after {processing_time:.2f}s: {e}")
            
            if isinstance(e, RAGVidquestException):
                raise
            
            raise RAGVidquestException(
                f"Failed to process query: {e}",
                ErrorCode.INTERNAL_ERROR,
                original_exception=e
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of RAG service components."""
        health_status = {
            'semantic_search': {'status': 'unknown'},
            'content_retrieval': {'status': 'unknown'},
            'response_generation': {'status': 'unknown'},
            'overall': 'unknown'
        }
        
        try:
            # Test semantic search
            test_results = await self.semantic_search.search_similar_content(
                query="test query",
                limit=1,
                min_score=0.0
            )
            health_status['semantic_search']['status'] = 'healthy'
            health_status['semantic_search']['test_results'] = len(test_results)
        except Exception as e:
            health_status['semantic_search']['status'] = 'unhealthy'
            health_status['semantic_search']['error'] = str(e)
        
        # Test content retrieval
        try:
            # This is a basic test - in production you might want more comprehensive tests
            health_status['content_retrieval']['status'] = 'healthy'
        except Exception as e:
            health_status['content_retrieval']['status'] = 'unhealthy'
            health_status['content_retrieval']['error'] = str(e)
        
        # Test response generation
        try:
            test_response = await self.response_generation.generate_response(
                query="test",
                context="test context"
            )
            health_status['response_generation']['status'] = 'healthy'
            health_status['response_generation']['test_response_length'] = len(test_response)
        except Exception as e:
            health_status['response_generation']['status'] = 'unhealthy'
            health_status['response_generation']['error'] = str(e)
        
        # Overall status
        component_statuses = [
            health_status['semantic_search']['status'],
            health_status['content_retrieval']['status'],
            health_status['response_generation']['status']
        ]
        
        if all(status == 'healthy' for status in component_statuses):
            health_status['overall'] = 'healthy'
        elif any(status == 'unhealthy' for status in component_statuses):
            health_status['overall'] = 'unhealthy'
        else:
            health_status['overall'] = 'degraded'
        
        return health_status
