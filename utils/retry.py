import time
import functools
from typing import Callable, Any


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e
                    
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    time.sleep(delay)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
