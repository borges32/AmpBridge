"""OpenTelemetry tracing setup."""

import logging
from typing import Optional

from app.settings import settings

logger = logging.getLogger(__name__)

# Global tracer instance
tracer = None


def setup_tracing() -> bool:
    """Setup OpenTelemetry tracing if configured.
    
    Returns:
        True if tracing was set up, False otherwise
    """
    global tracer
    
    if not settings.otlp_endpoint:
        logger.info("OTLP endpoint not configured, skipping tracing setup")
        return False
    
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        
        # Create resource
        resource = Resource.create({
            "service.name": "opamp-backend",
            "service.version": "1.0.0",
            "service.environment": settings.app_env
        })
        
        # Setup tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Setup OTLP exporter
        headers = {}
        if settings.otlp_headers:
            for header in settings.otlp_headers.split(','):
                if '=' in header:
                    key, value = header.split('=', 1)
                    headers[key.strip()] = value.strip()
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otlp_endpoint,
            headers=headers
        )
        
        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Get tracer
        tracer = trace.get_tracer(__name__)
        
        # Instrument libraries
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        
        logger.info(f"OpenTelemetry tracing initialized with endpoint: {settings.otlp_endpoint}")
        return True
        
    except ImportError as e:
        logger.warning(f"OpenTelemetry dependencies not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry tracing: {e}")
        return False


def get_tracer():
    """Get the global tracer instance.
    
    Returns:
        Tracer instance or None if not initialized
    """
    return tracer


def trace_function(operation_name: str):
    """Decorator to trace function execution.
    
    Args:
        operation_name: Name of the operation for the span
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if tracer:
                with tracer.start_as_current_span(operation_name):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator