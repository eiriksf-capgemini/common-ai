---
name: java-to-kotlin
description: Step-by-step Java-to-Kotlin migration with framework-aware transformations for Spring and Ktor
license: MIT
compatibility: Java project migrating to Kotlin
metadata:
  domain: backend
  tags: kotlin java migration refactoring ktor spring
---

# Java to Kotlin Migration

Systematic conversion of Java codebases to idiomatic Kotlin, with framework-aware transformations for JVM services. Covers the full journey from faithful translation through nullability audit, collection migration, and idiomatic transforms — plus framework-specific patterns for Spring→Ktor, JPA→Kotliquery, JUnit→Kotest, and Lombok elimination.

## When to Use

- Migrating existing Java services to Kotlin
- Converting Java files in mixed Java/Kotlin codebases
- Onboarding teams from Java to Kotlin patterns
- Planning a phased migration strategy for a service

## 4-Step Conversion Methodology

### Step 1: Faithful Translation

Direct Java → Kotlin conversion preserving exact behavior. Use IntelliJ's built-in converter as a starting point, then fix compilation errors. Keep all existing tests passing. No idiomatic changes yet — correctness first.

```java
// Java — before
public class UserService {
    private final UserRepository repository;
    private final Logger log = LoggerFactory.getLogger(UserService.class);

    public UserService(UserRepository repository) {
        this.repository = repository;
    }

    public User findById(Long id) {
        User user = repository.findById(id);
        if (user == null) {
            throw new NotFoundException("User not found: " + id);
        }
        log.info("Found user: {}", user.getName());
        return user;
    }

    public List<User> findActive() {
        return repository.findAll().stream()
            .filter(u -> u.getStatus().equals("active"))
            .collect(Collectors.toList());
    }
}
```

```kotlin
// Kotlin — Step 1: faithful translation (no idiomatic changes)
class UserService(private val repository: UserRepository) {
    private val log = LoggerFactory.getLogger(UserService::class.java)

    fun findById(id: Long): User {
        val user = repository.findById(id)
        if (user == null) {
            throw NotFoundException("User not found: $id")
        }
        log.info("Found user: {}", user.name)
        return user
    }

    fun findActive(): List<User> {
        return repository.findAll().stream()
            .filter { u -> u.status == "active" }
            .collect(Collectors.toList())
    }
}
```

### Step 2: Nullability Audit

Review every `!` (platform type assertion) and make nullability explicit. Map Java `@Nullable` / `@NotNull` to Kotlin `?` / non-null types. Decide per case: `requireNotNull()` vs safe calls vs default values. Focus on API boundaries — internal code gets strict non-null types.

```kotlin
// Before — platform types and implicit nullability
fun findById(id: Long): User {
    val user = repository.findById(id)  // returns User! (platform type)
    if (user == null) {
        throw NotFoundException("User not found: $id")
    }
    return user
}

// After — explicit nullability
fun findById(id: Long): User {
    return repository.findById(id)  // returns User? (explicit nullable)
        ?: throw NotFoundException("User not found: $id")
}
```

### Step 3: Collection and Type Migration

| Java | Kotlin |
|------|--------|
| `List<T>` (mutable) | `List<T>` (immutable) or `MutableList<T>` |
| `Optional<T>` | `T?` (nullable) |
| `Stream<T>` pipeline | Kotlin stdlib collection operations |
| `Map<K,V>` | `Map<K,V>` / `MutableMap<K,V>` |
| `enum` with methods | Kotlin `enum` or `sealed class` |

```kotlin
// Before — Java streams and Optional
fun findActive(): List<User> {
    return repository.findAll().stream()
        .filter { u -> u.status == "active" }
        .collect(Collectors.toList())
}

fun getDisplayName(id: Long): String {
    val user: Optional<User> = repository.findOptional(id)
    return user.map { it.name }.orElse("Unknown")
}

// After — Kotlin collection operations
fun findActive(): List<User> =
    repository.findAll().filter { it.status == "active" }

fun getDisplayName(id: Long): String =
    repository.findById(id)?.name ?: "Unknown"
```

### Step 4: Idiomatic Transforms

Apply Kotlin idioms: data classes, extension functions, sealed classes, `when` expressions, and scope functions where they improve readability.

```kotlin
// Before — Java-style POJO translated directly
class UserDto(
    private var id: Long,
    private var name: String,
    private var email: String,
    private var status: String
) {
    fun getId() = id
    fun getName() = name
    fun getEmail() = email
    fun getStatus() = status
    // equals, hashCode, toString, copy...
}

// After — Kotlin data class
data class UserDto(
    val id: Long,
    val name: String,
    val email: String,
    val status: String,
)

// Before — utility class with static methods
class StringUtils {
    companion object {
        fun maskNationalId(nationalId: String): String =
            if (nationalId.length == 11) nationalId.take(6) + "*****" else nationalId
    }
}
val masked = StringUtils.maskNationalId(nationalId)

// After — extension function
fun String.maskNationalId(): String =
    if (length == 11) take(6) + "*****" else this

val masked = nationalId.maskNationalId()

// Before — complex conditional chain
fun categorize(age: Int, status: String): String {
    if (status == "disabled") return "inactive"
    if (age < 18) return "minor"
    if (age < 67) return "working-age"
    return "senior"
}

// After — when expression
fun categorize(age: Int, status: String): String = when {
    status == "disabled" -> "inactive"
    age < 18 -> "minor"
    age < 67 -> "working-age"
    else -> "senior"
}

// Before — builder pattern
val config = Config.builder()
    .setHost("localhost")
    .setPort(8080)
    .setDebug(true)
    .build()

// After — named arguments with defaults
val config = Config(
    host = "localhost",
    port = 8080,
    debug = true,
)
```

## Framework-Aware Conversions

### Spring Boot → Ktor

| Spring | Ktor |
|--------|------|
| `@RestController` | `routing { }` with `get/post/put/delete` |
| `@Service` | Plain class with constructor injection |
| `@Repository` (JPA) | `using(sessionOf(dataSource))` pattern |
| `@Autowired` | Constructor parameters (no annotations) |
| `@Configuration` | Sealed class config pattern |
| `application.yml` | `System.getenv()` or `konfig` library |

```java
// Spring Boot controller
@RestController
@RequestMapping("/api/users")
public class UserController {
    @Autowired
    private UserService userService;

    @GetMapping("/{id}")
    public ResponseEntity<UserDto> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(userService.findById(id));
    }

    @PostMapping
    public ResponseEntity<UserDto> createUser(@RequestBody CreateUserRequest request) {
        UserDto created = userService.create(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }
}
```

```kotlin
// Ktor route handler
fun Route.userRoutes(userService: UserService) {
    route("/api/users") {
        get("/{id}") {
            val id = call.parameters["id"]?.toLongOrNull()
                ?: return@get call.respond(HttpStatusCode.BadRequest, "Invalid ID")
            val user = userService.findById(id)
            call.respond(HttpStatusCode.OK, user)
        }

        post {
            val request = call.receive<CreateUserRequest>()
            val created = userService.create(request)
            call.respond(HttpStatusCode.Created, created)
        }
    }
}
```

### Hibernate/JPA → Kotliquery

```java
// JPA entity + repository
@Entity
@Table(name = "orders")
public class OrderEntity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String userId;
    private String status;
    private LocalDate validFrom;
}

public interface OrderRepository extends CrudRepository<OrderEntity, Long> {
    List<OrderEntity> findByUserId(String userId);
}
```

```kotlin
// Kotliquery — data class + repository
data class Order(
    val id: Long,
    val userId: String,
    val status: String,
    val validFrom: LocalDate,
)

class OrderRepository(private val dataSource: DataSource) {
    fun findByUserId(userId: String): List<Order> =
        using(sessionOf(dataSource)) { session ->
            session.run(
                queryOf("SELECT * FROM orders WHERE user_id = ?", userId)
                    .map { row ->
                        Order(
                            id = row.long("id"),
                            userId = row.string("user_id"),
                            status = row.string("status"),
                            validFrom = row.localDate("valid_from"),
                        )
                    }.asList
            )
        }

    fun save(order: Order): Long =
        using(sessionOf(dataSource)) { session ->
            session.run(
                queryOf(
                    "INSERT INTO orders (user_id, status, valid_from) VALUES (?, ?, ?)",
                    order.userId, order.status, order.validFrom
                ).asUpdateAndReturnGeneratedKey
            ) ?: throw IllegalStateException("Failed to insert order")
        }
}
```

### JUnit → Kotest

```java
// JUnit 5 test
public class UserServiceTest {
    @Mock private UserRepository repository;
    @InjectMocks private UserService service;

    @BeforeEach
    void setup() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void shouldFindUserById() {
        User user = new User(1L, "Kari");
        when(repository.findById(1L)).thenReturn(user);

        User result = service.findById(1L);

        assertEquals("Kari", result.getName());
        verify(repository).findById(1L);
    }

    @Test
    void shouldThrowWhenNotFound() {
        when(repository.findById(99L)).thenReturn(null);

        assertThrows(NotFoundException.class, () -> service.findById(99L));
    }
}
```

```kotlin
// Kotest matchers + MockK
class UserServiceTest {
    private val repository = mockk<UserRepository>()
    private val service = UserService(repository)

    @Test
    fun `should find user by id`() {
        val user = User(1L, "Kari")
        every { repository.findById(1L) } returns user

        val result = service.findById(1L)

        result.name shouldBe "Kari"
        verify { repository.findById(1L) }
    }

    @Test
    fun `should throw when not found`() {
        every { repository.findById(99L) } returns null

        shouldThrow<NotFoundException> {
            service.findById(99L)
        }
    }
}
```

### Lombok → Kotlin Native

| Lombok | Kotlin |
|--------|--------|
| `@Data` | `data class` |
| `@Builder` | Named arguments + default values |
| `@Getter` / `@Setter` | `val` / `var` properties |
| `@Slf4j` | `KotlinLogging.logger {}` |
| `@AllArgsConstructor` | Primary constructor (Kotlin default) |
| `@NoArgsConstructor` | Not needed, or add default values |
| `@RequiredArgsConstructor` | Primary constructor with `val` params |

```java
// Lombok
@Data
@Builder
@Slf4j
public class Application {
    private final String userId;
    private final LocalDate receivedAt;
    @Builder.Default
    private String status = "received";

    public void process() {
        log.info("Processing application for {}", userId);
        this.status = "processed";
    }
}
```

```kotlin
// Kotlin native
private val logger = KotlinLogging.logger {}

data class Application(
    val userId: String,
    val receivedAt: LocalDate,
    var status: String = "received",
) {
    fun process() {
        logger.info { "Processing application for $userId" }
        status = "processed"
    }
}
```

### Jackson → kotlinx.serialization (optional)

| Jackson | kotlinx.serialization |
|---------|----------------------|
| `@JsonProperty("name")` | `@SerialName("name")` |
| `ObjectMapper()` | `Json { ignoreUnknownKeys = true }` |
| `@JsonIgnore` | `@Transient` |

> **Note:** Many services keep Jackson with the `jackson-module-kotlin` — only migrate to kotlinx.serialization if the team explicitly wants to.

## Git History Preservation

Two-phase rename strategy to preserve `git log --follow`:

```bash
# Phase 1: rename file (pure rename, no content change)
git mv src/main/java/com/example/MyService.java src/main/kotlin/com/example/MyService.kt
git commit -m "rename: MyService.java → MyService.kt"

# Phase 2: convert content (in separate commit)
# ... apply Kotlin conversion ...
git commit -m "refactor: convert MyService to idiomatic Kotlin"
```

This ensures `git log --follow src/main/kotlin/com/example/MyService.kt` shows the full history including the Java era.

## Batch Conversion Workflow

Convert bottom-up: dependencies before dependents. Keep mixed Java/Kotlin builds working throughout. Run the full test suite after each file conversion.

**Suggested order:**

1. **Models/DTOs** — data classes, straightforward wins
2. **Utilities** — extension functions, small scope
3. **Repositories** — Kotliquery migration
4. **Services** — business logic, may have complex nullability
5. **Controllers/Routes** — framework migration (Spring→Ktor)
6. **Configuration** — sealed class patterns
7. **Tests** — Kotest migration (do last, keeps validation working)

Within each layer, convert leaf packages first (no internal dependencies), then work inward.

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Kotlin keywords as identifiers (`when`, `is`, `in`, `object`) | Backtick-escape `` `when` `` or rename |
| SAM conversion — Java functional interfaces auto-convert, Kotlin interfaces don't | Use `fun interface` for Kotlin SAM types |
| Platform types (`T!`) from Java without null annotations | Decide null strategy explicitly — never leave `!` |
| Java static → Kotlin | `companion object` or top-level functions |
| `@JvmStatic` / `@JvmField` | Needed if Java code still calls Kotlin `companion object` members |
| Checked exceptions | Kotlin doesn't have them — add `@Throws` if called from Java |
| Property access syntax | Java `getX()` becomes `x` in Kotlin callers |

## Related

| Resource | Use For |
|----------|---------|
| `kotlin-app-config` skill | Sealed class configuration pattern |

## Boundaries

### ✅ Always

- Preserve git history (two-phase rename)
- Run tests after each file conversion
- Convert bottom-up (dependencies before dependents)
- Fix nullability explicitly — never leave platform types
- Keep mixed Java/Kotlin builds compiling throughout

### ⚠️ Ask First

- Framework migration (Spring → Ktor)
- Changing test framework (JUnit → Kotest)
- Build system changes (Maven → Gradle)
- Switching serialization library (Jackson → kotlinx)

### 🚫 Never

- Convert multiple files without testing in between
- Suppress Kotlin warnings with `@Suppress`
- Use `!!` without verifying the value cannot be null
- Change behavior during conversion — correctness first
- Delete Java files before Kotlin replacements compile and pass tests
