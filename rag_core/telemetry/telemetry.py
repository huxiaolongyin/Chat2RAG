from openinference.instrumentation.haystack import HaystackInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
import socket
import subprocess
import sys


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def ensure_telemetry_server():
    """查看是否存在 telemetry 服务，不存在则启动"""
    if not is_port_in_use(6006):
        python_executable = sys.executable
        server_command = [python_executable, "-m", "phoenix.server.main", "serve"]
        subprocess.Popen(server_command, start_new_session=True)


def setup_telemetry():
    ensure_telemetry_server()
    endpoint = "http://localhost:6006/v1/traces"
    tracer_provider = trace_sdk.TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))
    HaystackInstrumentor().instrument(tracer_provider=tracer_provider)
