---
name: security-review
description: Use before commit, push or pull request to check that the code is safe to merge
license: MIT
metadata:
  domain: security
  tags: security pre-commit vulnerability-scanning code-review
---

# Security Review Skill

This skill provides pre-commit and pre-PR security checks for applications. Covers secret scanning, vulnerability scanning, and common platform requirements.

For architecture questions, threat modeling, or compliance decisions, involve a security architect rather than relying on this checklist.

## Automated Scans

Run with `run_in_terminal`:

```bash
# Scan repo for known vulnerabilities and secrets
trivy repo .

# Scan Docker image for HIGH/CRITICAL CVEs
trivy image <image-name> --severity HIGH,CRITICAL

# Scan GitHub Actions workflows for insecure patterns
zizmor .github/workflows/

# Quick search for secrets in git history
git log -p --all -S 'password' -- '*.kt' '*.ts' | head -100
git log -p --all -S 'secret' -- '*.kt' '*.ts' | head -100
```

## Parameterized SQL (Never Concatenate)

```kotlin
// ✅ Correct – parameterized query
fun findUser(nationalId: String): User? =
    jdbcTemplate.queryForObject(
        "SELECT * FROM user WHERE nationalId = ?",
        userRowMapper,
        nationalId
    )

// ❌ Wrong – SQL injection risk
fun findUserUnsafe(nationalId: String): User? =
    jdbcTemplate.queryForObject(
        "SELECT * FROM user WHERE nationalId = '$nationalId'",
        userRowMapper
    )
```

## No PII in Logs

```kotlin
// ✅ Correct – log correlation ID, not PII
log.info("Processing case for user", kv("caseId", case.id), kv("topic", case.topic))

// ❌ Wrong – never log FNR, name, or other PII
log.info("Processing case for user ${user.nationalId}")  // GDPR violation
log.info("Name: ${user.name}")                            // GDPR violation
```

## Secrets from Environment, Never Hardcoded

```kotlin
// ✅ Correct – read from environment (injected from a Secret)
val dbPassword = System.getenv("DB_PASSWORD")
    ?: throw IllegalStateException("DB_PASSWORD missing")

// ❌ Wrong – hardcoded secret
val dbPassword = "supersecret123"
```

## Network Policy

Only expose what must be exposed. On Kubernetes, a default-deny `NetworkPolicy` with explicit allow rules:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: my-app
spec:
  podSelector:
    matchLabels:
      app: my-app
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend-app        # only explicitly named callers
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: customer-api
    - to:                              # external hosts only if strictly necessary
        - ipBlock:
            cidr: 203.0.113.0/24
```

Platforms with their own access-policy abstraction (service meshes, PaaS manifests) express the same thing; the rule is the same: explicit inbound and outbound, nothing open by default.

## OWASP Top 10 Checks

### A01: Broken Access Control

```kotlin
// ✅ Correct — check that user has access to the resource
@GetMapping("/api/orders/{id}")
fun getOrder(@PathVariable id: UUID): ResponseEntity<OrderDTO> {
    val user = getLoggedInUser()
    val order = orderService.findById(id)
    if (order.userId != user.id) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).build()
    }
    return ResponseEntity.ok(order.toDTO())
}

// ❌ Wrong — no access control (IDOR)
@GetMapping("/api/orders/{id}")
fun getOrder(@PathVariable id: UUID) = orderService.findById(id)
```

### A03: Injection

```kotlin
// ✅ Correct — parameterized query
jdbcTemplate.query("SELECT * FROM user WHERE nationalId = ?", mapper, nationalId)

// ❌ Wrong — string concatenation
jdbcTemplate.query("SELECT * FROM user WHERE nationalId = '$nationalId'", mapper)
```

### A05: Security Misconfiguration

```kotlin
// ✅ Correct — CORS only for known domains
@Bean
fun corsFilter() = CorsFilter(CorsConfiguration().apply {
    allowedOrigins = listOf("https://my-app.example.com")
    allowedMethods = listOf("GET", "POST")
    allowedHeaders = listOf("Authorization", "Content-Type")
})

// ❌ Wrong — open CORS
allowedOrigins = listOf("*")
```

### A07: Cross-Site Scripting (XSS)

```tsx
// ✅ Correct — React escapes automatically
<BodyShort>{user.navn}</BodyShort>

// ❌ Wrong — raw HTML injection
<div dangerouslySetInnerHTML={{ __html: userInput }} />
```

### A08: Insecure Deserialization

```kotlin
// ✅ Correct — validate input after deserialization
@PostMapping("/api/orders")
fun create(@RequestBody @Valid request: CreateOrderRequest): ResponseEntity<OrderDTO>

// ✅ Limit Jackson to known types
objectMapper.apply {
    activateDefaultTyping(
        polymorphicTypeValidator,
        ObjectMapper.DefaultTyping.NON_FINAL
    )
}
```

### A09: Logging & Monitoring

```kotlin
// ✅ Correct — structured logging with correlation ID, no PII
log.info("Order created", kv("orderId", order.id), kv("caseId", case.id))

// ❌ Wrong — PII in logs
log.info("Order for user ${user.nationalId} created")
```

## File Upload Security

```kotlin
// ✅ Correct — validate file type, size, and magic bytes
fun validateUpload(file: MultipartFile) {
    require(file.size <= 10 * 1024 * 1024) { "File too large (max 10 MB)" }
    require(file.contentType in ALLOWED_TYPES) { "Invalid file type" }

    val bytes = file.bytes.take(8).toByteArray()
    require(verifyMagicBytes(bytes, file.contentType!!)) { "File content does not match type" }
}

private val ALLOWED_TYPES = setOf("application/pdf", "image/png", "image/jpeg")
```

## Dependency Management

```kotlin
// build.gradle.kts — pin versions, use BOM
dependencyManagement {
    imports {
        mavenBom("org.springframework.boot:spring-boot-dependencies:3.4.1")
    }
}

// Check vulnerable dependencies
// ./gradlew dependencyCheckAnalyze
// trivy repo .
```

## Expanded Checklist

- [ ] SQL queries are parameterized (no string concatenation)
- [ ] No PII in logs (national ID, name, address)
- [ ] Secrets only from environment/secrets
- [ ] Network policy is explicit (no open inbound)
- [ ] CORS is restricted to known domains
- [ ] Input is validated and sanitized
- [ ] Access control checks ownership (not just auth)
- [ ] File upload validates type, size, and content
- [ ] Dependencies are up to date and vulnerability-scanned
- [ ] No `dangerouslySetInnerHTML` without sanitization

## Dependency Management

```bash
# Kotlin – check for outdated/vulnerable dependencies
./gradlew dependencyUpdates
./gradlew dependencyCheckAnalyze   # OWASP check

# Node/TypeScript
npm audit
npm audit fix
```

## Security Checklist

- [ ] No secrets, tokens, or API keys hardcoded in source
- [ ] No PII (national ID, name, address) in log statements
- [ ] All SQL queries use parameterized statements
- [ ] Network policy limits inbound/outbound to only what is needed
- [ ] Token validation on all protected endpoints
- [ ] M2M tokens validate `azp` against the pre-authorized client list
- [ ] Auth code matches the network policy's inbound rules (no dead code or missing rules)
- [ ] `trivy repo .` passes without HIGH/CRITICAL findings
- [ ] `zizmor` passes on all GitHub Actions workflows
- [ ] Git history clean of committed secrets (`git log` scan above)
- [ ] HTTPS enforced – no plain HTTP calls to external services
- [ ] Dependencies up to date (`dependencyUpdates` / `npm audit`)

## Related

| Resource | Use For |
|----------|---------|
| `security-owasp` skill | Code-level OWASP Top 10 patterns per language |
| `github-actions-hardening-audit` skill | Pipeline hardening baseline |
| [OWASP Top 10:2025](https://owasp.org/Top10/2025/) | Official category descriptions |

## Review contract

*Axes: the Expanded Checklist and the Security Checklist above, plus whatever the automated scans returned.*

The review ends here, in this shape. A review with no output section has not run.

**Judge primary evidence.** The diff, the file, the `EXPLAIN` output, the rendered page — never your own summary of the change, and never your memory of what you meant to write. Resolve the base first, then cover committed, staged, unstaged **and untracked** changes. Read untracked files in full: diff output omits them.

**Every axis reports.** Each axis produces at least one finding, or one line saying what it inspected and what that evidence does not prove. An axis that says nothing has not looked.

**Report what you inspected.** "No findings in the two files I opened" and "no findings in the change" are different claims, and only the first one is ever true.

```
Inspected:     <files, queries, URLs, viewports actually opened>
Not inspected: <in scope, not examined, and why>
Findings:      <n blocking, n concerns>
Verdict:       BLOCK | CONCERNS | CLEAN
```

- `BLOCK` — at least one finding that, shipped as written, risks data loss, a security or privacy breach, a production incident, or a wrong answer to a user.
- `CONCERNS` — no blocking finding, but at least one a maintainer should fix or answer first.
- `CLEAN` — every axis inspected against primary evidence, nothing at either bar. `CLEAN` claims only the axes above and the files on the `Inspected` line, and it is wrong if a defect is later found in them.

**Not a review:** `LGTM`; restating what the change does; cosmetic findings only; reading the changed lines without the code they call.
