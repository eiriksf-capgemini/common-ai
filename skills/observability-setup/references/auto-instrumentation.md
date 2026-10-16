# What OpenTelemetry auto-instrumentation does

Auto-instrumentation means attaching the OpenTelemetry Java agent (or the equivalent for your runtime) to the process, so traces and metrics are produced without code changes. On a managed platform this may be a one-line manifest switch. On plain Kubernetes you enable it yourself; see "How to enable it" below.

## What Auto-Instrumentation Provides

**Automatic Tracing For**:

- HTTP server requests (Ktor, Spring Boot)
- HTTP client requests (Ktor client, OkHttp)
- Database queries (JDBC, PostgreSQL driver)
- Kafka producer/consumer
- Redis/Valkey operations

**Automatic Metrics**:

- JVM metrics (heap, GC, threads)
- HTTP request metrics
- Database connection pool metrics

**No Code Changes Required** for basic instrumentation.

## How to enable it

**Option A: OpenTelemetry Operator (recommended on Kubernetes).** Install the operator, create an `Instrumentation` resource pointing at your collector, and annotate the workload:

```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: default
spec:
  exporter:
    endpoint: http://otel-collector.observability:4317
  propagators: [tracecontext, baggage]
  sampler:
    type: parentbased_traceidratio
    argument: "1.0"
---
# on the Deployment's pod template
metadata:
  annotations:
    instrumentation.opentelemetry.io/inject-java: "true"   # or inject-nodejs, inject-python, inject-dotnet
```

The operator injects the agent via an init container and sets `OTEL_*` environment variables for you.

**Option B: Bundle the agent in the image.**

```dockerfile
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar /otel/javaagent.jar
ENV JAVA_TOOL_OPTIONS="-javaagent:/otel/javaagent.jar"
ENV OTEL_SERVICE_NAME=my-app
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability:4317
ENV OTEL_EXPORTER_OTLP_PROTOCOL=grpc
```

Either way, the agent needs a reachable **OpenTelemetry Collector** that forwards to your tracing backend (Tempo, Jaeger, Azure Monitor, Datadog). Without a collector, auto-instrumentation produces nothing visible.

## Manual Instrumentation (Advanced)

For custom spans, keep the agent for context propagation and use the API in code (as shown in the main skill). `GlobalOpenTelemetry.getTracer(...)` picks up the agent's SDK automatically. If you run without the agent, you must configure the SDK yourself with `opentelemetry-sdk-extension-autoconfigure`.

## Sensitive Data Masking

Nothing masks data for you unless you configure it:

- **SQL statements**: the Java agent sanitises `db.statement` by default (`otel.instrumentation.common.db-statement-sanitizer.enabled=true`). Do not turn it off.
- **URL paths and query strings with personal data** (national IDs, emails): strip or hash them in the collector with a `transform` or `redaction` processor, or add a `SpanProcessor` in code that rewrites `url.path`.
- **Kafka message keys**: if keys carry identifiers, drop `messaging.kafka.message.key` in the collector.

**Always verify** traces in your tracing backend before go-live to ensure no sensitive data is exposed.

## Noisy Traces (Filter them)

Health checks and metrics scrapes generate a trace per probe. Drop them in the collector:

```yaml
processors:
  filter/health:
    error_mode: ignore
    traces:
      span:
        - 'attributes["url.path"] == "/isalive"'
        - 'attributes["url.path"] == "/isready"'
        - 'attributes["url.path"] == "/metrics"'
        - 'IsMatch(attributes["url.path"], ".*/actuator/.*")'
        - 'IsMatch(attributes["url.path"], ".*/internal/(health|status).*")'
```

Alternatively, exclude them at the agent: `OTEL_INSTRUMENTATION_HTTP_SERVER_... ` options vary by version, so the collector filter is the portable choice.
