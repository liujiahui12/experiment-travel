import hashlib
import json
import time
from typing import Any, Optional
from functools import wraps


class CacheManager:
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @staticmethod
    def _generate_key(*args, **kwargs) -> str:
        key_data = f"{args}_{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            cached_data = self._cache[key]
            if time.time() < cached_data['expires_at']:
                return cached_data['data']
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, data: Any, ttl: int = 3600) -> None:
        self._cache[key] = {
            'data': data,
            'expires_at': time.time() + ttl
        }
    
    def clear(self) -> None:
        self._cache.clear()
    
    def cached(self, ttl: int = 3600):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = self._generate_key(func.__name__, *args, **kwargs)
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
