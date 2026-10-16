---
name: backstage-plugin-wiring
description: Diagnose a Backstage plugin that's installed and even backend-registered but doesn't do anything visible — and distinguish backend logger *config* from a real external log-sink integration. Use when a plugin's backend routes/APIs work (or the package is a listed dependency) but its UI/behavior never shows up, or when asked to "send logs to CloudWatch/Loki/Datadog/etc."
user-invocable: true
license: MIT
metadata:
  domain: platform-engineering
  tags: backstage plugins debugging logging
---

# Backstage plugin wiring

Built from two real fixes in a scaffolded Backstage app on the **new frontend
system** (`createApp` from `@backstage/frontend-defaults`): notifications/
signals plugins that were backend-registered but inert, and a logger-config
question that looked like a one-line config change but wasn't.

## 1. Backend registration and frontend registration are two separate steps — check both

A plugin can be:
- a listed `package.json` dependency,
- `backend.add(import('@backstage/plugin-x-backend'))`'d in
  `packages/backend/src/index.ts`,
- and its backend routes fully functional (`curl` against its API works),

...and still be completely invisible in the app, because the **frontend**
`/alpha` package was never added to `packages/app/src/App.tsx`'s
`features: [...]` array.

**Important caveat, corrected after this was first written**: the app in that session had
`app-config.yaml`'s `app.packages: all` set, and — contrary to what an
earlier version of this skill (and `backstage-design-sync`) claimed —
that setting **does** auto-discover every `@backstage/plugin-*` package in
`packages/app/package.json` in this dev environment, via a build-time
virtual module (`__backstage-autodetected-plugins__.js`) that populates
`window["__@backstage/discovered__"]`. Confirmed directly: 31 modules
auto-discovered in a live session, including `plugin-notifications`,
`plugin-signals`, and `plugin-scaffolder`. See `backstage-design-sync`'s
corrected section 5 for the full finding, including how to verify it
yourself (inspect that global, or grep the served `vendor.js` for
`__@backstage/discovered__`).

**What this means for diagnosis**: "listed dependency, backend routes work,
nothing renders in the UI" is *still* a real bug class — explicit
`features[]` registration is still what the code should show, for
readability if nothing else, and auto-discovery may not hold on every
CLI/bundler version or in a production build. But **check whether the page
already works before writing an explicit-registration fix** — if
`app.packages: all` is set and auto-discovery is active, the "fix" may be
redundant (harmless to add, but not what actually made it work), and the
real bug is somewhere else. Don't assume either way; verify with the
`window["__@backstage/discovered__"]` check first.

Concrete case (registration added regardless of whether auto-discovery was
already covering it — worth doing either way, but don't cite this as proof
the page was broken without having tested the pre-fix state):
`@backstage/plugin-notifications-backend` and
`@backstage/plugin-signals-backend` were registered in
`packages/backend/src/index.ts:66-67`, but the notifications page and
real-time toast delivery did nothing until
`@backstage/plugin-notifications/alpha` and `@backstage/plugin-signals/alpha`
were imported and added to `features` in `packages/app/src/App.tsx`:

```tsx
import notificationsPlugin from '@backstage/plugin-notifications/alpha';
import signalsPlugin from '@backstage/plugin-signals/alpha';

export default createApp({
  features: [
    catalogPlugin,
    catalogImportPlugin,
    notificationsPlugin,
    signalsPlugin,
    navModule,
    themeModule,
  ],
});
```

This is the same class of bug as the catalog-import case documented in
`backstage-design-sync` (a page 404s instead of rendering, inheriting the
theme's chrome so it can look like a theming bug) — treat "plugin backend
works but nothing shows in the UI" as first evidence of a missing
`features[]` entry, not a backend problem, before digging further.

## 2. Logger config in `app-config.yaml` has a hard ceiling — it cannot route logs externally

`backend.logger.level` and `backend.logger.overrides` (matched by plugin) in
`app-config.yaml` control verbosity and per-plugin filtering with zero code:

```yaml
backend:
  logger:
    level: info
    overrides:
      - matcher:
          plugin: catalog
        level: debug
```

That's the entire surface of what config-only logging control can do. It
cannot redirect output to an external sink — CloudWatch, Loki, Elasticsearch,
Datadog, etc. There is no config key for that. Shipping logs externally
requires overriding the `rootLogger` core backend service with a custom
Winston transport (a backend service override, i.e. code in
`packages/backend/src/index.ts` replacing the `coreServices.rootLogger`
implementation) — see
https://backstage.io/docs/backend-system/core-services/root-logger/. If a
request is "route our logs to X," don't reach for `app-config.yaml` at all;
scope it as a rootLogger override from the start.
