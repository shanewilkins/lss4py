from typing import Final

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

DEFAULT_SERVICE_NAME: Final[str] = "lss4py"


def configure_telemetry(service_name: str = DEFAULT_SERVICE_NAME) -> None:
    """Install a tracer provider with batched console export for the named service."""
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


def get_tracer(name: str = DEFAULT_SERVICE_NAME):
    """Return a tracer for the named instrumentation scope."""
    return trace.get_tracer(name)
