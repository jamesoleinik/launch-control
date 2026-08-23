from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

_TRACER: trace.Tracer | None = None


def configure_telemetry() -> trace.Tracer:
    global _TRACER
    if _TRACER is not None:
        return _TRACER
    provider = TracerProvider(
        resource=Resource.create({
            "service.name": "launch-control-quality-gate",
            "service.namespace": "microsoft-agent-365",
        })
    )
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _TRACER = trace.get_tracer("launch-control.quality-gate")
    return _TRACER


@contextmanager
def assignment_span(
    tracer: trace.Tracer, assignment_key: str
) -> Iterator[trace.Span]:
    with tracer.start_as_current_span("quality_gate.assignment") as span:
        span.set_attribute("launch_control.assignment_key", assignment_key)
        yield span
