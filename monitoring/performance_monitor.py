"""
Performance Monitoring - Track bot performance metrics
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

from cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    timestamp: datetime
    metric_type: str
    value: float
    tags: Dict[str, str]

class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    def __init__(self, cache: Optional[RedisCache] = None):
        self.cache = cache or RedisCache()
        self.metrics_buffer = defaultdict(list)
        self.flush_interval = 60  # Flush metrics every minute
        self._running = False
        
    async def start(self):
        """Start the performance monitor"""
        self._running = True
        asyncio.create_task(self._flush_metrics_periodically())
        logger.info("Performance monitor started")
        
    async def stop(self):
        """Stop the performance monitor"""
        self._running = False
        await self._flush_metrics()
        logger.info("Performance monitor stopped")
        
    def record_trade_execution(self, chain: str, execution_time: float, success: bool):
        """Record trade execution metrics"""
        self.metrics_buffer['trade_execution'].append(
            PerformanceMetric(
                timestamp=datetime.now(),
                metric_type='trade_execution_time',
                value=execution_time,
                tags={'chain': chain, 'success': str(success)}
            )
        )
        
    def record_api_latency(self, api_name: str, latency: float):
        """Record API call latency"""
        self.metrics_buffer['api_latency'].append(
            PerformanceMetric(
                timestamp=datetime.now(),
                metric_type='api_latency',
                value=latency,
                tags={'api': api_name}
            )
        )
        
    def record_queue_size(self, queue_name: str, size: int):
        """Record queue size"""
        self.metrics_buffer['queue_size'].append(
            PerformanceMetric(
                timestamp=datetime.now(),
                metric_type='queue_size',
                value=float(size),
                tags={'queue': queue_name}
            )
        )
        
    def record_cache_hit_rate(self, cache_type: str, hit: bool):
        """Record cache hit/miss"""
        self.metrics_buffer['cache_hits'].append(
            PerformanceMetric(
                timestamp=datetime.now(),
                metric_type='cache_hit',
                value=1.0 if hit else 0.0,
                tags={'cache_type': cache_type}
            )
        )
        
    def record_websocket_reconnect(self, service: str):
        """Record WebSocket reconnection"""
        self.metrics_buffer['websocket_reconnects'].append(
            PerformanceMetric(
                timestamp=datetime.now(),
                metric_type='websocket_reconnect',
                value=1.0,
                tags={'service': service}
            )
        )
        
    def record_error(self, error_type: str, component: str):
        """Record error occurrence"""
        self.metrics_buffer['errors'].append(
            PerformanceMetric(
                timestamp=datetime.now(),
                metric_type='error',
                value=1.0,
                tags={'error_type': error_type, 'component': component}
            )
        )
        
    async def _flush_metrics(self):
        """Flush metrics to Redis"""
        try:
            for metric_type, metrics in self.metrics_buffer.items():
                if not metrics:
                    continue
                    
                # Store in Redis with timestamp bucket
                bucket_time = datetime.now().replace(second=0, microsecond=0)
                key = f"metrics:{metric_type}:{bucket_time.isoformat()}"
                
                # Convert metrics to dict for storage
                metrics_data = [asdict(m) for m in metrics]
                existing = self.cache.get(key) or []
                existing.extend(metrics_data)
                
                self.cache.set(key, existing, expire=86400)  # Keep for 24 hours
                
            # Clear buffer
            self.metrics_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")
            
    async def _flush_metrics_periodically(self):
        """Periodically flush metrics to storage"""
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self._flush_metrics()
            
    async def get_metrics_summary(self, hours: int = 1) -> Dict[str, any]:
        """Get metrics summary for the last N hours"""
        summary = {
            'trade_execution': {
                'count': 0,
                'avg_time': 0,
                'success_rate': 0,
            },
            'api_latency': {},
            'cache_hit_rate': {},
            'errors': defaultdict(int),
            'queue_sizes': {},
        }
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Iterate through time buckets
        current_time = start_time.replace(second=0, microsecond=0)
        while current_time <= end_time:
            # Fetch metrics for each type
            for metric_type in ['trade_execution', 'api_latency', 'cache_hits', 'errors']:
                key = f"metrics:{metric_type}:{current_time.isoformat()}"
                metrics = self.cache.get(key) or []
                
                for metric in metrics:
                    if metric_type == 'trade_execution':
                        summary['trade_execution']['count'] += 1
                        summary['trade_execution']['avg_time'] += metric['value']
                        if metric['tags']['success'] == 'True':
                            summary['trade_execution']['success_rate'] += 1
                            
                    elif metric_type == 'api_latency':
                        api = metric['tags']['api']
                        if api not in summary['api_latency']:
                            summary['api_latency'][api] = []
                        summary['api_latency'][api].append(metric['value'])
                        
                    elif metric_type == 'cache_hits':
                        cache_type = metric['tags']['cache_type']
                        if cache_type not in summary['cache_hit_rate']:
                            summary['cache_hit_rate'][cache_type] = {'hits': 0, 'total': 0}
                        summary['cache_hit_rate'][cache_type]['total'] += 1
                        if metric['value'] > 0:
                            summary['cache_hit_rate'][cache_type]['hits'] += 1
                            
                    elif metric_type == 'errors':
                        error_key = f"{metric['tags']['component']}:{metric['tags']['error_type']}"
                        summary['errors'][error_key] += 1
                        
            current_time += timedelta(minutes=1)
            
        # Calculate averages
        if summary['trade_execution']['count'] > 0:
            summary['trade_execution']['avg_time'] /= summary['trade_execution']['count']
            summary['trade_execution']['success_rate'] = (
                summary['trade_execution']['success_rate'] / summary['trade_execution']['count']
            )
            
        # Calculate API latency averages
        for api, latencies in summary['api_latency'].items():
            if latencies:
                summary['api_latency'][api] = sum(latencies) / len(latencies)
                
        # Calculate cache hit rates
        for cache_type, stats in summary['cache_hit_rate'].items():
            if stats['total'] > 0:
                summary['cache_hit_rate'][cache_type] = stats['hits'] / stats['total']
                
        return summary

# Decorators for automatic performance tracking
def track_execution_time(metric_name: str):
    """Decorator to track function execution time"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                monitor.record_api_latency(metric_name, execution_time)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                monitor.record_api_latency(metric_name, execution_time)
                monitor.record_error(type(e).__name__, metric_name)
                raise
                
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                monitor.record_api_latency(metric_name, execution_time)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                monitor.record_api_latency(metric_name, execution_time)
                monitor.record_error(type(e).__name__, metric_name)
                raise
                
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

# Global monitor instance
monitor = PerformanceMonitor()