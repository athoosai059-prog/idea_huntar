"""
Caching layer for IdeaHunter using Redis.
Provides caching for API responses, computed data, and expensive operations.
"""

import json
import hashlib
import pickle
from typing import Optional, Any, Callable
from functools import wraps
from backend.utils.logging_config import get_logger

log = get_logger(__name__)

# Try to import Redis, fall back to in-memory cache if not available
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    log.warning("Redis not available, using in-memory cache")


class CacheManager:
    """Manages caching with Redis fallback to in-memory cache."""

    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379,
                 redis_db: int = 0, redis_password: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
            redis_password: Redis password
        """
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache

        if HAS_REDIS:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=False,  # Store as bytes
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                log.info("Connected to Redis cache")
            except Exception as e:
                log.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
                self.redis_client = None
        else:
            log.info("Using in-memory cache")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                if data:
                    return pickle.loads(data)
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            log.error(f"Error getting from cache: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.redis_client:
                data = pickle.dumps(value)
                self.redis_client.setex(key, ttl, data)
            else:
                self.memory_cache[key] = value
            return True
        except Exception as e:
            log.error(f"Error setting cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self.memory_cache.pop(key, None)
            return True
        except Exception as e:
            log.error(f"Error deleting from cache: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            else:
                return key in self.memory_cache
        except Exception as e:
            log.error(f"Error checking cache existence: {e}")
            return False

    def clear(self) -> bool:
        """
        Clear all cached values.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.redis_client:
                self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
            return True
        except Exception as e:
            log.error(f"Error clearing cache: {e}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            if self.redis_client:
                info = self.redis_client.info()
                return {
                    'type': 'redis',
                    'keys': info.get('db0', {}).get('keys', 0),
                    'memory_used': info.get('used_memory_human', 'N/A'),
                    'hits': info.get('keyspace_hits', 0),
                    'misses': info.get('keyspace_misses', 0)
                }
            else:
                return {
                    'type': 'memory',
                    'keys': len(self.memory_cache),
                    'memory_used': 'N/A',
                    'hits': 0,
                    'misses': 0
                }
        except Exception as e:
            log.error(f"Error getting cache stats: {e}")
            return {'type': 'unknown', 'error': str(e)}


# Global cache instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl: int = 3600, key_prefix: str = ''):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]

            # Add arguments to key
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

            cache_key = hashlib.md5(':'.join(key_parts).encode()).hexdigest()

            # Try to get from cache
            cache = get_cache_manager()
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                log.debug(f"Cache hit for {func.__name__}: {cache_key[:16]}...")
                return cached_value

            # Execute function and cache result
            log.debug(f"Cache miss for {func.__name__}: {cache_key[:16]}...")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


def cache_result(key: str, value: Any, ttl: int = 3600) -> bool:
    """
    Cache a result with a specific key.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds

    Returns:
        True if successful, False otherwise
    """
    cache = get_cache_manager()
    return cache.set(key, value, ttl)


def get_cached_result(key: str) -> Optional[Any]:
    """
    Get a cached result by key.

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found
    """
    cache = get_cache_manager()
    return cache.get(key)


def invalidate_cache(key: str) -> bool:
    """
    Invalidate a cached result.

    Args:
        key: Cache key

    Returns:
        True if successful, False otherwise
    """
    cache = get_cache_manager()
    return cache.delete(key)


def clear_all_cache() -> bool:
    """
    Clear all cached values.

    Returns:
        True if successful, False otherwise
    """
    cache = get_cache_manager()
    return cache.clear()


# Cache key generators for common use cases
def generate_idea_cache_key(idea_id: int) -> str:
    """Generate cache key for idea data."""
    return f"idea:{idea_id}"


def generate_scraper_cache_key(source: str, params: dict) -> str:
    """Generate cache key for scraper results."""
    params_str = json.dumps(params, sort_keys=True)
    return f"scraper:{source}:{hashlib.md5(params_str.encode()).hexdigest()}"


def generate_api_cache_key(endpoint: str, params: dict) -> str:
    """Generate cache key for API responses."""
    params_str = json.dumps(params, sort_keys=True)
    return f"api:{endpoint}:{hashlib.md5(params_str.encode()).hexdigest()}"


def generate_validation_cache_key(keyword: str) -> str:
    """Generate cache key for validation results."""
    return f"validation:{keyword}"