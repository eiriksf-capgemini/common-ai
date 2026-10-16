---
name: postgresql-review
description: PostgreSQL query review, optimisation and best practices for backend applications
license: MIT
compatibility: PostgreSQL database
metadata:
  domain: backend
  tags: postgresql sql optimization review indexing
---

# PostgreSQL Review Skill

Review and optimize PostgreSQL queries, schemas, and patterns for backend applications. Covers EXPLAIN analysis, index strategies, JSONB patterns, and common anti-patterns.

## Query Analysis

Run `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` to analyze queries:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders
WHERE user_id = '3f2b8c1e-6a4d-4e0b-9d57-1c2a7e5f9b10'
  AND status = 'active'
ORDER BY created_at DESC
LIMIT 10;
```

### Red Flags in EXPLAIN Output

| Sign | Problem | Solution |
|---|---|---|
| `Seq Scan` on large table | Missing index | `CREATE INDEX` |
| `Sort` with `external merge` | Not enough `work_mem` | Increase `work_mem` or add index with correct sort order |
| `Nested Loop` with high `rows` | Cartesian product / missing join index | Add index on join column |
| `Hash Join` with `Batches > 1` | `work_mem` too low | Increase `work_mem` for the session |
| Large difference between `estimated` and `actual` rows | Outdated statistics | `ANALYZE tablename;` |

## Index Strategies

```sql
-- Simple index for lookups
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Composite index — columns in order of selectivity
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- Partial index — only relevant rows
CREATE INDEX idx_orders_active ON orders(user_id)
WHERE status = 'active';

-- Covering index — avoids table lookup
CREATE INDEX idx_orders_covering ON orders(user_id, status)
INCLUDE (created_at, amount);

-- Concurrent — no table locking (requires outside transaction)
CREATE INDEX CONCURRENTLY idx_orders_date ON orders(created_at);
```

### When to Use What?

| Scenario | Index Type |
|---|---|
| `WHERE a = x` | B-tree on `a` |
| `WHERE a = x AND b = y` | Composite `(a, b)` |
| `WHERE a = x AND status = 'active'` | Partial index `WHERE status = 'active'` |
| `WHERE a LIKE 'prefix%'` | B-tree (prefix only) |
| `WHERE a @> '{"key": "val"}'` | GIN on JSONB |
| Full-text search | GIN with `to_tsvector` |
| Geography | GiST |

## JSONB Patterns

```sql
-- ✅ Correct — GIN index for JSONB queries
CREATE INDEX idx_metadata_gin ON events USING GIN (metadata);

-- Query JSONB
SELECT * FROM events
WHERE metadata @> '{"type": "order", "status": "paid"}';

-- Fetch nested values
SELECT
    id,
    metadata->>'type' AS type,
    metadata->'details'->>'amount' AS amount
FROM events;

-- ❌ Wrong — casting in WHERE without index
SELECT * FROM events
WHERE (metadata->>'created_at')::timestamp > NOW() - INTERVAL '7 days';
-- ✅ Better — use expression index
CREATE INDEX idx_metadata_created_at ON events (((metadata->>'created_at')::timestamp));
```

## Common Table Expressions (CTEs)

```sql
-- ✅ Correct — CTE for readability
WITH active_orders AS (
    SELECT user_id, COUNT(*) AS order_count
    FROM orders
    WHERE status = 'active'
    GROUP BY user_id
),
last_activity AS (
    SELECT user_id, MAX(created_at) AS last_active
    FROM activity_log
    GROUP BY user_id
)
SELECT
    ao.user_id,
    ao.order_count,
    la.last_active
FROM active_orders ao
JOIN last_activity la USING (user_id)
WHERE ao.order_count > 1;
```

## Window Functions

```sql
-- Ranking within group
SELECT user_id, order_id, created_at
FROM (
    SELECT
        user_id,
        order_id,
        created_at,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn
    FROM orders
) ranked
WHERE rn = 1;  -- Latest order per user

-- Running total
SELECT
    stat_date,
    event_count,
    SUM(event_count) OVER (ORDER BY stat_date) AS cumulative
FROM daily_statistics;
```

## Anti-patterns

### N+1 Queries

```kotlin
// ❌ Wrong — N+1: one query per user
val users = repository.findAll()
users.forEach { user ->
    val orders = orderRepository.findByUserId(user.id)  // N extra queries
    process(user, orders)
}

// ✅ Correct — JOIN or batch query
val usersWithOrders = repository.findAllUsersWithOrders()  // Single query with JOIN
```

### SELECT *

```sql
-- ❌ Wrong — fetches all columns incl. large JSONB/TEXT
SELECT * FROM documents WHERE user_id = 12345;

-- ✅ Correct — only necessary columns
SELECT id, title, created_at FROM documents WHERE user_id = 12345;
```

### Missing LIMIT on Unbounded Data

```sql
-- ❌ Wrong — can return millions of rows
SELECT * FROM events WHERE type = 'login';

-- ✅ Correct — always limit result set
SELECT * FROM events WHERE type = 'login'
ORDER BY created_at DESC
LIMIT 100;
```

## Connection Pooling

```kotlin
// HikariCP — recommended configuration for containerised workloads
HikariDataSource().apply {
    jdbcUrl = System.getenv("DB_JDBC_URL")
        ?: "jdbc:postgresql://${System.getenv("DB_HOST")}:5432/${System.getenv("DB_DATABASE")}"
    username = System.getenv("DB_USERNAME")
    password = System.getenv("DB_PASSWORD")
    maximumPoolSize = 5       // start low per pod, scale up as needed
    minimumIdle = 1
    connectionTimeout = 10_000
    idleTimeout = 300_000
    maxLifetime = 600_000
    validationTimeout = 5_000
}
```

## Migration Strategies for Large Tables

```sql
-- Add column with default (PostgreSQL 11+ — instant, no rewrite)
ALTER TABLE large_table ADD COLUMN new_column BOOLEAN DEFAULT false;

-- Create index without locking the table
CREATE INDEX CONCURRENTLY idx_large_table_new_column ON large_table(new_column);

-- Batch update (avoid long transaction)
-- Run in application code with batches of 10,000 rows:
UPDATE large_table SET new_column = true WHERE id BETWEEN $1 AND $2;
```

## Checklist

- [ ] Do all `WHERE` columns have indexes?
- [ ] Has `EXPLAIN ANALYZE` been run for new/changed queries?
- [ ] Are we avoiding `SELECT *` in production code?
- [ ] Do we have `LIMIT` on queries that can return many rows?
- [ ] Are JSONB columns indexed with GIN?
- [ ] Is connection pool size appropriate (5-10 per pod is a sensible start)?
- [ ] Are migrations on large tables run with `CONCURRENTLY`?

## Review contract

*Axes: the Checklist above — indexing, `EXPLAIN` evidence, column and row bounds, JSONB, connection pooling, migrations.*

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
