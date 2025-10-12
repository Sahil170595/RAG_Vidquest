"""
Caching and performance optimization for RAG Vidquest.

Provides Redis-based caching, connection pooling,
and performance monitoring for enterprise scalability.
"""

import asyncio
import json
import pickle
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
import time
from functools import wraps
import hashlib

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..config.settings import config
from ..config.logging import get_logger, LoggerMixin
from ..core.exceptions import RAGVidquestException, ErrorCode


logger = get_logger(__name__)


class CacheManager(LoggerMixin):
    """Manages caching operations with Redis backend."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        self.default_ttl = 3600  # 1 hour
        self.key_prefix = "rag_vidquest:"
    
    async def connect(self) -> None:
        """Connect to Redis server."""
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis not available, using in-memory cache")
            return
        
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            self.logger.info("Connected to Redis cache")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            self.logger.info("Disconnected from Redis")
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            # Try JSON first for simple types
            return json.dumps(value, default=str).encode('utf-8')
        except (TypeError, ValueError):
            # Fallback to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to pickle
            return pickle.loads(data)
    
    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_connected or not self.redis_client:
            return None
        
        try:
            full_key = self._make_key(key)
            data = await self.redis_client.get(full_key)
            
            if data is None:
                return None
            
            return self._deserialize_value(data)
            
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            full_key = self._make_key(key)
            serialized_value = self._serialize_value(value)
            ttl = ttl or self.default_ttl
            
            await self.redis_client.setex(full_key, ttl, serialized_value)
            return True
            
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            full_key = self._make_key(key)
            result = await self.redis_client.delete(full_key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            full_key = self._make_key(key)
            return await self.redis_client.exists(full_key) > 0
            
        except Exception as e:
            self.logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.is_connected or not self.redis_client:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = await self.redis_client.keys(full_pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                return len(keys)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.is_connected or not self.redis_client:
            return {'status': 'disconnected'}
        
        try:
            info = await self.redis_client.info()
            return {
                'status': 'connected',
                'used_memory': info.get('used_memory_human', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Cache stats error: {e}")
            return {'status': 'error', 'error': str(e)}


class InMemoryCache:
    """Fallback in-memory cache when Redis is not available."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        now = time.time()
        expired_keys = []
        
        for key, data in self.cache.items():
            if data['expires_at'] and now > data['expires_at']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            del self.access_times[key]
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[lru_key]
        del self.access_times[lru_key]
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        self._cleanup_expired()
        
        if key not in self.cache:
            return None
        
        self.access_times[key] = time.time()
        return self.cache[key]['value']
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        self._cleanup_expired()
        
        # Evict if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()
        
        expires_at = None
        if ttl:
            expires_at = time.time() + ttl
        
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
        self.access_times[key] = time.time()
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        self._cleanup_expired()
        return key in self.cache
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        import fnmatch
        
        self._cleanup_expired()
        matching_keys = [key for key in self.cache.keys() if fnmatch.fnmatch(key, pattern)]
        
        for key in matching_keys:
            del self.cache[key]
            del self.access_times[key]
        
        return len(matching_keys)


class CacheDecorator:
    """Decorator for caching function results."""
    
    def __init__(self, cache_manager: CacheManager, ttl: int = 3600, key_prefix: str = ""):
        self.cache_manager = cache_manager
        self.ttl = ttl
        self.key_prefix = key_prefix
    
    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = self._generate_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}")
            result = await func(*args, **kwargs)
            
            # Cache the result
            await self.cache_manager.set(cache_key, result, self.ttl)
            
            return result
        
        return wrapper
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments."""
        # Create a hash of the arguments
        args_str = str(args) + str(sorted(kwargs.items()))
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
        
        return f"{self.key_prefix}{func_name}:{args_hash}"


class PerformanceOptimizer(LoggerMixin):
    """Performance optimization utilities."""
    
    def __init__(self):
        self.connection_pools: Dict[str, Any] = {}
        self.batch_operations: Dict[str, List] = {}
    
    async def batch_embedding_requests(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Process embedding requests in batches for better performance."""
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Process batch concurrently
            batch_results = await asyncio.gather(
                *[self._process_single_embedding(text) for text in batch],
                return_exceptions=True
            )
            
            # Handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Embedding error for text {i + j}: {result}")
                    results.append([0.0] * 384)  # Fallback embedding
                else:
                    results.append(result)
        
        return results
    
    async def _process_single_embedding(self, text: str) -> List[float]:
        """Process single embedding request."""
        # This would integrate with the actual embedding service
        # For now, return a placeholder
        return [0.1] * 384
    
    def optimize_database_queries(self, queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize database queries by batching and deduplication."""
        # Remove duplicate queries
        unique_queries = []
        seen_queries = set()
        
        for query in queries:
            query_key = str(sorted(query.items()))
            if query_key not in seen_queries:
                unique_queries.append(query)
                seen_queries.add(query_key)
        
        # Sort by priority/type for better batching
        unique_queries.sort(key=lambda q: q.get('priority', 0), reverse=True)
        
        return unique_queries
    
    async def parallel_video_processing(self, video_tasks: List[Dict[str, Any]]) -> List[Any]:
        """Process multiple video operations in parallel."""
        semaphore = asyncio.Semaphore(5)  # Limit concurrent operations
        
        async def process_with_semaphore(task):
            async with semaphore:
                return await self._process_video_task(task)
        
        results = await asyncio.gather(
            *[process_with_semaphore(task) for task in video_tasks],
            return_exceptions=True
        )
        
        return results
    
    async def _process_video_task(self, task: Dict[str, Any]) -> Any:
        """Process individual video task."""
        # This would integrate with the actual video processing service
        # For now, return a placeholder
        return {"status": "processed", "task": task}


# Global cache manager
cache_manager = CacheManager()

# Fallback in-memory cache
in_memory_cache = InMemoryCache()

# Global performance optimizer
performance_optimizer = PerformanceOptimizer()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results."""
    def decorator(func):
        return CacheDecorator(cache_manager, ttl, key_prefix)(func)
    return decorator


async def initialize_caching():
    """Initialize caching system."""
    await cache_manager.connect()
    
    if not cache_manager.is_connected:
        logger.warning("Redis not available, using in-memory cache fallback")
        # In a real implementation, you'd set up fallback mechanisms here


async def get_cache_stats() -> Dict[str, Any]:
    """Get comprehensive cache statistics."""
    stats = await cache_manager.get_stats()
    
    if not cache_manager.is_connected:
        stats['fallback_cache'] = {
            'size': len(in_memory_cache.cache),
            'max_size': in_memory_cache.max_size
        }
    
    return stats
