---
name: kotlin-app-config
description: Sealed-class configuration for Kotlin applications with environment-specific settings
license: MIT
compatibility: Kotlin application
metadata:
  domain: backend
  tags: kotlin configuration sealed-class environment
---

# Kotlin Application Configuration Skill

This skill provides patterns for type-safe environment configuration using Kotlin sealed classes.

## Sealed Class Configuration Pattern

```kotlin
sealed class Environment(
    val name: String,
    val databaseUrl: String,
    val kafkaBrokers: String,
    val oidcIssuer: String
) {
    data object Local : Environment(
        name = "local",
        databaseUrl = "jdbc:postgresql://localhost:5432/myapp",
        kafkaBrokers = "localhost:9092",
        oidcIssuer = "http://localhost:8080/oidc"
    )

    data class Dev(
        private val env: Map<String, String>
    ) : Environment(
        name = "dev",
        databaseUrl = env.getValue("DATABASE_URL"),
        kafkaBrokers = env.getValue("KAFKA_BROKERS"),
        oidcIssuer = env.getValue("OIDC_ISSUER")
    )

    data class Prod(
        private val env: Map<String, String>
    ) : Environment(
        name = "prod",
        databaseUrl = env.getValue("DATABASE_URL"),
        kafkaBrokers = env.getValue("KAFKA_BROKERS"),
        oidcIssuer = env.getValue("OIDC_ISSUER")
    )

    companion object {
        fun from(env: Map<String, String>): Environment {
            return when (env["APP_CLUSTER"]) {
                "dev" -> Dev(env)
                "prod" -> Prod(env)
                else -> Local
            }
        }
    }
}
```

## Using Configuration

```kotlin
fun main() {
    val env = Environment.from(System.getenv())

    val dataSource = createDataSource(env.databaseUrl)
    val kafkaProducer = createKafkaProducer(env.kafkaBrokers)

    logger.info("Starting application in ${env.name} environment")
}
```

## With Konfig Library

```kotlin
import com.natpryce.konfig.*

data class AppConfig(
    val database: DatabaseConfig,
    val kafka: KafkaConfig,
    val auth: AuthConfig
)

data class DatabaseConfig(
    val url: String
)
data class KafkaConfig(
    val brokers: String
)
data class AuthConfig(
    val issuer: String
)

val config = EnvironmentVariables()

val appConfig = AppConfig(
    database = DatabaseConfig(
        url = config.getOrNull(Key("DATABASE_URL", stringType))
            ?: "jdbc:postgresql://localhost:5432/myapp"
    ),
    kafka = KafkaConfig(
        brokers = config.getOrNull(Key("KAFKA_BROKERS", stringType))
            ?: "localhost:9092"
    ),
    auth = AuthConfig(
        issuer = config.getOrNull(Key("OIDC_ISSUER", stringType))
            ?: "http://localhost:8080/oidc"
    )
)
```

## Alternative: Sealed Interface Pattern

Production pattern supporting multiple cluster types:

```kotlin
sealed interface Environment {
    val cluster: String
    val tier: Tier

    enum class Tier { TEST, LOCAL, DEV, PROD }

    companion object {
        private val all: List<Environment> = listOf(
            TestEnvironment,
            LocalEnvironment,
            CloudEnvironment.DEV,
            CloudEnvironment.PROD
        )

        val current: Environment by lazy {
            val cluster = System.getenv("APP_CLUSTER")
            all.find { it.cluster == cluster } ?: LocalEnvironment
        }
    }
}

sealed class DefaultEnvironment(
    override val cluster: String,
    override val tier: Environment.Tier
) : Environment

object TestEnvironment : DefaultEnvironment("test", Environment.Tier.TEST)
object LocalEnvironment : DefaultEnvironment("local", Environment.Tier.LOCAL)

enum class CloudEnvironment(
    override val cluster: String,
    override val tier: Environment.Tier
) : Environment {
    DEV("dev", Environment.Tier.DEV),
    PROD("prod", Environment.Tier.PROD)
}
```

## Benefits

- **Type Safety**: Compile-time validation of configuration
- **Environment Separation**: Clear boundaries between local/dev/prod
- **Testability**: Easy to create test configurations
- **Documentation**: Configuration structure is self-documenting
