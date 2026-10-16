---
name: backstage-global-header
description: Add persistent app-wide chrome (a header bar with the instance name, nav links, logged-in user) that shows on every page in Backstage's new frontend system, via AppRootWrapperBlueprint. Use when asked for a header/topbar/banner visible across all pages, not just one.
user-invocable: true
license: MIT
metadata:
  domain: platform-engineering
  tags: backstage frontend header
---

# Backstage global header

Built from a real session adding a top header (instance name + nav links +
logged-in user) to a Backstage app on the **new frontend system**
(`createApp` from `@backstage/frontend-defaults`), confirmed against
`@backstage/plugin-app-react@0.2.5` / `@backstage/plugin-app@0.1.x`.
Complements `backstage-design-sync` (colors/branding) and
`backstage-homepage` (the "/" route's content) — this is about chrome that
wraps *every* route, not one page's content.

## Why not `Header`/`ContentHeader` from `@backstage/core-components`

Those are per-page components a page opts into rendering inside its own
`<Content>` — that's what the `PageLayout` swappable component
(`backstage-scaffolder-styling`'s `SwappableComponentBlueprint` family) already
renders per page. None of them wrap the whole app. For chrome that must
appear identically on every route regardless of which page is mounted, the
right extension point is `AppRootWrapperBlueprint` from
`@backstage/plugin-app-react`.

## The mechanism, and why it's restricted to the app plugin

`AppRootWrapperBlueprint` attaches to `app/root`'s `wrappers` input, which is
marked `internal: true` in `@backstage/plugin-app`'s `AppRoot` extension —
its own JSDoc says "This blueprint is limited to use by the app plugin."
Concretely: register it in a module with `pluginId: 'app'`, same as the app's own
`navModule`/`themeModule`/`scaffolderModule`/`homeModule`.

**Positioning** (confirmed from `@backstage/plugin-app`'s `AppRoot.esm.js`
and `AppLayout.esm.js`): the app's `SidebarPage` (sidebar + routed content)
is built first, then each registered wrapper wraps around it as a single
child (`content = <Wrapper>{content}</Wrapper>`). So a wrapper's rendered
output sits **above the entire `SidebarPage`** — a full-width header pushes
both the sidebar and the content down, it doesn't float over just the
content pane. It still renders *inside* the router and API context
(`useApi`, `useRouteRef`, routing all work fine inside it).

```tsx
// modules/header/index.tsx — note .tsx, not .ts: this file has JSX in it
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { AppRootWrapperBlueprint } from '@backstage/plugin-app-react';
import { AppHeader } from './AppHeader';

const appHeaderWrapper = AppRootWrapperBlueprint.make({
  params: {
    component: ({ children }) => (
      <>
        <AppHeader />
        {children}
      </>
    ),
  },
});

export const headerModule = createFrontendModule({
  pluginId: 'app',
  extensions: [appHeaderWrapper],
});
```

`params.component` is the only supported key — the type also lists a
`Component` (capital C) field, but it's typed to always error
(`[error: "Use the 'component' parameter instead"]`); that's a deliberate
compile-time nudge away from an older/deprecated name, not a real option.

## Instance name and logged-in user, without hardcoding either

**Instance name** — read the same `app.title` the app already uses for the
browser tab title, via `configApiRef`, so a rename in `app-config.yaml`
doesn't require touching the header component:

```tsx
const configApi = useApi(configApiRef);
const title = configApi.getOptionalString('app.title') ?? 'Backstage';
```

**Logged-in user** — `identityApiRef.getProfileInfo()` (from
`@backstage/core-plugin-api`) returns `{ email?, displayName?, picture? }`.
It resolves against whatever `SignInPage` is configured — with no
`SignInPageBlueprint` registered (the default guest flow), it resolves to
`{ displayName: 'Guest', email: 'guest@example.com' }` out of the box, no
auth setup required to show *something* real in the header:

```tsx
const identityApi = useApi(identityApiRef);
const [displayName, setDisplayName] = useState<string>();
useEffect(() => {
  identityApi.getProfileInfo().then(p => setDisplayName(p.displayName));
}, [identityApi]);
```

Don't reach for `react-use`'s `useAsync` for this unless it's already a
direct dependency — it's usually only a transitive one here, and a plain
`useEffect`/`useState` avoids adding it just for one call.

## Gotchas already hit elsewhere, apply here too

- `makeStyles`' `fontWeight` typing breaks with `theme.typography.fontWeightBold`
  when any rule in the same `makeStyles` call also takes a props argument —
  use a numeric literal (`fontWeight: 700`) instead.
- Nav links inside the header are plain `<Link>` (`@backstage/core-components`)
  to fixed paths (`/`, `/catalog`, `/create`) — this duplicates the sidebar's
  own nav, which is fine (top bar quick-links vs. full sidebar menu is a
  normal pattern), but don't try to auto-derive the list from the sidebar's
  `nav.take(...)` calls — those are internal to `NavContentBlueprint`'s
  `component` render prop, not something importable from another module.

## Verify

Same loop as the other Backstage skills here: `yarn tsc`, then actually load
**more than one route** in a browser (`/` and `/catalog` at minimum) to
confirm the header is identical on both rather than accidentally scoped to
one page. See `backstage-scaffolder-styling` for the no-root headless-Chromium
setup if no browser is available in the sandbox.
