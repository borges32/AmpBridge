"""Prometheus metrics for the application."""

import time
from typing import Dict, Any
from functools import wraps

from prometheus_client import (
    Counter, Histogram, Gauge, Info, 
    generate_latest, CONTENT_TYPE_LATEST
)

# Application info
APP_INFO = Info('opamp_backend_info', 'OpAMP Backend application info')
APP_INFO.info({
    'version': '1.0.0',
    'name': 'opamp-backend'
})

# Agent metrics
AGENTS_TOTAL = Gauge(
    'opamp_agents_total',
    'Total number of agents',
    ['environment', 'status']
)

AGENT_LAST_SEEN = Histogram(
    'opamp_agent_last_seen_seconds',
    'Time since agent was last seen',
    ['environment', 'agent_id'],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400, 28800, 86400]
)

# Configuration metrics
CONFIG_APPLY_TOTAL = Counter(
    'opamp_config_apply_total',
    'Total configuration applications',
    ['agent_id', 'status']
)

CONFIG_APPLY_DURATION = Histogram(
    'opamp_config_apply_duration_seconds',
    'Time spent applying configurations',
    ['agent_id'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Job metrics
JOB_TOTAL = Counter(
    'opamp_job_total',
    'Total number of jobs',
    ['type', 'status']
)

JOB_DURATION = Histogram(
    'opamp_job_duration_seconds',
    'Job execution duration',
    ['type', 'status'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

JOB_PROGRESS = Gauge(
    'opamp_job_progress_percent',
    'Current job progress percentage',
    ['job_id', 'type']
)

BULK_APPLY_SUCCESS_TOTAL = Counter(
    'opamp_bulk_apply_success_total',
    'Total successful bulk configuration applications'
)

BULK_APPLY_FAIL_TOTAL = Counter(
    'opamp_bulk_apply_fail_total',
    'Total failed bulk configuration applications'
)

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# OpAMP client metrics
OPAMP_REQUESTS_TOTAL = Counter(
    'opamp_client_requests_total',
    'Total OpAMP client requests',
    ['endpoint', 'status']
)

OPAMP_REQUEST_DURATION = Histogram(
    'opamp_client_request_duration_seconds',
    'OpAMP client request duration',
    ['endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Authentication metrics
AUTH_ATTEMPTS_TOTAL = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['status']
)

AUTH_TOKEN_ISSUED_TOTAL = Counter(
    'auth_token_issued_total',
    'Total JWT tokens issued'
)

# Database metrics
DB_CONNECTIONS = Gauge(
    'db_connections_active',
    'Active database connections'
)

DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)


def track_time(metric: Histogram, labels: Dict[str, str] = None):
    """Decorator to track execution time with a histogram metric.
    
    Args:
        metric: Prometheus histogram metric
        labels: Optional labels dictionary
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        return async_wrapper if hasattr(func, '__await__') else sync_wrapper
    return decorator


def increment_counter(metric: Counter, labels: Dict[str, str] = None):
    """Increment a counter metric with optional labels.
    
    Args:
        metric: Prometheus counter metric
        labels: Optional labels dictionary
    """
    if labels:
        metric.labels(**labels).inc()
    else:
        metric.inc()


def set_gauge(metric: Gauge, value: float, labels: Dict[str, str] = None):
    """Set a gauge metric value with optional labels.
    
    Args:
        metric: Prometheus gauge metric
        value: Value to set
        labels: Optional labels dictionary
    """
    if labels:
        metric.labels(**labels).set(value)
    else:
        metric.set(value)


def get_metrics() -> str:
    """Get all metrics in Prometheus text format.
    
    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest()


def get_content_type() -> str:
    """Get the content type for Prometheus metrics.
    
    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST