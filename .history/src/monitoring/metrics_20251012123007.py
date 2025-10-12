"""
Monitoring and metrics for RAG Vidquest.

Provides Prometheus metrics, health checks, and observability
for production monitoring and alerting.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from typing import Dict, Any, Optional
import time
from datetime import datetime
import asyncio
from functools import wraps

from ..config.logging import get_logger, LoggerMixin
from ..config.settings import config


logger = get_logger(__name__)


# Prometheus metrics
REQUEST_COUNT = Counter(
    'rag_vidquest_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'rag_vidquest_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

QUERY_COUNT = Counter(
    'rag_vidquest_queries_total',
    'Total number of queries processed',
    ['status']
)

QUERY_DURATION = Histogram(
    'rag_vidquest_query_duration_seconds',
    'Query processing duration in seconds'
)

EMBEDDING_COUNT = Counter(
    'rag_vidquest_embeddings_generated_total',
    'Total number of embeddings generated'
)

EMBEDDING_DURATION = Histogram(
    'rag_vidquest_embedding_duration_seconds',
    'Embedding generation duration in seconds'
)

LLM_REQUEST_COUNT = Counter(
    'rag_vidquest_llm_requests_total',
    'Total number of LLM requests',
    ['model', 'status']
)

LLM_DURATION = Histogram(
    'rag_vidquest_llm_duration_seconds',
    'LLM request duration in seconds',
    ['model']
)

VIDEO_PROCESSING_COUNT = Counter(
    'rag_vidquest_video_processing_total',
    'Total number of video processing operations',
    ['operation', 'status']
)

VIDEO_PROCESSING_DURATION = Histogram(
    'rag_vidquest_video_processing_duration_seconds',
    'Video processing duration in seconds',
    ['operation']
)

DATABASE_CONNECTIONS = Gauge(
    'rag_vidquest_database_connections_active',
    'Number of active database connections',
    ['database']
)

CACHE_HITS = Counter(
    'rag_vidquest_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'rag_vidquest_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

APPLICATION_INFO = Info(
    'rag_vidquest_info',
    'Application information'
)

# Set application info
APPLICATION_INFO.info({
    'version': config.app_version,
    'environment': config.environment,
    'app_name': config.app_name
})


class MetricsCollector(LoggerMixin):
    """Collects and manages application metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self._custom_metrics: Dict[str, Any] = {}
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_query(self, status: str, duration: float):
        """Record query processing metrics."""
        QUERY_COUNT.labels(status=status).inc()
        QUERY_DURATION.observe(duration)
    
    def record_embedding(self, duration: float):
        """Record embedding generation metrics."""
        EMBEDDING_COUNT.inc()
        EMBEDDING_DURATION.observe(duration)
    
    def record_llm_request(self, model: str, status: str, duration: float):
        """Record LLM request metrics."""
        LLM_REQUEST_COUNT.labels(model=model, status=status).inc()
        LLM_DURATION.labels(model=model).observe(duration)
    
    def record_video_processing(self, operation: str, status: str, duration: float):
        """Record video processing metrics."""
        VIDEO_PROCESSING_COUNT.labels(operation=operation, status=status).inc()
        VIDEO_PROCESSING_DURATION.labels(operation=operation).observe(duration)
    
    def record_cache_hit(self, cache_type: str):
        """Record cache hit."""
        CACHE_HITS.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record cache miss."""
        CACHE_MISSES.labels(cache_type=cache_type).inc()
    
    def set_database_connections(self, database: str, count: int):
        """Set active database connections count."""
        DATABASE_CONNECTIONS.labels(database=database).set(count)
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary for health checks."""
        return {
            'uptime_seconds': self.get_uptime(),
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'custom_metrics': self._custom_metrics
        }


# Global metrics collector
metrics_collector = MetricsCollector()


def track_request_metrics(func):
    """Decorator to track request metrics."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status = "success"
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            # Extract method and endpoint from function name or args
            method = "POST" if "query" in func.__name__ else "GET"
            endpoint = func.__name__
            
            metrics_collector.record_request(method, endpoint, 200 if status == "success" else 500, duration)
    
    return wrapper


def track_performance(func):
    """Decorator to track performance metrics."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            # Record based on function name
            if "embedding" in func.__name__:
                metrics_collector.record_embedding(duration)
            elif "llm" in func.__name__:
                metrics_collector.record_llm_request("ollama", "success", duration)
            elif "video" in func.__name__:
                metrics_collector.record_video_processing("processing", "success", duration)
    
    return wrapper


class HealthChecker(LoggerMixin):
    """Comprehensive health checking system."""
    
    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.last_check_time: Dict[str, float] = {}
        self.check_interval = config.monitoring.health_check_interval
    
    def register_check(self, name: str, check_func: callable):
        """Register a health check function."""
        self.checks[name] = check_func
        self.logger.info(f"Registered health check: {name}")
    
    async def run_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check."""
        if name not in self.checks:
            return {
                'status': 'unknown',
                'error': f'Check {name} not found'
            }
        
        try:
            check_func = self.checks[name]
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            self.last_check_time[name] = time.time()
            return result
            
        except Exception as e:
            self.logger.error(f"Health check {name} failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        overall_status = "healthy"
        
        for name in self.checks:
            result = await self.run_check(name)
            results[name] = result
            
            if result.get('status') == 'unhealthy':
                overall_status = 'unhealthy'
            elif result.get('status') == 'degraded' and overall_status == 'healthy':
                overall_status = 'degraded'
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': results,
            'metrics': metrics_collector.get_metrics_summary()
        }
    
    def should_run_check(self, name: str) -> bool:
        """Check if enough time has passed since last check."""
        if name not in self.last_check_time:
            return True
        
        return time.time() - self.last_check_time[name] > self.check_interval


# Global health checker
health_checker = HealthChecker()


class DatabaseHealthCheck:
    """Database health check implementation."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    async def check(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            health_status = await self.db_manager.health_check()
            
            if health_status['overall'] == 'healthy':
                return {
                    'status': 'healthy',
                    'details': health_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
            elif health_status['overall'] == 'degraded':
                return {
                    'status': 'degraded',
                    'details': health_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'details': health_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


class ModelHealthCheck:
    """Model service health check implementation."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
    
    async def check(self) -> Dict[str, Any]:
        """Check model service health."""
        try:
            health_status = await self.model_manager.health_check()
            
            if health_status['overall'] == 'healthy':
                return {
                    'status': 'healthy',
                    'details': health_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
            elif health_status['overall'] == 'degraded':
                return {
                    'status': 'degraded',
                    'details': health_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'details': health_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


class SystemHealthCheck:
    """System resource health check."""
    
    async def check(self) -> Dict[str, Any]:
        """Check system resources."""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = 'healthy'
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = 'degraded'
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = 'unhealthy'
            
            return {
                'status': status,
                'details': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_free_gb': disk.free / (1024**3)
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ImportError:
            return {
                'status': 'unknown',
                'error': 'psutil not available',
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


def get_prometheus_metrics() -> str:
    """Get Prometheus metrics in text format."""
    return generate_latest().decode('utf-8')


def initialize_monitoring(db_manager, model_manager):
    """Initialize monitoring with health checks."""
    # Register health checks
    health_checker.register_check('database', DatabaseHealthCheck(db_manager).check)
    health_checker.register_check('models', ModelHealthCheck(model_manager).check)
    health_checker.register_check('system', SystemHealthCheck().check)
    
    logger.info("Monitoring initialized with health checks")
