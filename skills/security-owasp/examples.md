# OWASP Top 10:2025 — examples

Reference snippets for Kotlin, Go, Java (Spring Boot), and Node.js / Next.js.

Each subsection shows a short ❌ anti-pattern and a matching ✅ correct pattern.

## A01: Broken Access Control (incl. SSRF)

### Kotlin

```kotlin
// ❌ IDOR — trusts caller-supplied id
val order = orderRepository.findById(call.parameters["id"]!!.toLong())
call.respond(order)

// ✅ Verify resource ownership before returning data
val user = call.getUser()
val order = orderRepository.findById(call.parameters["id"]!!.toLong()) ?: return@get call.respond(HttpStatusCode.NotFound)
if (order.userId != user.id) return@get call.respond(HttpStatusCode.Forbidden)
call.respond(order.toDTO())
```

### Go

```go
// ❌ SSRF — fetches user-supplied URL directly
resp, _ := http.Get(r.URL.Query().Get("url"))

// ✅ Allowlist host and require HTTPS
u, err := url.Parse(r.URL.Query().Get("url"))
if err != nil || u.Scheme != "https" || !allowedHosts[u.Hostname()] {
http.Error(w, "host not allowed", http.StatusForbidden)
return
}
resp, _ := http.Get(u.String())
```

### Java (Spring Boot)

```java
// ❌ Authenticated user can read any order by id
@GetMapping("/api/orders/{id}")
OrderDto get(@PathVariable Long id) { return service.get(id); }

// ✅ Enforce access at method boundary
@GetMapping("/api/orders/{id}")
@PreAuthorize("@orderAuth.canRead(#id, authentication)")
OrderDto get(@PathVariable Long id) { return service.get(id); }
```

### Node.js / Next.js

```ts
// ❌ Route handler trusts caseId from query string
export async function GET(req: NextRequest) {
  return Response.json(await getOrder(req.nextUrl.searchParams.get("caseId")!))
}

// ✅ Scope lookup to authenticated user
export async function GET() {
  const session = await requireSession()
  return Response.json(await getOrdersForUser(session.userId))
}
```

### Patterns

- Verify ownership and scope on every resource, not only at login.
- Deny by default when authorization data is missing or ambiguous.
- For SSRF, allowlist outbound hosts, require HTTPS, and block loopback and metadata addresses.
- For M2M tokens, validate `azp` against pre-authorized apps.

## A02: Security Misconfiguration

### Kotlin

```kotlin
// ❌ Open CORS in production
install(CORS) { anyHost() }

// ✅ Restrict origins explicitly
install(CORS) {
    allowHost("my-app.example.com", schemes = listOf("https"))
}
```

### Go

```go
// ❌ Debug endpoint on public listener
mux.HandleFunc("/debug/pprof/", pprof.Index)

// ✅ Debug endpoint on internal-only listener
internalMux := http.NewServeMux()
internalMux.HandleFunc("/debug/pprof/", pprof.Index)
go http.ListenAndServe("127.0.0.1:9090", internalMux)
```

### Java (Spring Boot)

```java
// ❌ Wildcard CORS on controller
@CrossOrigin(origins = "*")
@RestController class OrderController {}

// ✅ Restrictive CORS via Spring Security
cfg.setAllowedOrigins(List.of("https://my-app.example.com"));
cfg.setAllowedMethods(List.of("GET", "POST"));
source.registerCorsConfiguration("/**", cfg);
```

### Node.js / Next.js

```ts
// ❌ Over-broad Server Actions config
serverActions: { allowedOrigins: ["*"], bodySizeLimit: "20mb" }

// ✅ Same-origin by default, add only trusted proxies when needed
serverActions: { allowedOrigins: ["my-proxy.example.com"], bodySizeLimit: "1mb" }
```

### Patterns

- Restrict CORS to known origins, methods, and headers.
- Keep debug and admin endpoints off public ingress.
- Disable development-only features in production.
- Return generic client errors; keep stack traces and SQL errors in logs only.

## A03: Software Supply Chain Failures

### Kotlin

```kotlin
// ❌ Floating dependency versions
implementation("org.postgresql:postgresql:+")

// ✅ Pin and lock dependencies
implementation("org.postgresql:postgresql:42.7.5")
dependencyLocking { lockAllConfigurations() }
```

### Go

```go
// ❌ Missing verification step in CI
// go test ./...

// ✅ Verify integrity and known vulnerabilities
// go mod verify
// govulncheck ./...
```

### Java (Spring Boot)

```xml
<!-- ❌ Floating ranges in pom.xml -->
<version>[5.8,)</version>

<!-- ✅ Pin exact version and keep lockfile/BOM updated -->
<version>5.8.16</version>
```

### Node.js / Next.js

```json
// ❌ Floating dependency range
"next": "^16.0.0"

// ✅ Pin version and commit lockfile
"next": "16.0.0"
```

### Patterns

- Pin dependencies and commit lockfiles (`go.sum`, `gradle.lockfile`, `package-lock.json` or `pnpm-lock.yaml`).
- Scan dependencies regularly with `govulncheck`, `npm audit`, Trivy, or equivalent CI checks.
- Pin GitHub Actions to full commit SHA, not tags or branches.
- Prefer maintained, first-party packages over abandoned wrappers.

## A04: Cryptographic Failures

### Kotlin

```kotlin
// ❌ Weak password hashing
val hash = MessageDigest.getInstance("MD5").digest(password.toByteArray())

// ✅ bcrypt for passwords
val hashed = BCrypt.hashpw(password, BCrypt.gensalt(12))
```

### Go

```go
// ❌ TLS verification disabled
client := &http.Client{Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}}}

// ✅ Use default TLS verification
client := &http.Client{}
```

### Java (Spring Boot)

```java
// ❌ Hardcoded secret and reversible password storage
String signingKey = "secret";
String stored = password;

// ✅ Secret from env and adaptive password hashing
String signingKey = env.getRequiredProperty("JWT_SIGNING_KEY");
String stored = passwordEncoder.encode(password);
```

### Node.js / Next.js

```ts
// ❌ Weak hash and hardcoded secret
const hash = createHash("sha1").update(password).digest("hex")
const jwtSecret = "secret"

// ✅ Use scrypt/bcrypt and env-managed secret
const hash = await scryptHash(password)
const jwtSecret = process.env.JWT_SECRET!
```

### Patterns

- Use bcrypt or argon2id for passwords, never MD5 or SHA-only hashes.
- Keep secrets in environment variables or a secret store, never in source.
- Require modern TLS and never set `InsecureSkipVerify: true`.
- Prefer authenticated encryption such as AES-256-GCM when you encrypt application data.

## A05: Injection

### Kotlin

```kotlin
// ❌ SQL injection via string interpolation
queryOf("SELECT * FROM order WHERE status = '$status'")

// ✅ Parameterized query
queryOf("SELECT * FROM order WHERE status = ?", status)
```

### Go

```go
// ❌ Shell injection via sh -c
exec.Command("sh", "-c", fmt.Sprintf("journalctl -u %s", service)).Run()

// ✅ Pass arguments directly
exec.Command("journalctl", "-u", service).Run()
```

### Java (Spring Boot)

```java
// ❌ SQL injection in JdbcTemplate
jdbcTemplate.query("SELECT * FROM order WHERE nationalId = '" + nationalId + "'", rowMapper);

// ✅ Prepared parameters in JdbcTemplate
jdbcTemplate.query("SELECT * FROM order WHERE nationalId = ?", rowMapper, nationalId);
```

### Node.js / Next.js

```ts
// ❌ Raw SQL and unsanitized user HTML
await prisma.$queryRawUnsafe(`SELECT * FROM order WHERE nationalId = '${nationalId}'`)
return <div dangerouslySetInnerHTML={{ __html: kommentar }} />

// ✅ Parameterize SQL and sanitize rendered content
await prisma.$queryRaw`SELECT * FROM order WHERE nationalId = ${nationalId}`
return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(kommentar) }} />
```

### Patterns

- Parameterize all SQL queries; never build SQL with string concatenation.
- Avoid shell execution for user-controlled data.
- Validate input at the boundary before it reaches template, shell, or database code.
- Treat user input as data, never as code or template source.

## A06: Insecure Design

### Kotlin

```kotlin
// ❌ Business rule missing — negative amount accepted
fun createOrder(amount: BigDecimal) = orderService.create(amount)

// ✅ Enforce domain rules before state changes
fun createOrder(amount: BigDecimal): Order {
    require(amount > BigDecimal.ZERO) { "Amount must be positive" }
    return orderService.create(amount)
}
```

### Go

```go
// ❌ No rate limiting on login
http.HandleFunc("/api/login", handleLogin)

// ✅ Rate limit sensitive endpoints
http.Handle("/api/login", rateLimitMiddleware(limiter, http.HandlerFunc(handleLogin)))
```

### Java (Spring Boot)

```java
// ❌ No validation of request body
public ResponseEntity<?> create(@RequestBody OrderRequest req) { return ok(service.create(req)); }

// ✅ Validate shape early and enforce business rules in service
public ResponseEntity<?> create(@RequestBody @Valid OrderRequest req) { return ok(service.create(req)); }
```

### Node.js / Next.js

```ts
// ❌ Server Action trusts raw form data
export async function createOrder(_: unknown, formData: FormData) { return save(formData.get("amount")) }

// ✅ Validate input before mutation
export async function createOrder(_: unknown, formData: FormData) {
  const data = schema.parse({ amount: Number(formData.get("amount")) })
  return save(data.amount)
}
```

### Patterns

- Validate input shape at the boundary, then enforce business rules in the domain layer.
- Add rate limiting to login, password reset, OTP, and expensive mutations.
- Use idempotency for operations that can otherwise be double-submitted.
- Design for fail-closed behavior when state is uncertain.

## A07: Authentication Failures

### Kotlin

```kotlin
// ❌ Accepts any signed JWT
val claims = parser.parseClaimsJws(token).body

// ✅ Validate issuer, audience, and expiry
val claims = parser.requireIssuer(issuer).requireAudience(audience).build().parseClaimsJws(token).body
require(claims.expiration.after(Date()))
```

### Go

```go
// ❌ Token parsed without claim validation
jwt.Parse(tokenString, keyFunc)

// ✅ Enforce issuer, audience, expiry, and algorithm
jwt.ParseWithClaims(tokenString, &Claims{}, keyFunc,
jwt.WithIssuer(expectedIssuer), jwt.WithAudience(expectedAudience), jwt.WithValidMethods([]string{"RS256"}))
```

### Java (Spring Boot)

```java
// ❌ Custom auth check trusts unsigned header
String user = request.getHeader("X-User");

// ✅ Let Spring Security validate JWT and enforce auth centrally
http.oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()));
http.authorizeHttpRequests(auth -> auth.requestMatchers("/api/**").authenticated());
```

### Node.js / Next.js

```ts
// ❌ middleware only checks cookie presence
if (!req.cookies.get("session")) return NextResponse.redirect(new URL("/login", req.url))

// ✅ middleware guards routes, action re-checks session and Origin
if (!req.cookies.get("session")) return NextResponse.redirect(new URL("/login", req.url))
const session = await requireSession()
const h = await headers()
if (h.get("origin") !== `https://${h.get("host")}`) throw new Error("CSRF blocked")
```

### Patterns

- Prefer platform or framework auth components over custom token parsing.
- Validate `iss`, `aud`, `exp`, and accepted signing algorithms.
- Use secure, HTTP-only, `SameSite` cookies for browser sessions.
- Re-check authentication and authorization inside Server Actions and route handlers.

## A08: Software or Data Integrity Failures

### Kotlin

```kotlin
// ❌ Unsafe polymorphic deserialization
objectMapper.enableDefaultTyping()

// ✅ Decode into explicit DTOs
val req = objectMapper.readValue(payload, OrderRequest::class.java)
```

### Go

```go
// ❌ Decode untrusted input into interface{}
var payload interface{}
json.NewDecoder(r.Body).Decode(&payload)

// ✅ Decode into concrete request type
var req OrderRequest
json.NewDecoder(r.Body).Decode(&req)
```

### Java (Spring Boot)

```java
// ❌ Trust webhook payload without signature check
service.importOrder(body);

// ✅ Verify signature before processing data
if (!signatureVerifier.isValid(signature, body)) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
service.importOrder(body);
```

### Node.js / Next.js

```ts
// ❌ Process callback body without integrity check
await processOrder(await req.text())

// ✅ Verify HMAC before accepting payload
const body = await req.text()
if (!isValidSignature(req.headers.get("x-signature"), body)) return new Response("unauthorized", { status: 401 })
await processOrder(body)
```

### Patterns

- Decode untrusted input into explicit DTOs, not generic object graphs.
- Verify signatures on webhooks, callbacks, and imported artifacts before use.
- Pin CI dependencies and actions so your pipeline is reproducible.
- Return only minimal, trusted data from server code to clients.

## A09: Security Logging and Alerting Failures

### Kotlin

```kotlin
// ❌ PII in logs
log.info("Created order for nationalId=${user.nationalId}")

// ✅ Structured logging without PII
log.info("Order created", kv("orderId", order.id), kv("caseId", order.caseId), kv("callId", callId))
```

### Go

```go
// ❌ Logs nationalId directly
slog.Info("order created", "nationalId", user.NationalId)

// ✅ Use opaque IDs and request correlation
slog.Info("order created", "order_id", order.ID, "case_id", order.CaseID, "request_id", requestID)
```

### Java (Spring Boot)

```java
// ❌ Leaks nationalId in logs
log.info("Created order for nationalId={}", nationalId);

// ✅ Log opaque identifiers and trace context
log.info("Order created orderId={} caseId={} traceId={}", orderId, caseId, MDC.get("traceId"));
```

### Node.js / Next.js

```ts
// ❌ Logs request body with nationalId
logger.info({ body }, "creating order")

// ✅ Structured audit log without PII
logger.info({ orderId, caseId, requestId }, "order created")
```

### Patterns

- Never log nationalId, tokens, raw request bodies, or secrets.
- Use structured logs with correlation IDs and opaque resource IDs.
- Create audit events for sensitive actions such as order changes and access grants.
- Alert on suspicious patterns such as repeated auth failures or unusual traffic spikes.

## A10: Mishandling of Exceptional Conditions

### Kotlin

```kotlin
// ❌ Swallows errors and keeps going
val req = runCatching { call.receive<OrderRequest>() }.getOrNull()

// ✅ Fail safely and return sanitized error
val req = try { call.receive<OrderRequest>() } catch (e: Exception) {
    log.warn("Invalid order request", kv("callId", callId))
    return@post call.respond(HttpStatusCode.BadRequest, "Invalid request")
}
```

### Go

```go
// ❌ Ignores decode error
json.NewDecoder(r.Body).Decode(&req)

// ✅ Handle error explicitly and stop processing
if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
http.Error(w, "invalid request", http.StatusBadRequest)
return
}
```

### Java (Spring Boot)

```java
// ❌ Leaks internal exception details to client
return ResponseEntity.internalServerError().body(Map.of("error", ex.getMessage()));

// ✅ Centralize sanitization in @RestControllerAdvice
@ExceptionHandler(Exception.class)
ResponseEntity<Map<String, String>> handle(Exception ex) { return ResponseEntity.internalServerError().body(Map.of("error", "Internal server error")); }
```

### Node.js / Next.js

```ts
// ❌ Returns stack trace to client
return Response.json({ error: err.stack }, { status: 500 })

// ✅ Log details server-side, return generic response
logger.error({ err, requestId }, "route failed")
return Response.json({ error: "Internal server error" }, { status: 500 })
```

### Patterns

- Handle parse, IO, and database errors explicitly.
- Fail closed when the system cannot determine a safe outcome.
- Keep detailed exception data in logs, not in responses.
- Centralize error mapping in middleware, exception mappers, or route helpers.
