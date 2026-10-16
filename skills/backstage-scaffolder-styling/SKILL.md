---
name: backstage-scaffolder-styling
description: Change the look and feel of the Backstage scaffolder's "Create" flow — template card colors/tags, or a full custom TemplateCard via SwappableComponentBlueprint — on the new frontend system. Use when asked to restyle/rebrand the template list or wizard, or to swap out a scaffolder-react component.
user-invocable: true
license: MIT
metadata:
  domain: platform-engineering
  tags: backstage scaffolder theming frontend
---

# Backstage scaffolder styling

Two levels of "change how templates look," built from a real session on the
**new Backstage frontend system** (`createApp` from `@backstage/frontend-defaults`),
confirmed against `@backstage/plugin-scaffolder-react@2.0.2`,
`@backstage/plugin-app-react@0.2.5`, `@backstage/frontend-plugin-api@0.17.3`.
Complements `backstage-design-sync` (whole-app theme/branding) and
`backstage-scaffolder-templates` (template authoring mechanics) — this one is
specifically about the visual presentation of the template list/wizard.

## 1. Cheap win: reuse the existing pageTheme map + tags, no new code

The stock `TemplateCard`'s banner color is driven by the template's
`spec.type`, through the exact same `pageTheme`/`genPageTheme` map documented
in `backstage-design-sync` for catalog pages — so if that skill's theme
module already overrides `pageTheme.home`, extending it with the type(s)
your templates actually use is a two-line change that recolors every
template card for free:

```ts
// packages/app/src/modules/theme/theme.ts
const brand = { ink900: '#061a2b', honoluluBlue: '#0070ad', gammaBlue: '#12abdb' };

const brandPageTheme = {
  ...pageTheme,
  home: genPageTheme({ colors: [brand.ink900, brand.honoluluBlue], shape: shapes.wave }),
  service: genPageTheme({ colors: [brand.honoluluBlue, brand.gammaBlue], shape: shapes.round }),
};
```

Separately, `metadata.tags` on a `Template` entity render as chips on its
card and automatically populate a "Tags" filter in the template list
sidebar — no frontend code at all, just add `tags: [...]` next to
`metadata.title`/`description` in the template's YAML.

## 2. Full replacement: swap `TemplateCard` via `SwappableComponentBlueprint`

`TemplateCard` (and other core components like `Progress`, `NotFoundErrorPage`,
`ErrorDisplay`, `PageLayout`) are "swappable components" — the new frontend
system lets an app replace their implementation entirely by registering a
`SwappableComponentBlueprint` (from `@backstage/plugin-app-react`) that
targets the original component's exported `.ref`. Confirmed by
`@backstage/plugin-scaffolder-react`'s own JSDoc on `TemplateCard`:
"Apps using the new frontend system can replace it by registering a
`SwappableComponentBlueprint` that targets `TemplateCard`."

**Add the dependency explicitly.** `@backstage/plugin-scaffolder-react` is
normally only a hoisted transitive dep of `@backstage/plugin-scaffolder` in
`packages/app` — importing from it directly (needed for the `TemplateCard`
component/type and the `/alpha` entry point) requires adding it to
`packages/app/package.json` pinned to the installed version, same as the
`@backstage/theme` gotcha in `backstage-design-sync`.

**The component** receives `TemplateCardComponentProps` — `{ template,
additionalLinks?, onSelected }`, where `onSelected` is a zero-arg callback
(the surrounding list already binds it to the specific template — just call
it, don't pass arguments). To keep the type-based coloring instead of
hardcoding brand hexes, pull it from the theme the same way the *default*
`CardHeader` does internally (`node_modules/@backstage/plugin-scaffolder-react/dist/next/components/TemplateCard/CardHeader.esm.js`):

```tsx
// packages/app/src/modules/scaffolder/TemplateCard.tsx
import { useTheme } from '@material-ui/core/styles';
import type { TemplateCardComponentProps } from '@backstage/plugin-scaffolder-react/alpha';

export const TemplateCard = ({ template, onSelected }: TemplateCardComponentProps) => {
  const { getPageTheme } = useTheme();
  const themeForType = getPageTheme({ themeId: template.spec.type as string });
  // themeForType.backgroundImage / .fontColor — same pageTheme map as section 1
  // ...render whatever layout you want, call onSelected() from the "Choose" button
};
```

**Register it** — mirrors how `themeModule`/`navModule` are already
registered in this app:

```ts
// packages/app/src/modules/scaffolder/index.ts
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { SwappableComponentBlueprint } from '@backstage/plugin-app-react';
import { TemplateCard as DefaultTemplateCard } from '@backstage/plugin-scaffolder-react/alpha';
import { TemplateCard } from './TemplateCard';

const templateCard = SwappableComponentBlueprint.make({
  name: 'template-card', // must be unique among this module's extensions
  params: define => define({
    component: DefaultTemplateCard, // the ORIGINAL export, used only to carry its `.ref`
    loader: () => TemplateCard,     // your replacement — sync fn or `() => import(...).then(...)`
  }),
});

export const scaffolderModule = createFrontendModule({
  pluginId: 'app',
  extensions: [templateCard],
});
```

Then add `scaffolderModule` to `createApp({ features: [...] })` in `App.tsx`
— forgetting this step is the same "backend/plugin present but never added
to `features[]`" bug class documented in `backstage-plugin-wiring`, except
here it's a module you wrote yourself, not a third-party plugin.

The `params.component` argument's type requires the exact object that
carries the `SwappableComponentRef` (i.e. the real `TemplateCard` export,
not a re-declared type) — passing anything else fails to typecheck, which is
by design: it's how the blueprint knows which swap point you're targeting.

## 3. Other swap points that exist but weren't used here

For future reference, confirmed present in `@backstage/plugin-scaffolder-react/alpha`
but not exercised in this session — reach for these before writing a full
custom `TemplateCard`/page from scratch:

- `FormFieldBlueprint` / `createFormField` — replace a single `ui:field`
  widget in the parameter form with a fully custom component.
- `FormDecoratorBlueprint` — wrap a wizard step with extra UI/behavior
  without replacing the whole form.
- `Stepper`'s `components` prop — swap `ReviewStepComponent`,
  `ReviewStateComponent`, or the back/next/create button labels.
- Theme `overrides` keys `BackstageTemplateStepper` (`backButton`, `footer`,
  `formWrapper`) and `ScaffolderReactTemplateCategoryPicker` — CSS-only
  tweaks via the same `createUnifiedTheme` call as the rest of the app's
  branding, no new components needed.
- `useScaffolderTheme()` returns `'mui' | 'bui'` — Backstage's newer
  "Backstage UI" design system can render the wizard instead of classic
  Material UI; a much bigger visual shift than any single-component swap.
  **Tried and reverted in that session**: it's a pure config flag, no code —
  `app-config.yaml`'s `app.extensions` (same mechanism as step 2 in
  `backstage-homepage`), on the scaffolder's `templates` sub-page:
  ```yaml
  app:
    extensions:
      - sub-page:scaffolder/templates:
          config:
            enableBackstageUi: true
  ```
  (Confirmed via `scaffolderTemplatesSubPage`'s `configSchema` in
  `node_modules/@backstage/plugin-scaffolder/dist/alpha/extensions.esm.js`,
  which feeds `EXPERIMENTAL_theme: config.enableBackstageUi ? 'bui' : 'mui'`
  into `Form`.) Standard RJSF widgets (text/textarea/select) re-skin fine —
  labels move above fields, "(Required)" replaces `*`, selects become
  react-aria-based bui components. **But it broke the `RepoUrlPicker`
  custom `ui:field`**: its "Repository" text input (where the user types
  the repo name) rendered with a label and description but *no input
  element at all* — verified by DOM inspection, not just a screenshot look.
  Any custom `ui:field`/`FormFieldBlueprint` widget written against MUI
  assumptions is a real compatibility risk under `bui` — don't flip this on
  for a template that has one without testing that specific field
  end-to-end first (typecheck and a plain screenshot aren't enough; try to
  actually type into every custom field).

## Verify

Same loop as `backstage-design-sync`: `yarn tsc`, start the dev server, and
actually look at `/create` — a card/theme change can typecheck fine and
still render wrong (or not swap at all, if `features[]` registration was
missed). If no browser is available in the sandbox, `apt-get download` +
`dpkg-deb -x` the missing shared libs (e.g. `libnspr4`, `libnss3`,
`libatk1.0-0t64`, `libcups2t64`, `libgbm1`, `libasound2t64`, `libpango-1.0-0`,
`libpangocairo-1.0-0`, `libx11-6`, `libxcomposite1`, `libxdamage1`,
`libxext6`, `libxfixes3`, `libxkbcommon0`, `libxrandr2`, `libcairo2`,
`libdrm2`, `libexpat1`, `libglib2.0-0t64`) into a scratch directory and run
Playwright/Chromium with `LD_LIBRARY_PATH` pointed at the extracted
`usr/lib/x86_64-linux-gnu` dirs — no root required, works when `sudo` isn't
available to run `playwright install --with-deps`.
