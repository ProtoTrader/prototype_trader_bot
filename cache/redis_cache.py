import redis
import json
import pickle
from typing import Optional, Any, Union
from datetime import timedelta
import asyncio
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=False
        )
        self.async_redis = None
        
    async def init_async(self):
        import aioredis
        self.async_redis = await aioredis.create_redis_pool(
            f'redis://localhost',
            encoding='utf-8'
        )
        
    def _serialize(self, value: Any) -> bytes:
        """Serialize Python objects to bytes"""
        if isinstance(value, (str, int, float)):
            return json.dumps(value).encode('utf-8')
        return pickle.dumps(value)
        
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize bytes to Python objects"""
        if value is None:
            return None
        try:
            return json.loads(value.decode('utf-8'))
        except:
            return pickle.loads(value)
    
    def set(self, key: str, value: Any, expire: Optional[int] = None):
        """Set a value in cache"""
        serialized = self._serialize(value)
        if expire:
            self.redis_client.setex(key, expire, serialized)
        else:
            self.redis_client.set(key, serialized)
            
    def get(self, key: str) -> Any:
        """Get a value from cache"""
        value = self.redis_client.get(key)
        return self._deserialize(value)
        
    def delete(self, key: str):
        """Delete a key from cache"""
        self.redis_client.delete(key)
        
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.redis_client.exists(key)
        
    def expire(self, key: str, seconds: int):
        """Set expiration time for a key"""
        self.redis_client.expire(key, seconds)
        
    def ttl(self, key: str) -> int:
        """Get time to live for a key"""
        return self.redis_client.ttl(key)
        
    def set_price(self, chain: str, token: str, price: float, expire: int = 60):
        """Cache token price"""
        key = f"price:{chain}:{token}"
        self.set(key, price, expire)
        
    def get_price(self, chain: str, token: str) -> Optional[float]:
        """Get cached token price"""
        key = f"price:{chain}:{token}"
        return self.get(key)
        
    def set_liquidity(self, chain: str, pair: str, liquidity: dict, expire: int = 300):
        """Cache liquidity data"""
        key = f"liquidity:{chain}:{pair}"
        self.set(key, liquidity, expire)
        
    def get_liquidity(self, chain: str, pair: str) -> Optional[dict]:
        """Get cached liquidity data"""
        key = f"liquidity:{chain}:{pair}"
        return self.get(key)
        
    def set_gas_price(self, chain: str, gas_price: int, expire: int = 30):
        """Cache gas price"""
        key = f"gas:{chain}"
        self.set(key, gas_price, expire)
        
    def get_gas_price(self, chain: str) -> Optional[int]:
        """Get cached gas price"""
        key = f"gas:{chain}"
        return self.get(key)
        
    def set_user_session(self, user_id: int, session_data: dict, expire: int = 3600):
        """Cache user session data"""
        key = f"session:{user_id}"
        self.set(key, session_data, expire)
        
    def get_user_session(self, user_id: int) -> Optional[dict]:
        """Get cached user session data"""
        key = f"session:{user_id}"
        return self.get(key)
        
    def cache_transaction(self, tx_hash: str, tx_data: dict, expire: int = 86400):
        """Cache transaction data"""
        key = f"tx:{tx_hash}"
        self.set(key, tx_data, expire)
        
    def get_transaction(self, tx_hash: str) -> Optional[dict]:
        """Get cached transaction data"""
        key = f"tx:{tx_hash}"
        return self.get(key)
        
    def increment_rate_limit(self, key: str, window: int = 60) -> int:
        """Increment rate limit counter"""
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        result = pipe.execute()
        return result[0]
        
    def check_rate_limit(self, key: str, limit: int) -> bool:
        """Check if rate limit exceeded"""
        count = self.redis_client.get(key)
        if count is None:
            return True
        return int(count) <= limit
        
    def add_to_queue(self, queue_name: str, item: Any):
        """Add item to queue"""
        serialized = self._serialize(item)
        self.redis_client.rpush(queue_name, serialized)
        
    def pop_from_queue(self, queue_name: str, timeout: int = 0) -> Any:
        """Pop item from queue (blocking)"""
        if timeout:
            result = self.redis_client.blpop(queue_name, timeout)
            if result:
                return self._deserialize(result[1])
        else:
            result = self.redis_client.lpop(queue_name)
            if result:
                return self._deserialize(result)
        return None
        
    def queue_length(self, queue_name: str) -> int:
        """Get queue length"""
        return self.redis_client.llen(queue_name)
        
    def publish(self, channel: str, message: Any):
        """Publish message to channel"""
        serialized = self._serialize(message)
        self.redis_client.publish(channel, serialized)
        
    def subscribe(self, channel: str):
        """Subscribe to channel"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)
        return pubsub
        
    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        for key in self.redis_client.scan_iter(pattern):
            self.redis_client.delete(key)

def cached(expire: int = 300):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = RedisCache()
            key = f"func:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
                
            result = await func(*args, **kwargs)
            cache.set(key, result, expire)
            return result
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = RedisCache()
            key = f"func:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
                
            result = func(*args, **kwargs)
            cache.set(key, result, expire)
            return result
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

# Global cache instance
cache = RedisCache()