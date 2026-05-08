"""
Retry logic and rate limiting utilities for IdeaHunter.
Provides exponential backoff, circuit breaker pattern, and rate limiting.
"""

import time
import random
from functools import wraps
from typing import Callable, Optional, Type, Tuple
from backend.utils.logging_config import get_logger

log = get_logger(__name__)


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []

    def acquire(self) -> bool:
        """
        Try to acquire a token.

        Returns:
            True if token acquired, False if rate limit exceeded
        """
        now = time.time()

        # Remove old calls outside time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

        # Check if we can make a call
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True

        return False

    def wait_time(self) -> float:
        """
        Get time to wait before next call.

        Returns:
            Seconds to wait before next call can be made
        """
        if not self.calls:
            return 0.0

        oldest_call = min(self.calls)
        return max(0.0, self.time_window - (time.time() - oldest_call))


class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result or raises CircuitBreakerOpenError
        """
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                log.info("Circuit breaker entering half-open state")
                self.state = 'half-open'
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            # Success - reset failure count and close circuit
            if self.state == 'half-open':
                log.info("Circuit breaker closing after successful call")
                self.state = 'closed'
            self.failure_count = 0
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                log.error(f"Circuit breaker opening after {self.failure_count} failures")
                self.state = 'open'

            raise


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delay
        retry_exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    if retry_exceptions and not isinstance(e, retry_exceptions):
                        raise

                    # Don't retry on last attempt
                    if attempt == max_retries:
                        log.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter if enabled
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    log.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                               f"retrying in {delay:.2f}s: {e}")

                    time.sleep(delay)

            # This should never be reached, but just in case
            raise last_exception

        return wrapper
    return decorator


def rate_limited(max_calls: int, time_window: float):
    """
    Decorator for rate limiting function calls.

    Args:
        max_calls: Maximum number of calls in time window
        time_window: Time window in seconds
    """
    def decorator(func: Callable):
        rate_limiter = RateLimiter(max_calls, time_window)

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not rate_limiter.acquire():
                wait_time = rate_limiter.wait_time()
                log.warning(f"Rate limit exceeded for {func.__name__}, waiting {wait_time:.2f}s")
                time.sleep(wait_time)

                # Try again after waiting
                if not rate_limiter.acquire():
                    raise RateLimitExceededError(f"Rate limit exceeded for {func.__name__}")

            return func(*args, **kwargs)

        return wrapper
    return decorator


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


# Pre-configured rate limiters for common APIs
REDDIT_RATE_LIMITER = RateLimiter(max_calls=60, time_window=60.0)  # 60 calls per minute
GOOGLE_TRENDS_RATE_LIMITER = RateLimiter(max_calls=30, time_window=60.0)  # 30 calls per minute
SERPAPI_RATE_LIMITER = RateLimiter(max_calls=100, time_window=3600.0)  # 100 calls per hour
PRODUCTHUNT_RATE_LIMITER = RateLimiter(max_calls=50, time_window=60.0)  # 50 calls per minute
HACKERNEWS_RATE_LIMITER = RateLimiter(max_calls=1000, time_window=60.0)  # 1000 calls per minute