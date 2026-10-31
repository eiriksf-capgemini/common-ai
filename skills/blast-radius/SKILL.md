---
name: blast-radius
description: Trace what depends on an interface before changing it. Use before renaming or removing a function, changing an API response or request shape, altering a database column or Prisma model, changing an event payload, a config key, an environment variable, or a shared type. Read-only; produces a classified dependency list with evidence, not a patch. Triggers: "blast radius", "what breaks if I change", "who calls this", "hva avhenger av", "/blast-radius".
roles: [all]
license: MIT
metadata:
  domain: engineering
  tags: refactoring dependencies api impact-analysis
---

# Blast Radius

## Purpose
A patch that is correct in the file being edited can still break three callers, a background job and a mobile client that reads the old field for another six months. The agent finds the obvious file quickly and produces a reasonable patch, which is exactly why the search for dependents has to happen first and separately. This skill is that search. It ends with a classified list and the smallest safe change, and it modifies nothing.

Adapted from Infinity's "7 Claude Code Skills" (Medium, 2026-10-25).

## When to invoke
- Before a rename, signature change, or removal of anything exported, public, or shared between packages.
- Before changing a response or request shape, a database schema, a Prisma model, an event or queue payload, a feature flag, a config key, an environment variable, or an error code that clients match on.
- When the user asks "what breaks if", "who uses this", or asks for an estimate of a change that touches a contract.
- Not for changes inside one private function with one caller; say so and move on.

## Procedure
1. **Name the contract.** State precisely what changes: symbol, field, type, table, column, route, env var, event name. If more than one, list each; the analysis is per contract.
2. **Trace direct dependents** with the repo's own tools: grep and the language's reference search for the symbol; route and client searches for an API; migrations, raw SQL, ORM queries, seeds, fixtures and reports for a column; `process.env` and deployment manifests for an env var; workflow files for anything CI reads.
3. **Trace indirect dependents** one hop out: consumers of the callers' outputs, serialised forms (JSON on disk, cache keys, queue messages, logs that are parsed), generated clients, OpenAPI or GraphQL schemas, tests that pin the old shape, docs and runbooks that show it.
4. **Look outside the repo** when the contract leaves it: other repositories in the same organisation, mobile or desktop clients with their own release cadence, webhooks delivered to third parties, dashboards and alerts keyed on a field name.
5. **Classify every finding** into exactly one of:
   - **Confirmed breakage**: the dependent reads or calls the thing that changes, and the change is incompatible. Cite `path:line`.
   - **Possible compatibility risk**: a dependent exists but compatibility depends on something not yet verified (a runtime value, a client version, a dynamic key). Say what would settle it.
   - **Unaffected**: checked and safe; list these too, so the reader knows what was searched.
6. **Recommend the smallest safe implementation**: often a compatible addition first and a removal later (hand off to `migration-strategist` when old and new must coexist across a deploy), plus the tests that would catch each confirmed breakage.

## Output
Write to the task's working file or `/tmp/blast-radius-<slug>.md` when longer than a screen; return the path and the counts. Shape:

```
## Blast radius: <contract>
Confirmed breakage (n)
- path:line, what it does with the contract, why it breaks
Possible compatibility risk (n)
- path:line, what is unknown, how to verify
Unaffected, searched (n)
- path or area, why safe
Searched with: <commands or queries, so the search can be repeated>
Smallest safe change: ...
Tests to add: ...
```

## Rules
- Do not edit code during the analysis. If asked to "just do it", run the analysis first and report, then implement in a separate step.
- Never invent a dependency without evidence. A dependent that could not be verified goes under "possible risk" with the reason, never under "confirmed".
- Record what was searched, not only what was found; an empty result is only meaningful with the query attached.
- Scale the depth to the contract: an exported type used in forty files needs the full procedure; a private helper does not need the skill at all.
