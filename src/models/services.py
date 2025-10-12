"""
Model management and inference services for RAG Vidquest.

Handles embedding models, LLM integration, and provides
caching and performance optimization.
"""

from typing import List, Dict, Any, Optional, Union
import asyncio
import time
from functools import lru_cache
import numpy as np
from sentence_transformers import SentenceTransformer
import requests
import json
from dataclasses import dataclass

from ..config.settings import config
from ..core.exceptions import ModelError, ExternalServiceError, ErrorCode
from ..config.logging import LoggerMixin, log_performance


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    
    embeddings: List[List[float]]
    model_name: str
    processing_time: float
    token_count: Optional[int] = None


@dataclass
class LLMResponse:
    """Response from LLM service."""
    
    content: str
    model_name: str
    processing_time: float
    token_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingService(LoggerMixin):
    """Service for generating text embeddings."""
    
    def __init__(self):
        self._model: Optional[SentenceTransformer] = None
        self._model_name = config.model.embedding_model
        self._cache_size = 1000
        self._embedding_cache: Dict[str, List[float]] = {}
    
    async def initialize(self) -> None:
        """Initialize the embedding model."""
        try:
            self.logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            self.logger.info("Embedding model loaded successfully")
        except Exception as e:
            raise ModelError(
                f"Failed to load embedding model {self._model_name}: {e}",
                ErrorCode.MODEL_LOAD_ERROR,
                original_exception=e
            )
    
    @log_performance
    async def encode_text(self, text: Union[str, List[str]]) -> EmbeddingResult:
        """Generate embeddings for text."""
        if not self._model:
            raise ModelError("Embedding model not initialized", ErrorCode.MODEL_LOAD_ERROR)
        
        start_time = time.time()
        
        try:
            # Handle single text or batch
            if isinstance(text, str):
                texts = [text]
                single_text = True
            else:
                texts = text
                single_text = False
            
            # Check cache for single text
            if single_text and text in self._embedding_cache:
                self.logger.debug(f"Using cached embedding for text: {text[:50]}...")
                embeddings = [self._embedding_cache[text]]
            else:
                # Generate embeddings
                embeddings = self._model.encode(texts, convert_to_tensor=False)
                
                # Convert to list format
                if isinstance(embeddings, np.ndarray):
                    embeddings = embeddings.tolist()
                
                # Cache single text result
                if single_text:
                    self._embedding_cache[text] = embeddings[0]
                    # Limit cache size
                    if len(self._embedding_cache) > self._cache_size:
                        # Remove oldest entries
                        keys_to_remove = list(self._embedding_cache.keys())[:100]
                        for key in keys_to_remove:
                            del self._embedding_cache[key]
            
            processing_time = time.time() - start_time
            
            return EmbeddingResult(
                embeddings=embeddings,
                model_name=self._model_name,
                processing_time=processing_time,
                token_count=len(texts)
            )
            
        except Exception as e:
            raise ModelError(
                f"Failed to generate embeddings: {e}",
                ErrorCode.EMBEDDING_ERROR,
                original_exception=e
            )
    
    async def encode_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        result = await self.encode_text(query)
        return result.embeddings[0]
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        self.logger.info("Embedding cache cleared")


class LLMService(LoggerMixin):
    """Service for LLM interactions via Ollama."""
    
    def __init__(self):
        self.base_url = config.model.ollama_url
        self.model_name = config.model.ollama_model
        self.max_tokens = config.model.max_tokens
        self.temperature = config.model.temperature
        self.timeout = 30
    
    @log_performance
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate response from LLM."""
        start_time = time.time()
        
        try:
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare payload
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": max_tokens or self.max_tokens,
                    "temperature": temperature or self.temperature
                }
            }
            
            # Make request
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract content
            if "message" in data and "content" in data["message"]:
                content = data["message"]["content"].strip()
            elif "response" in data:
                content = data["response"].strip()
            else:
                raise ExternalServiceError(
                    f"Unexpected response format from Ollama: {data}",
                    ErrorCode.OLLAMA_RESPONSE_ERROR
                )
            
            processing_time = time.time() - start_time
            
            return LLMResponse(
                content=content,
                model_name=self.model_name,
                processing_time=processing_time,
                token_count=len(prompt.split()),  # Rough estimate
                metadata={
                    "ollama_response": data,
                    "prompt_length": len(prompt)
                }
            )
            
        except requests.exceptions.RequestException as e:
            raise ExternalServiceError(
                f"Failed to connect to Ollama service: {e}",
                ErrorCode.OLLAMA_CONNECTION_ERROR,
                original_exception=e
            )
        except Exception as e:
            raise ExternalServiceError(
                f"Failed to generate LLM response: {e}",
                ErrorCode.OLLAMA_RESPONSE_ERROR,
                original_exception=e
            )
    
    async def summarize_content(
        self,
        content: str,
        question: str,
        context: Optional[str] = None
    ) -> str:
        """Summarize content based on a question."""
        system_prompt = (
            "You are a helpful assistant that summarizes lecture content. "
            "Provide clear, accurate answers based only on the provided content. "
            "If the content doesn't contain enough information to answer the question, "
            "say so explicitly."
        )
        
        prompt = f"Here's the content to analyze:\n\n{content}\n\n"
        
        if context:
            prompt += f"Additional context:\n{context}\n\n"
        
        prompt += f"Question: {question}\n\nPlease provide a clear, comprehensive answer."
        
        response = await self.generate_response(prompt, system_prompt)
        return response.content
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Ollama service is healthy."""
        try:
            # Simple ping request
            response = requests.get(
                self.base_url.replace("/api/chat", "/api/tags"),
                timeout=5
            )
            response.raise_for_status()
            
            return {
                "status": "healthy",
                "model_available": self.model_name in str(response.json()),
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


class ModelManager(LoggerMixin):
    """Manages all model services."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all model services."""
        try:
            await self.embedding_service.initialize()
            self._initialized = True
            self.logger.info("All model services initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize model services: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all model services."""
        health_status = {
            "embedding_service": {"status": "unknown"},
            "llm_service": {"status": "unknown"},
            "overall": "unknown"
        }
        
        # Check embedding service
        try:
            if self.embedding_service._model:
                health_status["embedding_service"]["status"] = "healthy"
            else:
                health_status["embedding_service"]["status"] = "not_initialized"
        except Exception as e:
            health_status["embedding_service"]["status"] = "unhealthy"
            health_status["embedding_service"]["error"] = str(e)
        
        # Check LLM service
        llm_health = await self.llm_service.health_check()
        health_status["llm_service"] = llm_health
        
        # Overall status
        if (health_status["embedding_service"]["status"] == "healthy" and 
            health_status["llm_service"]["status"] == "healthy"):
            health_status["overall"] = "healthy"
        elif (health_status["embedding_service"]["status"] == "unhealthy" or 
              health_status["llm_service"]["status"] == "unhealthy"):
            health_status["overall"] = "unhealthy"
        else:
            health_status["overall"] = "degraded"
        
        return health_status
    
    @property
    def is_initialized(self) -> bool:
        """Check if all services are initialized."""
        return self._initialized


# Global model manager instance
model_manager = ModelManager()
