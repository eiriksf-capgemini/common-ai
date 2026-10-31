---
name: migration-strategist
description: Plan a backward-compatible change to a database schema, API, event or data format for a system where old and new code run at the same time: rolling deploys, queued jobs, cached data, mobile clients, other repositories. Produces an expand-migrate-contract plan with verification gates, backfill, dual-write and rollback steps. Triggers: "migration plan", "schema change", "rename a column", "break the API safely", "expand-contract", "hvordan migrere uten nedetid", "/migration-strategist".
roles: [all]
license: MIT
metadata:
  domain: engineering
  tags: migration database api expand-contract zero-downtime
---

# Migration Strategist

## Purpose
Local development teaches a misleading lesson: change the schema, change the code, restart, done. Production has older instances still serving during a rollout, workers mid-job, long requests, cached rows, queued messages written by the previous version, and clients that update when they feel like it. A change that is correct in isolation can still fail during the window when two versions coexist, and a deploy can be interrupted anywhere in that window. This skill plans the change as a sequence with a gate between each step, so the question "what if it stops here" is answered in a document instead of during an incident.

Adapted from Infinity's "7 Claude Code Skills" (Medium, 2026-10-25). Run `blast-radius` first when the set of readers and writers is not already known.

## When to invoke
- Renaming, splitting, retyping or removing a column, table, Prisma model or index on a live database.
- Changing an API request or response shape, an error contract, an auth claim, or a route.
- Changing an event, queue message, cache value, file format or anything serialised and read later by code that may be older or newer.
- Any change where a client outside the deploy unit (mobile app, another repo, a partner integration) depends on the old form.
- Not for additive changes nobody reads yet; say so, and ship them in one step.

## Procedure
1. **Contracts.** Write down the existing contract and the proposed one side by side: schema, shape, semantics, nullability, defaults, ordering, encoding.
2. **Readers and writers.** List every writer and every reader of the contract, with its deploy unit and release cadence: the service, its workers and cron jobs, other repos, clients, analytics, backups and restores. Take this from a `blast-radius` run when one exists.
3. **Expand.** Introduce the new form alongside the old: new nullable column or new table, new field in the response, new event version, new route. Nothing reads it yet. Old code must be unaffected by its presence.
4. **Migrate.** Move writers to write both forms (dual write), backfill historical data in batches with a resumable cursor, then move readers to prefer the new form with the old as fallback. Each move is its own deploy. Define how a batch backfill is verified (row counts, checksums, a sampled diff).
5. **Contract.** Once every reader has migrated and the metrics show the old form unread for a full retention window (longest cache TTL, longest queue age, oldest supported client), stop writing the old form, then remove it. Removal is a separate deploy from "stop writing".
6. **Gates.** Between each step, name the observable condition that permits the next one: a query, a metric, a log line, a client version floor. No gate, no step.
7. **Failure at every step.** For each step, state what happens if the deploy halts halfway, if the step must be rolled back, and whether the rollback itself is compatible with data written in the meantime. Backfills must be idempotent; dual writes must tolerate one side failing.
8. **Checklists.** Produce a deployment checklist and a recovery checklist, both executable by someone who did not write the plan.

## Output
Write to the task's working file or `/tmp/migration-<slug>.md`; return the path. Shape:

```
## Migration: <old contract> → <new contract>
Readers and writers: table (component, deploy unit, cadence, reads/writes, old/new)
Phase 1 Expand: changes, deploy unit, gate to proceed, rollback
Phase 2 Migrate: dual write, backfill (batching, cursor, verification), reader switch, gates, rollback
Phase 3 Contract: stop-write, retention window and why, removal, gate, rollback
Interrupted-deploy analysis: per phase
Deployment checklist / Recovery checklist
Open questions: anything the plan assumes and nobody has confirmed
```

## Rules
- Assume old and new versions coexist; never plan as if a deploy were atomic.
- Never remove or stop writing an old contract without evidence that its readers have migrated: a query, a metric, a version floor, not an assumption.
- Backfills and dual writes are idempotent by construction; say how.
- Prefer boring: an extra nullable column and a two-week retention window beat a clever one-step rewrite. Do not introduce a tool or a coordinator the problem does not need.
- When the change is to ugcportal's or Esport Arena's Prisma schema, the plan also names the Prisma migration files and whether `prisma migrate deploy` runs before or after the app rollout in CI.
