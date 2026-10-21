---
name: observability-setup
description: Set up Prometheus metrics, OpenTelemetry tracing and health-check endpoints for Kubernetes-deployed applications
license: MIT
compatibility: Application deployed on Kubernetes with Prometheus and an OpenTelemetry Collector available
metadata:
  domain: observability
  tags: prometheus opentelemetry health metrics kubernetes
---

# Observability Setup Skill

This skill provides patterns for setting up observability in applications deployed to Kubernetes or a similar container platform.

## Prerequisites: what the platform must provide

The code patterns below only produce visible results if the platform around the application is in place. Check these before starting, and tell the user which ones are missing. Managed platforms often provide all of them with a manifest switch; on plain Kubernetes each is a separate installation.

| Need | What must exist | How to check |
|---|---|---|
| **Metrics collection** | A Prometheus (or compatible, e.g. Mimir, Azure Monitor managed Prometheus) that scrapes pods. Scrape config via `ServiceMonitor`/`PodMonitor` (Prometheus Operator) or `prometheus.io/*` pod annotations | `kubectl get servicemonitors -A`, or look for `prometheus.io/scrape` annotations on existing workloads |
| **Trace collection** | An OpenTelemetry Collector reachable from the pod (OTLP on 4317/4318) that exports to a tracing backend (Tempo, Jaeger, Azure Monitor, Datadog) | `kubectl get svc -A \| grep -i otel`; ask for `OTEL_EXPORTER_OTLP_ENDPOINT` |
| **Auto-instrumentation** | The OpenTelemetry Operator with an `Instrumentation` resource, or the Java agent bundled in the image. See [references/auto-instrumentation.md](references/auto-instrumentation.md) | `kubectl get instrumentations -A` |
| **Log shipping** | Something that tails container stdout into Loki, Elasticsearch, or Application Insights (Promtail, Alloy, Fluent Bit, OTel Collector filelog) | `kubectl get ds -A \| grep -iE 'promtail\|alloy\|fluent'` |
| **Dashboards and alerting** | Grafana with the metrics, logs and traces data sources connected. Alertmanager or Grafana Alerting with a route to the team's channel | Open Grafana, check Connections → Data sources |

Application dependencies (Gradle, Kotlin):

```kotlin
implementation("io.ktor:ktor-server-metrics-micrometer:$ktorVersion")
implementation("io.micrometer:micrometer-registry-prometheus:$micrometerVersion")
implementation("io.opentelemetry:opentelemetry-api:$otelVersion")        // manual spans only; the agent provides the SDK
implementation("net.logstash.logback:logstash-logback-encoder:$logstashVersion")
implementation("io.github.oshai:kotlin-logging-jvm:$kotlinLoggingVersion")
```

On AKS with the **Azure Monitor managed Prometheus** add-on, the metrics and dashboard rows look different (annotation scraping per allow-listed namespace, `azmonitoring.coreos.com` CRDs, no `PrometheusRule`, portal Grafana): see [references/azure-monitor-managed-prometheus.md](references/azure-monitor-managed-prometheus.md) before writing any monitor or rule objects.

If none of the platform pieces exist, the quickest local setup for development is the Grafana LGTM all-in-one image (`docker run -p 3000:3000 -p 4317:4317 -p 4318:4318 grafana/otel-lgtm`), which bundles Grafana, Loki, Tempo, Mimir and a collector.

## Required Health Endpoints

The paths `/healthz` and `/readyz` are a convention; any pair works as long as the Kubernetes probes use the same paths.

```kotlin
import io.ktor.server.application.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import io.ktor.http.*

fun Application.configureHealthEndpoints(
    dataSource: HikariDataSource,
    kafkaProducer: KafkaProducer<String, String>
) {
    routing {
        get("/healthz") {
            call.respondText("Alive", ContentType.Text.Plain)
        }

        get("/readyz") {
            val databaseHealthy = checkDatabase(dataSource)
            val kafkaHealthy = checkKafka(kafkaProducer)

            if (databaseHealthy && kafkaHealthy) {
                call.respondText("Ready", ContentType.Text.Plain)
            } else {
                call.respondText(
                    "Not ready",
                    ContentType.Text.Plain,
                    HttpStatusCode.ServiceUnavailable
                )
            }
        }
    }
}

fun checkDatabase(dataSource: HikariDataSource): Boolean {
    return try {
        dataSource.connection.use { it.isValid(1) }
    } catch (e: Exception) {
        false
    }
}

fun checkKafka(producer: KafkaProducer<String, String>): Boolean {
    return try {
        producer.partitionsFor("health-check-topic").isNotEmpty()
    } catch (e: Exception) {
        false
    }
}
```

## Prometheus Metrics Setup

```kotlin
import io.micrometer.core.instrument.Clock
import io.micrometer.core.instrument.binder.jvm.*
import io.micrometer.prometheus.PrometheusConfig
import io.micrometer.prometheus.PrometheusMeterRegistry
import io.prometheus.client.CollectorRegistry
import io.ktor.server.metrics.micrometer.*
import io.ktor.server.response.*
import io.ktor.http.*

val meterRegistry = PrometheusMeterRegistry(
    PrometheusConfig.DEFAULT,
    CollectorRegistry.defaultRegistry,
    Clock.SYSTEM
)

fun Application.configureMetrics() {
    install(MicrometerMetrics) {
        registry = meterRegistry
        meterBinders = listOf(
            JvmMemoryMetrics(),        // Heap, non-heap memory
            JvmGcMetrics(),            // Garbage collection
            ProcessorMetrics(),        // CPU usage
            UptimeMetrics()            // Application uptime
        )
    }

    routing {
        get("/metrics") {
            call.respondText(
                meterRegistry.scrape(),
                ContentType.parse("text/plain; version=0.0.4")
            )
        }
    }
}
```

## Business Metrics

```kotlin
import io.micrometer.core.instrument.Counter
import io.micrometer.core.instrument.Timer

class UserService(private val meterRegistry: PrometheusMeterRegistry) {
    private val userCreatedCounter = Counter.builder("users_created_total")
        .description("Total users created")
        .register(meterRegistry)

    private val userCreationTimer = Timer.builder("user_creation_duration_seconds")
        .description("User creation duration")
        .register(meterRegistry)

    fun createUser(user: User) {
        userCreationTimer.record {
            repository.save(user)
        }
        userCreatedCounter.increment()
    }
}
```

## OpenTelemetry Tracing

With the OpenTelemetry agent attached (see Prerequisites), HTTP, JDBC and Kafka are traced automatically. For manual spans:

```kotlin
import io.opentelemetry.api.GlobalOpenTelemetry
import io.opentelemetry.api.trace.Span
import io.opentelemetry.api.trace.StatusCode

val tracer = GlobalOpenTelemetry.getTracer("my-app")

fun processPayment(paymentId: String) {
    val span = tracer.spanBuilder("processPayment")
        .setAttribute("payment.id", paymentId)
        .startSpan()

    try {
        // Business logic
        val payment = repository.findPayment(paymentId)
        span.setAttribute("payment.amount", payment.amount)

        processPaymentInternal(payment)
        span.setStatus(StatusCode.OK)
    } catch (e: Exception) {
        span.setStatus(StatusCode.ERROR, "Payment processing failed")
        span.recordException(e)
        throw e
    } finally {
        span.end()
    }
}
```

## Structured Logging

```kotlin
import mu.KotlinLogging
import net.logstash.logback.argument.StructuredArguments.kv

private val logger = KotlinLogging.logger {}

fun processOrder(orderId: String) {
    logger.info(
        "Processing order",
        kv("order_id", orderId),
        kv("timestamp", LocalDateTime.now())
    )

    try {
        orderService.process(orderId)

        logger.info(
            "Order processed successfully",
            kv("order_id", orderId)
        )
    } catch (e: Exception) {
        logger.error(
            "Order processing failed",
            kv("order_id", orderId),
            kv("error", e.message),
            e
        )
        throw e
    }
}
```

## Kubernetes Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: myteam
  labels:
    app: my-app
    team: myteam
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
        team: myteam
      annotations:
        # Prometheus scraping (annotation style; use a PodMonitor if you run the Prometheus Operator)
        prometheus.io/scrape: "true"
        prometheus.io/path: /metrics
        prometheus.io/port: "8080"
        # OpenTelemetry Operator auto-instrumentation
        instrumentation.opentelemetry.io/inject-java: "true"
    spec:
      containers:
        - name: my-app
          image: ghcr.io/{org}/my-app:latest
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: OTEL_SERVICE_NAME
              value: my-app
            # OTEL_EXPORTER_OTLP_ENDPOINT is set by the operator; set it explicitly if you bundle the agent yourself
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 1
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 1
            failureThreshold: 3
          resources:
            requests:
              cpu: 50m
              memory: 256Mi
            limits:
              memory: 512Mi
```

If you run the Prometheus Operator, add a `PodMonitor` instead of relying on annotations. Check that the CRD exists first (`kubectl get crd podmonitors.monitoring.coreos.com`); on Azure managed Prometheus the group is `azmonitoring.coreos.com/v1` and annotations are usually enough (see the Azure reference):

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: my-app
  namespace: myteam
spec:
  selector:
    matchLabels:
      app: my-app
  podMetricsEndpoints:
    - port: http
      path: /metrics
```

Logs go to stdout as JSON. The platform's log shipper, where one exists, picks them up; the application never writes log files. On AKS with only the managed Prometheus add-on there is no shipper and `kubectl logs` is the log store (see the Azure reference).

## Alert Configuration

With the Prometheus Operator, alerts are `PrometheusRule` resources. Routing to a chat channel is done in Alertmanager (or Grafana Alerting), not in the rule. There is no `PrometheusRule` CRD on Azure managed Prometheus; the same expressions go into an Azure `prometheusRuleGroups` resource in the platform's OpenTofu (see the Azure reference).

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: my-app-alerts
  namespace: myteam
  labels:
    team: myteam
spec:
  groups:
    - name: my-app
      rules:
        - alert: HighErrorRate
          expr: |
            (sum(rate(http_requests_total{app="my-app",status=~"5.."}[5m]))
            / sum(rate(http_requests_total{app="my-app"}[5m]))) > 0.05
          for: 5m
          labels:
            severity: critical
            team: myteam
          annotations:
            summary: "Error rate is {{ $value | humanizePercentage }}"
            action: "Check logs in Grafana"
            runbook_url: https://teamdocs/runbooks/high-error-rate

        - alert: HighResponseTime
          expr: |
            histogram_quantile(0.95,
              rate(http_request_duration_seconds_bucket{app="my-app"}[5m])
            ) > 1
          for: 10m
          labels:
            severity: warning
            team: myteam
          annotations:
            summary: "95th percentile response time is {{ $value }}s"
            action: "Check traces for slow requests"

        - alert: PodCrashLooping
          expr: |
            rate(kube_pod_container_status_restarts_total{
              pod=~"my-app-.*"
            }[15m]) > 0
          for: 5m
          labels:
            severity: critical
            team: myteam
          annotations:
            summary: "Pod {{ $labels.pod }} is crash looping"
            action: "Check logs: kubectl logs {{ $labels.pod }}"

        - alert: HighMemoryUsage
          expr: |
            (container_memory_working_set_bytes{app="my-app"}
            / container_spec_memory_limit_bytes{app="my-app"}) > 0.9
          for: 10m
          labels:
            severity: warning
            team: myteam
          annotations:
            summary: "Memory usage is {{ $value | humanizePercentage }}"
            action: "Check for memory leaks, increase limits if needed"
```

Alertmanager route example, so `team: myteam` lands in the team's channel:

```yaml
route:
  routes:
    - matchers: [team="myteam"]
      receiver: myteam-chat
receivers:
  - name: myteam-chat
    slack_configs:            # or msteams_configs / webhook_configs
      - channel: "#myteam-alerts"
        api_url: ${SLACK_WEBHOOK_URL}
```

## Complete Example

```kotlin
import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.micrometer.core.instrument.Timer
import io.opentelemetry.api.GlobalOpenTelemetry
import io.opentelemetry.api.trace.StatusCode

fun main() {
    val env = Environment.from(System.getenv())
    val dataSource = createDataSource(env.databaseUrl)

    // Run database migrations
    runMigrations(dataSource)

    val kafkaProducer = createKafkaProducer(env.kafkaBrokers)

    embeddedServer(Netty, port = 8080) {
        configureHealthEndpoints(dataSource, kafkaProducer)
        configureMetrics()  // uses the top-level meterRegistry
        configureRouting(dataSource, meterRegistry)
    }.start(wait = true)
}

fun Application.configureRouting(
    dataSource: HikariDataSource,
    meterRegistry: PrometheusMeterRegistry
) {
    val tracer = GlobalOpenTelemetry.getTracer("my-app")

    routing {
        get("/api/users") {
            val requestTimer = Timer.sample()
            val requestCounter = meterRegistry.counter(
                "http_requests_total",
                "method", "GET",
                "endpoint", "/api/users"
            )

            val span = tracer.spanBuilder("getUsersRequest")
                .setAttribute("http.method", "GET")
                .setAttribute("http.route", "/api/users")
                .startSpan()

            try {
                val users = userRepository.findAll()
                span.setAttribute("user.count", users.size.toLong())
                span.setStatus(StatusCode.OK)

                requestCounter.increment()
                requestTimer.stop(meterRegistry.timer(
                    "http_request_duration_seconds",
                    "method", "GET",
                    "endpoint", "/api/users",
                    "status", "200"
                ))

                call.respond(users)
            } catch (e: Exception) {
                span.setStatus(StatusCode.ERROR, "Failed to get users")
                span.recordException(e)

                meterRegistry.counter(
                    "http_requests_total",
                    "method", "GET",
                    "endpoint", "/api/users",
                    "status", "500"
                ).increment()

                // trace_id and span_id are auto-injected into MDC by OTel agent
                logger.error("Failed to get users", e)

                throw e
            } finally {
                span.end()
            }
        }
    }
}
```

## Grafana & Loki & Tempo Queries

See [references/grafana-queries.md](references/grafana-queries.md) for PromQL dashboard panels, LogQL query examples, and Tempo trace search patterns.

## Monitoring Checklist

- [ ] `/healthz` endpoint implemented
- [ ] `/readyz` endpoint with dependency checks (database, Kafka)
- [ ] `/metrics` endpoint exposing Prometheus metrics
- [ ] Liveness and readiness probes configured in the Deployment
- [ ] Business metrics instrumented (counters, timers, gauges)
- [ ] Verify trace_id appears in logs (auto-injected by OTel agent via MDC)
- [ ] OpenTelemetry agent attached (operator annotation or bundled) and collector endpoint reachable
- [ ] Alert rules created as `PrometheusRule` (or in Grafana Alerting)
- [ ] Alertmanager route sends the team's alerts to its chat channel
- [ ] Grafana dashboard created
- [ ] No sensitive data in logs or metrics (verify in Grafana)
- [ ] High-cardinality labels avoided (no user_ids, transaction_ids)
- [ ] Metric names are snake_case with unit suffix, counters end in `_total`
- [ ] Label values are bounded (no free-text, no unbounded ids)
- [ ] Logs go to stdout as JSON, never to files

## Production Patterns & DORA Metrics

See [references/production-patterns.md](references/production-patterns.md) for production metric patterns and DORA metric implementation examples.

## More references

- [references/metric-conventions.md](references/metric-conventions.md): Prometheus naming rules (snake_case, unit suffixes, `_total`), label cardinality rules, and the Gauge and Histogram patterns.
- [references/tracing-and-logging.md](references/tracing-and-logging.md): trace context propagation (W3C, Kafka headers, DB), log levels, logging practice, and fixing broken log-to-trace correlation.
- [references/auto-instrumentation.md](references/auto-instrumentation.md): what the OpenTelemetry agent covers, how to enable it on Kubernetes, sensitive-data masking, and filtering noisy health-check traces.
- [references/alerting.md](references/alerting.md): raw Prometheus alert-rule schema, alerting practice, and a common alert catalogue (availability, memory, DB pool, Kafka lag, DORA).
- [references/typescript.md](references/typescript.md): Grafana Faro for frontends and `prom-client` metrics in Next.js API routes.
- [references/azure-monitor-managed-prometheus.md](references/azure-monitor-managed-prometheus.md): what differs on AKS with the managed add-on: annotation scraping per namespace allow-list, `azmonitoring.coreos.com` monitors, rule groups as Azure resources, portal Grafana, per-sample cost.
