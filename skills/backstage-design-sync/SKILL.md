---
name: backstage-design-sync
description: Apply a design system (from a claude.ai/design project, or hex/font values given directly) to a Backstage app's actual look and feel — theme, branding, sign-in page. Use when the user wants to reskin/rebrand a Backstage instance, connect it to a Claude Design project, or asks why some Backstage page "still looks like the old/default design" after a theme change.
user-invocable: true
license: MIT
metadata:
  domain: platform-engineering
  tags: backstage theming branding design-system
---

# Backstage design sync

Wires a design system's real tokens (colors, typography, brand) into a Backstage app that uses the **new Backstage frontend system** (`createApp` from `@backstage/frontend-defaults`). Built from a real session applying a corporate design system to a scaffolded Backstage app — the API details below were confirmed against installed `node_modules` type definitions, not assumed from older Backstage docs, because most public tutorials describe the legacy `app-defaults` theming API which does **not** apply here.

## 0. Confirm which frontend system this app uses

Read `packages/app/src/App.tsx`. If it imports `createApp` from `@backstage/frontend-defaults`, you're on the **new frontend system** — everything below applies as written. If it imports `createApp` from `@backstage/app-defaults` (legacy), this skill's API calls don't apply; that app takes a `themes: [...]` array directly in `createApp()` — look up the legacy `UnifiedThemeProvider`/`themes` pattern instead, don't force-fit `ThemeBlueprint`.

Also check the installed version of `@backstage/frontend-plugin-api` / `@backstage/plugin-app-react` in `node_modules` before trusting any API shape below — Backstage's new frontend system moved things between packages at least once already (`ThemeBlueprint` etc. moved from `@backstage/frontend-plugin-api` to `@backstage/plugin-app-react` as of `frontend-plugin-api@0.14.0`). If a documented import fails to resolve, grep the actual installed `.d.ts` files rather than guessing at a different version's API.

## 1. Get the design tokens

**If the user points at a claude.ai/design project** (a URL like `claude.ai/design/p/<uuid>`): that page is a client-rendered SPA — `WebFetch` on the URL only returns the shell, never real content. Use the `DesignSync` tool instead (load it via `ToolSearch(query: "select:DesignSync")` if not already available):

```
DesignSync(method: "get_project", projectId: "<uuid>")   # confirm it exists, type PROJECT_TYPE_DESIGN_SYSTEM
DesignSync(method: "list_files", projectId: "<uuid>")     # see what's actually in it
DesignSync(method: "get_file", projectId: "<uuid>", path: "tokens/colors.css")
```

A design system built by Claude Design typically has a `tokens/` directory with `colors.css`, `typography.css`, `fonts.css`, `radii.css`, `spacing.css`, `shadows.css` (CSS custom properties), plus `readme.md` explaining sourcing/rationale and `guidelines/*.html` specimen cards. Read the token files directly — they're the ground truth. Read `readme.md` too: it typically documents what's a **real** source value (e.g. brand hex codes from an actual logo) versus a **placeholder/substitution** the design agent made because no real asset was attached (e.g. "no logo file was provided," "no corporate font files — using Roboto as placeholder"). Carry that distinction into the implementation — don't treat a flagged placeholder as final brand truth, and tell the user what's still a placeholder.

**If the user gives hex codes/font names directly**, skip DesignSync and use those values as-is.

## 2. Wire the theme via `ThemeBlueprint`

Do not use `createApp({ themes: [...] })` — that's the legacy API and doesn't exist on `createApp` from `@backstage/frontend-defaults`.

Check `packages/app/package.json` for `@backstage/theme` as a **direct** dependency — it's commonly present only as a hoisted transitive dep (pulled in by `@backstage/plugin-app` etc.) without being declared. If you import from it directly, add it explicitly (check installed version in `node_modules/@backstage/theme/package.json` and pin to that).

Create a theme module mirroring whatever pattern the app already uses for its sidebar/nav module (look for `createFrontendModule({ pluginId: 'app', extensions: [...] })` — e.g. in `packages/app/src/modules/nav/index.ts`), e.g. `packages/app/src/modules/theme/`:

`theme.ts`:
```ts
import { createUnifiedTheme, palettes, pageTheme, genPageTheme, shapes } from '@backstage/theme';

const fontFamily = '"Roboto", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'; // from the DS

// See step 3 — Backstage's page-theme banner is a SEPARATE color table from `palette`.
const brandPageTheme = {
  ...pageTheme,
  home: genPageTheme({ colors: ['#061a2b', '#0070ad'], shape: shapes.wave }),
};

export const lightTheme = createUnifiedTheme({
  palette: {
    ...palettes.light,
    primary: { main: '#0070ad' },
    secondary: { main: '#12abdb' },
    background: { default: '#f7f9fa', paper: '#ffffff' },
    navigation: {
      ...palettes.light.navigation,
      background: '#061a2b',
      indicator: '#12abdb',
      color: '#c0dfee',
      selectedColor: '#ffffff',
    },
  },
  fontFamily,
  defaultPageTheme: 'home',
  pageTheme: brandPageTheme,
});

export const darkTheme = createUnifiedTheme({ /* same shape, dark variant */ });
```

`index.tsx`:
```tsx
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { ThemeBlueprint } from '@backstage/plugin-app-react';
import { UnifiedThemeProvider } from '@backstage/theme';
import { lightTheme, darkTheme } from './theme';

const LightTheme = ThemeBlueprint.make({
  name: 'light',
  params: {
    theme: {
      id: 'light',
      title: 'Light Theme',
      variant: 'light',
      Provider: ({ children }) => (
        <UnifiedThemeProvider theme={lightTheme}>{children}</UnifiedThemeProvider>
      ),
    },
  },
});

const DarkTheme = ThemeBlueprint.make({
  name: 'dark',
  params: {
    theme: {
      id: 'dark',
      title: 'Dark Theme',
      variant: 'dark',
      Provider: ({ children }) => (
        <UnifiedThemeProvider theme={darkTheme}>{children}</UnifiedThemeProvider>
      ),
    },
  },
});

export const themeModule = createFrontendModule({
  pluginId: 'app',
  extensions: [LightTheme, DarkTheme],
});
```

Register it in `App.tsx`:
```tsx
import { themeModule } from './modules/theme';
export default createApp({ features: [catalogPlugin, /* ... */, themeModule] });
```

Key facts confirmed against `@backstage/plugin-app-react@0.2.5` / `@backstage/frontend-plugin-api@0.17.3`:
- `ThemeBlueprint`'s `AppTheme` params need `{ id, title, variant: 'light'|'dark', Provider }` — not a raw `UnifiedTheme` or a bare function.
- The blueprint's default `attachTo` is `{ id: 'api:app/app-theme', input: 'themes' }`, baked in — you don't pass `attachTo` yourself.
- It must be wrapped in `createFrontendModule`; a bare `ThemeBlueprint.make()` result is not itself a `FrontendFeature` and cannot go directly into `features: [...]`.

## 3. Don't stop at `palette` — fix the page-theme banner too

Backstage has a **second, independent color table** for the colored header band on certain pages (the sign-in page, and any page rendering `<Page themeId="home">` or similar) — `pageTheme`/`genPageTheme`/`shapes`, also from `@backstage/theme`. It is NOT derived from `palette.primary`/`secondary`. If you only override `palette`, the sign-in page (and Backstage's default "home" banner) will still show the stock teal/green gradient (`#005B4B`) — this is the single most common "why does this one page still look unthemed" symptom.

- `genPageTheme({ colors: string[], shape })` — `colors` is always an array (2 colors = gradient stops); `shape` is one of `shapes.wave`, `shapes.wave2`, `shapes.round`, `shapes.square`.
- `pageTheme` (the built-in map) has keys: `home, documentation, tool, service, website, library, other, app, apis, card`.
- **`createUnifiedTheme`'s `pageTheme` option replaces the whole map, it does not merge.** Always spread the built-in `pageTheme` first (`{ ...pageTheme, home: genPageTheme(...) }`) or every other themeId resolves to `undefined` unless it happens to equal `defaultPageTheme`.
- Set `defaultPageTheme: 'home'` alongside it (matches the built-in default, but be explicit).

## 4. Branding assets — small, easy to forget

- Logo components (commonly `packages/app/src/modules/nav/LogoFull.tsx` / `LogoIcon.tsx`): usually just a `makeStyles` `fill` color on an existing SVG path — recolor to the brand accent. Don't invent a new logo shape unless the design system actually shipped a real logo file (check its readme/assets — many placeholder DSes explicitly flag "no logo file provided, wordmark stands in").
- `packages/app/public/manifest.json`: `theme_color`, `background_color`.
- `packages/app/public/index.html`: `<meta name="theme-color">`, and add a `<link rel="stylesheet" href="...fonts.googleapis.com...">` (or self-hosted `@font-face`) if the DS specifies a webfont not already loaded.
- `app-config.yaml`: `app.title`, `organization.name` — cosmetic but part of "look and feel," trivial to update alongside everything else.

## 5. Adjacent check: a page "looks old" may be unregistered, not unthemed

Before assuming a themeless-looking page is a theme-propagation bug, check whether the plugin is actually registered at all, either through `app.packages: all` auto-discovery (see the correction below) or explicitly in `features: [...]` in `App.tsx`. In one real case, `@backstage/plugin-catalog-import` was a listed `package.json` dependency but never imported/added to `features` — its page never mounted, so what the user saw was a 404/not-found page (which *does* inherit the theme's chrome), not a broken theme. Fix: import the plugin's `/alpha` entry point and add it to `features`.

**Correction (superseded claim, keep for context):** an earlier version of this
skill asserted that `app-config.yaml`'s `app.packages: all` never actually
auto-discovers anything because nothing populates
`window["__@backstage/discovered__"]` in `@backstage/cli@0.36.4` /
`@backstage/frontend-defaults@0.5.4`. That was wrong, at least for that
app's dev server. Directly confirmed by evaluating
`window["__@backstage/discovered__"]` in a live `yarn start` session: it
contained 31 modules, including every `@backstage/plugin-*` package listed
in `packages/app/package.json` (both default and `/alpha` exports). The
producer is a build-time **virtual module** injected by the CLI's
rspack-based dev bundler — `./node_modules/__backstage-autodetected-plugins__.js`
— visible by grepping the served `vendor.js` chunk for
`__@backstage/discovered__` (it isn't a real file on disk, so it won't show
up in a `node_modules` file grep, only in the compiled bundle). It runs
before `main.js` (loaded first via `<script defer>` order), so it's
populated in time for `createApp()`'s `discoverAvailableFeatures()` call.

Practical upshot: **before diagnosing "backend/dependency present but
frontend missing" as a `features[]` registration bug, check whether
`app.packages: all` is set and whether the page/plugin actually already
works** — it may already be auto-discovered, and adding it to `features[]`
explicitly is then redundant (harmless, but not the fix). Confirm via the
`window["__@backstage/discovered__"]` inspection above, or just test the
page directly, before writing an explicit-registration fix. This doesn't
necessarily generalize to other CLI/bundler versions or to production
builds (`yarn build`) — re-verify the `vendor.js`/equivalent chunk for the
`__backstage-autodetected-plugins__` virtual module on a different setup
rather than assuming either behavior.

## 6. Verify

1. `yarn tsc` (repo root script, not per-workspace) — must be clean.
2. Kill any stray dev server first (`pgrep -af "backstage-cli|yarn start"`, `pkill -f "backstage-cli repo start"`) — a leftover instance causes `EADDRINUSE` on the next `yarn start` and produces misleading errors.
3. `yarn start` in the background, poll `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/` until 200/304.
4. Check the log for real errors, filtering out known-benign noise: `kubernetes` "config missing" warnings, `signals`/WebSocket guest-auth JWKS warnings — both are pre-existing in a fresh scaffold and unrelated to theming.
5. Confirm the new colors actually landed by grepping the served bundle: `curl -s http://localhost:3000/main.js | grep -o '<hex>'` (and grep for the OLD default hex, e.g. `005B4B` for the stock page-theme teal, to confirm it's gone).
6. Confirm `<title>` via `curl -s http://localhost:3000/ | grep -o "<title>[^<]*</title>"` if `app.title` changed.
7. Stop the dev server when done (`pkill -f "backstage-cli repo start"`) — don't leave it running.

## Notes on environment

If working over a WSL-mounted repo from a Windows Bash/PowerShell tool, plain `node`/`yarn` may not be on that shell's PATH — invoke via `wsl.exe -d <distro> -- bash -lic '...'` (interactive login shell) to pick up nvm-managed Node/Yarn.
