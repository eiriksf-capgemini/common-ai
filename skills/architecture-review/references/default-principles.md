# Default architecture principles

Fallback used when the repo states no principles of its own (SKILL.md Step 0). When the repo
does state principles, quote those instead and ignore this file.

## Decision process: advice, not approval

The team that owns a system owns its decisions. Before deciding something that affects
others, seek advice from the affected parties and from people with relevant expertise,
record the advice in the ADR, then decide. The process is advisory, not a gate.

## Principles

1. **Essential over accidental complexity.** Spend complexity on the business problem, not on
   tooling. Choose the simplest solution that solves the actual problem today.
2. **Prefer platform capabilities.** Use what the platform already provides (identity, secrets,
   ingress, databases, queues, metrics, tracing) before building or operating your own.
3. **Loose coupling.** Contracts and events over shared databases and synchronous chains where
   latency allows. Teams should be able to deploy independently.
4. **Reversible by default.** Prefer decisions that can be undone cheaply; isolate the ones
   that cannot (data models, public contracts, vendor lock-in) and give them extra scrutiny.
5. **Observability from day one.** Metrics, structured logs without personal data, traces and
   alerts with meaningful thresholds are part of "done", not a follow-up.
6. **Secure by default.** Least privilege, no shared credentials, identity-based access for
   workloads, nothing reachable that does not need to be.
7. **Cost is a requirement.** State standing cost, idle cost and what can be stopped or
   destroyed. Development environments should cost nothing when nobody uses them.
8. **Measure flow.** Track the DORA metrics (deployment frequency, lead time, change failure
   rate, time to restore) and let decisions improve them rather than degrade them.

## Platform-capability checklist (generic)

| Need | Prefer | Avoid |
|---|---|---|
| Identity for humans | the organisation's IdP (OIDC) | local user databases |
| Identity for workloads | managed / workload identity, federation | long-lived keys in secrets |
| Secrets | platform secret store, injected at runtime | secrets in Git or images |
| Ingress / TLS | platform ingress + managed certificates | hand-rolled proxies |
| Data stores | managed services | self-operated databases on VMs |
| Messaging | managed queue / stream | self-operated brokers |
| Metrics / logs / traces | platform-integrated stack | per-service bespoke pipelines |
| Delivery | GitOps / the standard CI path | manual deploys, snowflake scripts |
