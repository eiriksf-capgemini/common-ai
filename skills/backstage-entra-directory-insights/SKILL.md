---
name: backstage-entra-directory-insights
description: Sync Users/Groups from Microsoft Entra ID (Azure AD) into the Backstage catalog via the official msgraph plugin, and enrich User entity pages with data that plugin doesn't sync (password-change date, sign-in activity, MFA method count), plus a redesigned User/Group entity page layout. Use when asked to pull Azure AD/Entra directory data into Backstage, show group membership or "last password change" on a user page, or make User/Group catalog pages richer/more useful.
user-invocable: true
license: MIT
metadata:
  domain: platform-engineering
  tags: backstage entra-id azure catalog
---

# Backstage Entra ID directory insights

Built from a real session adding Entra ID (Azure AD)-backed User/Group entity
pages to a Backstage app on the **new frontend system** (`createApp` from
`@backstage/frontend-defaults`) and **new backend system** (`createBackend`
from `@backstage/backend-defaults`). No real Entra app registration existed
at build time — everything below is designed to be scaffolded and verified
against demo data first, then flipped on later with real credentials.

## 1. Check for `@backstage/plugin-org` before building custom cards

Before writing any custom User/Group card, check `packages/app/package.json`
for `@backstage/plugin-org` — it's commonly already an installed dependency
that nobody wired into `features`. Its `/alpha` export is a `FrontendPlugin`
you register directly (default import, same as `@backstage/plugin-catalog/alpha`):

```tsx
import orgPlugin from '@backstage/plugin-org/alpha';
// features: [catalogPlugin, orgPlugin, ...]
```

This alone gives you `EntityUserProfileCard` (entity ref, email, **memberOf
with a "...More (N)" dialog listing every group** — the "list all groups for
a user" ask is often already solved by just turning this on), `EntityGroupProfileCard`
(entity ref, parent group, child groups), `EntityMembersListCard`, and
`EntityOwnershipCard`. Don't rebuild these from scratch.

## 2. Custom cards via `EntityCardBlueprint`, not a new EntityPage

For anything `plugin-org` doesn't cover, add cards with
`EntityCardBlueprint.make()` from `@backstage/plugin-catalog-react/alpha`,
filtered by kind, in a module following the same `createFrontendModule({
pluginId: 'app', extensions: [...] })` shape as any other app module:

```tsx
const directoryInsightsCard = EntityCardBlueprint.make({
  name: 'directory-insights',
  params: {
    type: 'info',
    filter: { kind: 'user' },
    loader: () => import('./components/DirectoryInsightsCard')
      .then(m => <m.DirectoryInsightsCard />),
  },
});
```

`type: 'info'` places it in the right-hand rail next to the profile card;
`type: 'content'` (or omitted) puts it in the main column. Read the entity via
`useEntity()` from `@backstage/plugin-catalog-react` inside the loaded
component — don't thread it through props.

**Design for the common case: annotations are absent.** Every custom card
should render a clear, non-alarming empty state (e.g. "Not synced — Entra ID
integration not yet configured") when its data annotations aren't present,
rather than a blank card or an error. This is the state the app will be in
for most of its life until real credentials exist, and after that too for any
entity the sync hasn't reached yet.

## 3. `@backstage/plugin-catalog-backend-module-msgraph` — ignore the README's wiring instructions

The package's own README shows the **legacy** backend system
(`packages/backend/src/plugins/catalog.ts`, `CatalogBuilder.create`,
manually calling `builder.addEntityProvider(MicrosoftGraphOrgEntityProvider.fromConfig(...))`).
On the new backend system, none of that is needed — the package's default
export (`index.d.ts`, not `/alpha`) is already a `createBackendModule` you
register exactly like every other module in `packages/backend/src/index.ts`:

```ts
backend.add(import('@backstage/plugin-catalog-backend-module-msgraph'));
```

It reads config from `catalog.providers.microsoftGraphOrg` — either a single
provider block (if it directly `.has('clientId')`) or a map of named provider
blocks (`catalog.providers.microsoftGraphOrg.<id>`). It natively syncs
`displayName`, `email`, `jobTitle`, `department`, `officeLocation`, manager
relation, and group membership/children — real org data belongs here, not in
a custom processor.

Required Graph **application** permissions (admin consent, not delegated):
`GroupMember.Read.All`, `User.Read.All`.

Before writing the actual config block for a new version of this package,
read the installed copy's own `README.md` and `dist/index.d.ts` —
field/config-key names have drifted between versions before.

## 4. Sensitive/dynamic fields need a separate `CatalogProcessor`, not the msgraph provider

Password-change date, sign-in activity, and MFA method count are **not**
part of msgraph's sync (different Graph endpoints/permissions, more
sensitive, more volatile than org-chart data). Handle them with a second,
small backend module — a `CatalogProcessor.postProcessEntity` that runs
after the msgraph sync, looks up the Graph object ID annotation the msgraph
provider already wrote (`graph.microsoft.com/user-id`), and calls Graph
directly:

```ts
class GraphDirectoryInsightsProcessor implements CatalogProcessor {
  async postProcessEntity(entity, _location, _emit, cache) {
    if (!this.credentials || !isUserEntity(entity)) return entity;
    const userId = entity.metadata.annotations?.['graph.microsoft.com/user-id'];
    if (!userId) return entity;
    const lastFetch = await cache.get<number>('lastFetch');
    if (lastFetch && Date.now() - lastFetch < ONE_HOUR_MS) return entity; // throttle
    // ...acquire token, fetch, write annotations, cache.set('lastFetch', Date.now())
  }
}
```

- Use `CatalogProcessorCache` (the 4th `postProcessEntity` param) to throttle —
  it's scoped per-entity and persists between processing runs. Without this,
  a processor calling out to Graph runs on **every** catalog processing
  cycle for every matching entity.
- Get the Graph token via `@azure/msal-node`'s `ConfidentialClientApplication.acquireTokenByClientCredential({ scopes: ['https://graph.microsoft.com/.default'] })`
  (client-credentials flow) — this is a separate, smaller permission
  footprint than the org-wide msgraph sync: `User.Read.All` (for
  `passwordProfile.lastPasswordChangeDateTime`), `AuditLog.Read.All` (for
  `signInActivity.lastSignInDateTime`), `UserAuthenticationMethod.Read.All`
  (for `/users/{id}/authentication/methods`) — all admin-consented app
  permissions, none delegated.
- Register it the same way as any catalog backend module:
  `createBackendModule({ pluginId: 'catalog', moduleId: '...' })` +
  `catalog.addProcessor(...)` inside `registerInit`, `backend.add(import('./modules/...'))`
  in `index.ts`.
- **Fail closed and silent, not loud**, when unconfigured: gate the whole
  processor behind an explicit `enabled: false`-by-default config flag, and
  swallow/log-debug (not throw) on missing credentials or Graph errors so a
  half-configured integration never breaks catalog processing for every
  other entity.

## 5. Config: env-var placeholders only, `enabled` flags default off

```yaml
catalog:
  providers:
    microsoftGraphOrg:
      default:
        tenantId: ${AZURE_TENANT_ID}
        clientId: ${AZURE_CLIENT_ID}
        clientSecret: ${AZURE_CLIENT_SECRET}
        schedule: { frequency: { hours: 1 }, timeout: { minutes: 10 } }

graphDirectoryInsights:
  enabled: false   # flip once AZURE_* creds + Graph app permissions exist
  tenantId: ${AZURE_TENANT_ID}
  clientId: ${AZURE_CLIENT_ID}
  clientSecret: ${AZURE_CLIENT_SECRET}
```

`${VAR}` references to *unset* env vars don't crash Backstage's config
loader — they just resolve to `undefined` for that key (confirmed: the app in that session
already shipped `integrations.github.token: ${GITHUB_TOKEN}` with no
`GITHUB_TOKEN` set, and starts fine). So it's safe to commit these blocks
with placeholders before any real tenant exists, as long as the code that
reads them treats a missing value as "not configured" rather than assuming
it's present.

Never put a real tenant ID, client ID, or client secret directly in a
committed config file or in chat — only `${ENV_VAR}` references, with real
values living in `app-config.local.yaml` (gitignored) or deployment secrets.

## 6. Compliance flag, every time

Password-change dates, sign-in activity, and full directory group membership
are personal data; MFA/auth-method data touches security posture. Before
pointing any of this at a real tenant (even for a demo), flag it to
whoever owns the Entra app registration and, if your org has one, the Data
Privacy Officer — this skill only builds the technical scaffolding, not the
authorization to use it on real people's data.

## Verify

1. `yarn tsc` across app + backend.
2. Dev server + a screenshot check of both a User and a Group entity page,
   confirming: `plugin-org` cards render, custom cards render in the right
   column, and the "not synced" empty state shows correctly (expected state
   with no real Entra credentials configured).
3. If default ports (3000 frontend / 7007 backend) are already in use by
   another project on the same machine, don't fight over them — create a
   gitignored `app-config.local.yaml` (check `.gitignore` for `*.local.yaml`
   first) with `app.baseUrl`, `backend.baseUrl`, `backend.listen.port`, and
   `backend.cors.origin` pointed at alternate ports, and pass no extra flags
   (`yarn start` picks up `app-config.local.yaml` automatically via the
   default config-loading order).
4. If no browser/Chromium shared libs are available in the sandbox (`error
   while loading shared libraries: libnspr4.so`), `apt-get download` the
   missing libs (`libnspr4 libnss3 libatk1.0-0t64 libcups2t64 libgbm1
   libasound2t64 libpango-1.0-0 libpangocairo-1.0-0 libx11-6 libxcomposite1
   libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 libcairo2 libdrm2
   libexpat1 libglib2.0-0t64 libxcb1`) into a scratch dir, `dpkg-deb -x` each,
   and set `LD_LIBRARY_PATH` to the extracted `usr/lib/x86_64-linux-gnu`
   before launching Playwright — no root needed.
5. The msgraph sync and the custom processor's real Graph calls **cannot** be
   verified without a real Entra app registration — say so explicitly rather
   than claiming end-to-end verification you didn't do.
