"""
Performance monitoring and optimization utilities.

Provides profiling, performance metrics, and optimization
recommendations for enterprise-grade performance.
"""

import time
import asyncio
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import tracemalloc
from contextlib import asynccontextmanager

from ..config.logging import get_logger, LoggerMixin
from ..config.settings import config


logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    
    function_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System resource metrics."""
    
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_percent: float
    disk_free_gb: float
    network_io: Dict[str, int]
    timestamp: datetime


class PerformanceProfiler(LoggerMixin):
    """Profiles application performance."""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.max_metrics = 10000
        self.profiling_enabled = config.monitoring.enable_metrics
        self._lock = threading.Lock()
    
    def start_profiling(self):
        """Start memory profiling."""
        if self.profiling_enabled:
            tracemalloc.start()
    
    def stop_profiling(self):
        """Stop memory profiling."""
        if self.profiling_enabled:
            tracemalloc.stop()
    
    def record_metrics(self, metrics: PerformanceMetrics):
        """Record performance metrics."""
        if not self.profiling_enabled:
            return
        
        with self._lock:
            self.metrics.append(metrics)
            
            # Keep only recent metrics
            if len(self.metrics) > self.max_metrics:
                self.metrics = self.metrics[-self.max_metrics:]
    
    def get_recent_metrics(self, minutes: int = 5) -> List[PerformanceMetrics]:
        """Get metrics from the last N minutes."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self._lock:
            return [
                metric for metric in self.metrics
                if metric.timestamp > cutoff_time
            ]
    
    def get_function_stats(self, function_name: str) -> Dict[str, Any]:
        """Get statistics for a specific function."""
        function_metrics = [
            metric for metric in self.metrics
            if metric.function_name == function_name
        ]
        
        if not function_metrics:
            return {}
        
        execution_times = [m.execution_time for m in function_metrics]
        memory_usages = [m.memory_usage for m in function_metrics]
        
        return {
            'call_count': len(function_metrics),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'min_execution_time': min(execution_times),
            'max_execution_time': max(execution_times),
            'avg_memory_usage': sum(memory_usages) / len(memory_usages),
            'min_memory_usage': min(memory_usages),
            'max_memory_usage': max(memory_usages),
            'last_called': max(m.timestamp for m in function_metrics)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        if not self.metrics:
            return {'status': 'no_data'}
        
        recent_metrics = self.get_recent_metrics(5)
        
        if not recent_metrics:
            return {'status': 'no_recent_data'}
        
        execution_times = [m.execution_time for m in recent_metrics]
        memory_usages = [m.memory_usage for m in recent_metrics]
        
        # Group by function
        function_stats = {}
        for metric in recent_metrics:
            if metric.function_name not in function_stats:
                function_stats[metric.function_name] = []
            function_stats[metric.function_name].append(metric.execution_time)
        
        # Find slowest functions
        slowest_functions = sorted(
            function_stats.items(),
            key=lambda x: sum(x[1]) / len(x[1]),
            reverse=True
        )[:5]
        
        return {
            'status': 'active',
            'total_calls': len(recent_metrics),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'max_execution_time': max(execution_times),
            'avg_memory_usage': sum(memory_usages) / len(memory_usages),
            'slowest_functions': [
                {'function': name, 'avg_time': sum(times) / len(times)}
                for name, times in slowest_functions
            ],
            'timestamp': datetime.utcnow().isoformat()
        }


class SystemMonitor(LoggerMixin):
    """Monitors system resource usage."""
    
    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.max_history = 1000
        self._lock = threading.Lock()
    
    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)
            
            # Network I/O
            network_io = psutil.net_io_counters()._asdict()
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_gb=memory_available_gb,
                disk_percent=disk_percent,
                disk_free_gb=disk_free_gb,
                network_io=network_io,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return SystemMetrics(
                cpu_percent=0,
                memory_percent=0,
                memory_available_gb=0,
                disk_percent=0,
                disk_free_gb=0,
                network_io={},
                timestamp=datetime.utcnow()
            )
    
    def record_metrics(self, metrics: SystemMetrics):
        """Record system metrics."""
        with self._lock:
            self.metrics_history.append(metrics)
            
            # Keep only recent metrics
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history:]
    
    def get_metrics_trend(self, minutes: int = 10) -> Dict[str, List[float]]:
        """Get metrics trend over time."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self._lock:
            recent_metrics = [
                m for m in self.metrics_history
                if m.timestamp > cutoff_time
            ]
        
        if not recent_metrics:
            return {}
        
        return {
            'timestamps': [m.timestamp.isoformat() for m in recent_metrics],
            'cpu_percent': [m.cpu_percent for m in recent_metrics],
            'memory_percent': [m.memory_percent for m in recent_metrics],
            'disk_percent': [m.disk_percent for m in recent_metrics]
        }
    
    def check_resource_alerts(self) -> List[Dict[str, Any]]:
        """Check for resource usage alerts."""
        current_metrics = self.get_current_metrics()
        alerts = []
        
        # CPU alert
        if current_metrics.cpu_percent > 90:
            alerts.append({
                'type': 'cpu_high',
                'level': 'warning',
                'value': current_metrics.cpu_percent,
                'message': f'CPU usage is {current_metrics.cpu_percent:.1f}%'
            })
        elif current_metrics.cpu_percent > 95:
            alerts.append({
                'type': 'cpu_high',
                'level': 'critical',
                'value': current_metrics.cpu_percent,
                'message': f'CPU usage is critically high: {current_metrics.cpu_percent:.1f}%'
            })
        
        # Memory alert
        if current_metrics.memory_percent > 90:
            alerts.append({
                'type': 'memory_high',
                'level': 'warning',
                'value': current_metrics.memory_percent,
                'message': f'Memory usage is {current_metrics.memory_percent:.1f}%'
            })
        
        # Disk alert
        if current_metrics.disk_percent > 90:
            alerts.append({
                'type': 'disk_high',
                'level': 'warning',
                'value': current_metrics.disk_percent,
                'message': f'Disk usage is {current_metrics.disk_percent:.1f}%'
            })
        
        return alerts


class PerformanceOptimizer(LoggerMixin):
    """Provides performance optimization recommendations."""
    
    def __init__(self, profiler: PerformanceProfiler, system_monitor: SystemMonitor):
        self.profiler = profiler
        self.system_monitor = system_monitor
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance and provide recommendations."""
        recommendations = []
        
        # Analyze function performance
        recent_metrics = self.profiler.get_recent_metrics(10)
        if recent_metrics:
            slow_functions = [
                metric for metric in recent_metrics
                if metric.execution_time > 1.0  # Functions taking more than 1 second
            ]
            
            if slow_functions:
                recommendations.append({
                    'type': 'slow_functions',
                    'priority': 'high',
                    'message': f'{len(slow_functions)} functions are taking more than 1 second',
                    'functions': [m.function_name for m in slow_functions[:5]]
                })
        
        # Analyze system resources
        current_metrics = self.system_monitor.get_current_metrics()
        
        if current_metrics.cpu_percent > 80:
            recommendations.append({
                'type': 'cpu_optimization',
                'priority': 'medium',
                'message': f'High CPU usage: {current_metrics.cpu_percent:.1f}%',
                'suggestions': [
                    'Consider horizontal scaling',
                    'Optimize CPU-intensive operations',
                    'Implement caching for repeated operations'
                ]
            })
        
        if current_metrics.memory_percent > 80:
            recommendations.append({
                'type': 'memory_optimization',
                'priority': 'medium',
                'message': f'High memory usage: {current_metrics.memory_percent:.1f}%',
                'suggestions': [
                    'Review memory leaks',
                    'Implement memory pooling',
                    'Consider increasing memory limits'
                ]
            })
        
        # Analyze trends
        trend = self.system_monitor.get_metrics_trend(30)
        if trend and len(trend.get('cpu_percent', [])) > 10:
            cpu_trend = trend['cpu_percent']
            if all(cpu_trend[i] < cpu_trend[i+1] for i in range(len(cpu_trend)-1)):
                recommendations.append({
                    'type': 'trend_analysis',
                    'priority': 'low',
                    'message': 'CPU usage is trending upward',
                    'suggestions': ['Monitor for potential issues', 'Consider proactive scaling']
                })
        
        return {
            'recommendations': recommendations,
            'current_metrics': {
                'cpu_percent': current_metrics.cpu_percent,
                'memory_percent': current_metrics.memory_percent,
                'disk_percent': current_metrics.disk_percent
            },
            'timestamp': datetime.utcnow().isoformat()
        }


def profile_function(func):
    """Decorator to profile function performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = getattr(wrapper, '_profiler', None)
        if not profiler:
            return await func(*args, **kwargs)
        
        start_time = time.time()
        start_memory = 0
        
        # Get initial memory usage
        try:
            process = psutil.Process()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
        except:
            pass
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            # Calculate metrics
            execution_time = time.time() - start_time
            
            try:
                process = psutil.Process()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_usage = end_memory - start_memory
            except:
                memory_usage = 0
            
            try:
                cpu_usage = psutil.cpu_percent()
            except:
                cpu_usage = 0
            
            # Record metrics
            metrics = PerformanceMetrics(
                function_name=func.__name__,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                timestamp=datetime.utcnow(),
                metadata={
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
            )
            
            profiler.record_metrics(metrics)
    
    return wrapper


@asynccontextmanager
async def performance_context(name: str):
    """Context manager for performance monitoring."""
    profiler = getattr(performance_context, '_profiler', None)
    if not profiler:
        yield
        return
    
    start_time = time.time()
    start_memory = 0
    
    try:
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024
    except:
        pass
    
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        
        try:
            process = psutil.Process()
            end_memory = process.memory_info().rss / 1024 / 1024
            memory_usage = end_memory - start_memory
        except:
            memory_usage = 0
        
        try:
            cpu_usage = psutil.cpu_percent()
        except:
            cpu_usage = 0
        
        metrics = PerformanceMetrics(
            function_name=name,
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            timestamp=datetime.utcnow()
        )
        
        profiler.record_metrics(metrics)


# Global instances
profiler = PerformanceProfiler()
system_monitor = SystemMonitor()
performance_optimizer = PerformanceOptimizer(profiler, system_monitor)


def initialize_performance_monitoring():
    """Initialize performance monitoring."""
    profiler.start_profiling()
    
    # Start background system monitoring
    async def monitor_system():
        while True:
            try:
                metrics = system_monitor.get_current_metrics()
                system_monitor.record_metrics(metrics)
                await asyncio.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    # Start monitoring task
    asyncio.create_task(monitor_system())
    
    logger.info("Performance monitoring initialized")


def get_performance_report() -> Dict[str, Any]:
    """Get comprehensive performance report."""
    return {
        'profiler_summary': profiler.get_performance_summary(),
        'system_alerts': system_monitor.check_resource_alerts(),
        'optimization_recommendations': performance_optimizer.analyze_performance(),
        'timestamp': datetime.utcnow().isoformat()
    }
