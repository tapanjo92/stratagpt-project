"""
Common utilities and decorators for Lambda functions using AWS Lambda Powertools
"""
import os
import json
from typing import Any, Dict, Callable
from functools import wraps
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.tracing import capture_method
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize Powertools
logger = Logger(service="strata-ingestion")
tracer = Tracer(service="strata-ingestion")
metrics = Metrics(namespace="StrataGPT/Ingestion", service="ingestion")

class IngestionError(Exception):
    """Base exception for ingestion pipeline errors"""
    pass

class TextractError(IngestionError):
    """Textract processing errors"""
    pass

class ChunkingError(IngestionError):
    """Document chunking errors"""
    pass

class EmbeddingError(IngestionError):
    """Embedding generation errors"""
    pass

class IndexingError(IngestionError):
    """OpenSearch indexing errors"""
    pass

def lambda_handler_decorator(handler_func: Callable) -> Callable:
    """
    Decorator that adds standard error handling, logging, and metrics to Lambda handlers
    """
    @wraps(handler_func)
    @logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
    @tracer.capture_lambda_handler
    @metrics.log_metrics(capture_cold_start_metric=True)
    def wrapper(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
        try:
            # Log event
            logger.info("Lambda invoked", extra={"event": event})
            
            # Add custom metric
            metrics.add_metric(name="Invocations", unit=MetricUnit.Count, value=1)
            
            # Call the actual handler
            result = handler_func(event, context)
            
            # Log success
            logger.info("Lambda completed successfully", extra={"result": result})
            
            # Add success metric
            metrics.add_metric(name="Success", unit=MetricUnit.Count, value=1)
            
            return result
            
        except IngestionError as e:
            # Known errors - log as warning
            logger.warning(f"Ingestion error: {str(e)}", exc_info=True)
            metrics.add_metric(name="BusinessErrors", unit=MetricUnit.Count, value=1)
            
            return {
                'statusCode': 400,
                'error': str(e),
                'errorType': type(e).__name__
            }
            
        except Exception as e:
            # Unknown errors - log as error
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            metrics.add_metric(name="SystemErrors", unit=MetricUnit.Count, value=1)
            
            # Re-raise to trigger Lambda retry
            raise
    
    return wrapper

@capture_method
def validate_event(event: Dict[str, Any], required_fields: list) -> None:
    """
    Validate that required fields are present in the event
    """
    missing_fields = [field for field in required_fields if field not in event]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

@capture_method
def emit_metric(metric_name: str, value: float = 1, unit: MetricUnit = MetricUnit.Count) -> None:
    """
    Emit a custom CloudWatch metric
    """
    metrics.add_metric(name=metric_name, unit=unit, value=value)

@capture_method
def log_performance(operation: str, duration_ms: float) -> None:
    """
    Log performance metrics
    """
    logger.info(f"Performance: {operation}", extra={
        "operation": operation,
        "duration_ms": duration_ms
    })
    
    metrics.add_metric(
        name=f"{operation}Duration",
        unit=MetricUnit.Milliseconds,
        value=duration_ms
    )

class RetryHandler:
    """
    Exponential backoff retry handler
    """
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Retry a function with exponential backoff
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s", extra={
                        "error": str(e),
                        "attempt": attempt + 1
                    })
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed", extra={
                        "error": str(e)
                    })
        
        raise last_exception

# Export commonly used functions
__all__ = [
    'logger',
    'tracer',
    'metrics',
    'lambda_handler_decorator',
    'validate_event',
    'emit_metric',
    'log_performance',
    'RetryHandler',
    'IngestionError',
    'TextractError',
    'ChunkingError',
    'EmbeddingError',
    'IndexingError'
]