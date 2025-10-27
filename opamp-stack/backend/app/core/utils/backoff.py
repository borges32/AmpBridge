"""Exponential backoff utilities for retry logic."""

import random
from typing import Union


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """Calculate exponential backoff delay with optional jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
        
    Returns:
        Delay in seconds
    """
    # Calculate exponential delay: base_delay * (2 ^ attempt)
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    # Add jitter to avoid thundering herd
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay


def linear_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    increment: float = 1.0
) -> float:
    """Calculate linear backoff delay.
    
    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        increment: Delay increment per attempt
        
    Returns:
        Delay in seconds
    """
    delay = base_delay + (attempt * increment)
    return min(delay, max_delay)


def fibonacci_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> float:
    """Calculate Fibonacci backoff delay.
    
    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Delay in seconds
    """
    def fibonacci(n: int) -> int:
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    delay = base_delay * fibonacci(attempt)
    return min(delay, max_delay)