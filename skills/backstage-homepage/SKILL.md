---
name: backstage-homepage
description: Build or fix a Backstage landing page ("/") on the new frontend system — installing @backstage/plugin-home, overriding which page owns the root path, and writing custom home-page widgets/layout via HomePageWidgetBlueprint and HomePageLayoutBlueprint. Use when asked for a homepage/dashboard, quick links on "/", or when the stock homepage renders empty.
user-invocable: true
license: MIT
metadata:
  domain: platform-engineering
  tags: backstage homepage frontend
---

# Backstage homepage

Built from a real session adding a landing page to a Backstage app on the
**new frontend system** (`createApp` from `@backstage/frontend-defaults`),
confirmed against `@backstage/plugin-home@0.9.8`,
`@backstage/plugin-home-react@0.1.40`, `@backstage/frontend-app-api@0.16.6`.
The public getting-started docs for Backstage homepages
(`docs/getting-started/homepage`) describe the **legacy** frontend system
(`<Route path="/" element={<HomepageCompositionRoot>...}>`,
`CustomHomepageGrid` composed by hand in `App.tsx`) — check which system the
app is on first (see step 0 of `backstage-design-sync`) before following
that page literally; none of it applies as written to a `createApp`-based
app.

## 1. Install and confirm the alpha entry point

`@backstage/plugin-home` ships a `/alpha` default export for the new
frontend system. Add it (and `@backstage/plugin-home-react`, since you'll
import `HomePageWidgetBlueprint`/`HomePageLayoutBlueprint` from it directly)
as **explicit** dependencies in `packages/app/package.json` pinned to the
installed version — same "hoisted transitive dep isn't enough for a direct
import" gotcha as `@backstage/theme` in `backstage-design-sync` and
`@backstage/plugin-scaffolder-react` in `backstage-scaffolder-templates`.

```tsx
// App.tsx
import homePlugin from '@backstage/plugin-home/alpha';
// features: [..., homePlugin, homeModule]
```

## 2. Put the home page at "/" — it defaults to "/home"

The plugin's `page:home` extension has a baked-in default path of `/home`,
not `/`. Override it declaratively via `app-config.yaml`'s
`app.extensions` array (confirmed against
`@backstage/frontend-app-api`'s `readAppExtensionsConfig` — each array entry
is either a bare extension-id string, or `{ <id>: { config, disabled,
attachTo } }`):

```yaml
app:
  extensions:
    - page:home:
        config:
          path: /
```

If another page (commonly `page:catalog`) was previously configured to own
`/`, remove that override — two extensions both configured to `path: /`
will conflict. Just deleting the other page's override is enough; it falls
back to its own default path (`page:catalog` → `/catalog`).

Also add a sidebar entry — `nav.take('page:home')` in the app's nav module,
next to the existing `nav.take('page:catalog')`/`nav.take('page:scaffolder')`
calls (a freshly scaffolded app's `Sidebar.tsx` already has that pattern for other pages).

## 3. The stock dashboard starts EMPTY — read this before assuming a bug

The default `page:home` layout (`DefaultHomePageLayout` →
`CustomHomepageGrid`) is a drag-and-drop, per-browser-persisted dashboard
(state lives in `storageApiRef`'s `home.customHomepage` bucket). Critically,
`DefaultHomePageLayout` never passes a `config` prop to `CustomHomepageGrid`,
so its computed `defaultLayout` is always `[]` — **every fresh browser sees
an empty grid with "No widgets added. Start by clicking the 'Add widget'
button," regardless of how many widgets you've registered.** This is not a
bug in your setup; it's how the shipped layout behaves. It's the wrong
default for a landing page that should look the same for everyone on first
load.

Fix: write your own layout instead of trying to pre-seed
`CustomHomepageGrid`'s config/local-storage state. `HomePageLayoutBlueprint`
attaches to `page:home`'s `layout` input, which is a **singleton** — so
registering one fully replaces the default, no `SwappableComponentBlueprint`
needed:

```tsx
// modules/home/HomePageLayout.tsx
import Grid from '@material-ui/core/Grid';
import type { HomePageLayoutProps } from '@backstage/plugin-home-react/alpha';

export const HomePageLayout = ({ widgets }: HomePageLayoutProps) => (
  <Grid container spacing={3} style={{ padding: 24 }}>
    {widgets.map((widget, index) => (
      <Grid item xs={12} md={6} key={widget.name ?? index}>
        {widget.component}
      </Grid>
    ))}
  </Grid>
);
```

`widget.component` is already a fully-wrapped card (title header + your
content), built by `HomePageWidgetBlueprint`'s factory — don't re-wrap it in
another `Card`.

## 4. Writing a custom widget (e.g. quick links to templates)

```tsx
// modules/home/index.ts
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { HomePageLayoutBlueprint, HomePageWidgetBlueprint } from '@backstage/plugin-home-react/alpha';
import { HomePageLayout } from './HomePageLayout';
import { QuickLinksContent } from './QuickLinksContent';

const quickLinksWidget = HomePageWidgetBlueprint.make({
  name: 'quick-links',
  params: {
    title: 'Quick Links',
    description: 'Jump straight to a scaffolder template',
    components: () => Promise.resolve({ Content: QuickLinksContent }),
  },
});

const homePageLayout = HomePageLayoutBlueprint.make({
  params: { loader: () => Promise.resolve(HomePageLayout) },
});

export const homeModule = createFrontendModule({
  pluginId: 'home',
  extensions: [quickLinksWidget, homePageLayout],
});
```

Both blueprints have a baked-in `attachTo: { id: 'page:home', input: '...' }`
— don't pass `attachTo` yourself. `components` only needs `{ Content }`;
`Actions`/`Settings`/`ContextProvider` are optional (`ComponentParts` type in
`@backstage/plugin-home-react`).

The built-in `toolkit`/`starred-entities`/`random-joke` widgets that ship
with the plugin keep rendering alongside a custom one automatically (they're
plugin-installed extensions attaching to the same `widgets` input) — no
extra wiring needed to keep them; disable one via the same
`app-config.yaml` `app.extensions` mechanism from step 2
(`- home-page-widget:home/random-joke: false`) if it's not wanted.

## Verify

Same loop as `backstage-design-sync`/`backstage-scaffolder-styling`: `yarn
tsc`, start the dev server, actually load `/` in a browser. A missing
`features[]` registration or a leftover `path: /` conflict between two pages
both typecheck fine and fail silently/visually — this is the same
"registered but not wired" bug class as `backstage-plugin-wiring`, just one
more place it recurs. If no browser is available in the sandbox, see the
no-root Chromium workaround (`apt-get download` + `dpkg-deb -x` +
`LD_LIBRARY_PATH`) documented at the end of `backstage-scaffolder-styling`.
