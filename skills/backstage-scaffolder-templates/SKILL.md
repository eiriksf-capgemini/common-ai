---
name: backstage-scaffolder-templates
description: Author or debug a Backstage scaffolder Template entity — catalog registration, cross-field validation limits in the parameter form, and Nunjucks-vs-GitHub-Actions delimiter collisions in skeleton files. Use when a template doesn't show up in "Create", a step fails against a catalog entity that "should" exist, or generated CI/workflow files come out mangled.
user-invocable: true
license: MIT
metadata:
  domain: platform-engineering
  tags: backstage scaffolder templates catalog
---

# Backstage scaffolder templates

Built from a real session adding an "AI-first application" template
(`examples/template/ai-first-app/template.yaml`) to a Backstage instance —
covers three gotchas that aren't obvious from the Backstage docs alone.

## 1. A template needs TWO separate registrations, and they fail independently

Dropping a `template.yaml` on disk does nothing by itself. It must be added
as a catalog location, e.g. `app-config.yaml`:

```yaml
catalog:
  locations:
    - type: file
      target: ../../examples/template/ai-first-app/template.yaml
      rules:
        - allow: [Template]
```

Without this, the template simply never appears in "Create" — no error,
it's just absent.

Separately: if any step in the template references a catalog entity by ref
(commonly a `notification:send` step targeting a group, e.g.
`group:default/admin-group` as owner or notification recipient), that entity
must *also* exist in whatever catalog data is registered — e.g. appended to
`examples/org.yaml`:

```yaml
---
apiVersion: backstage.io/v1alpha1
kind: Group
metadata:
  name: admin-group
spec:
  type: team
  children: []
```

These are two unrelated failure modes for one template: the template can
render fine in the UI and still fail at execution time because a referenced
entity isn't registered, or it can be perfectly correct internally and never
show up at all because the location isn't registered. Check both before
assuming the template itself is broken.

## 2. The parameter form cannot see sibling field values at render time

Only scaffolder **step inputs** get Nunjucks-templated, and only after the
user submits the form — the JSON Schema parameter *form* itself is static
per-field and cannot derive one field's default/pattern from another field's
live value while the user is still filling it in. So "make field B's default
depend on field A" or "validate field B against field A's current value" is
not achievable directly in `parameters:`.

The workaround, used for enforcing that a repo name is prefixed with its
business area (`examples/template/ai-first-app/template.yaml:85-132`), is
`dependencies.<field>.oneOf`, pairing each enum value of the driving field
with a `pattern` constraint on the dependent field:

```yaml
dependencies:
  businessArea:
    oneOf:
      - properties:
          businessArea:
            enum: [Marketing]
          repoUrl:
            pattern: '[?&]repo=marketing-'
      - properties:
          businessArea:
            enum: [Finance]
          repoUrl:
            pattern: '[?&]repo=finance-'
      # ... one branch per enum value
```

Gotcha inside the gotcha: `RepoUrlPicker`'s value is not a clean repo-name
string — it's a serialized query string like
`github.com?owner=org&repo=my-app`. The regex has to match the `repo=`
substring within that whole string (`'[?&]repo=marketing-'`), not anchor
against the full value (`^marketing-`), or it will never match.

This pattern only enforces the constraint client-side in the form (via AJV);
it is not a substitute for a step-level check if the template can also be
invoked non-interactively.

## 3. Nunjucks and GitHub Actions share the same `${{ }}` delimiter

The scaffolder templates skeleton files with Nunjucks, which uses `${{ ... }}`
for expressions — the exact same syntax GitHub Actions uses for
`${{ github.sha }}`, `${{ secrets.X }}`, etc. Any file under a template's
`skeleton/` directory that needs to contain a **real** GitHub Actions
expression (as opposed to a scaffolder variable) will have that expression
misinterpreted as Nunjucks and mangled or fail to render, unless it's wrapped
in a Nunjucks raw block in the template source:

```
{% raw %}
${{ github.sha }}
{% endraw %}
```

This only matters for edits to files inside `skeleton/` (pre-scaffold) — once
a repo is generated from the template, the output file is a normal GHA
workflow with no Nunjucks involved, and `${{ }}` behaves normally from then
on. See the comment at the top of
`examples/template/ai-first-app/skeleton/.github/workflows/ci.yml` for the
in-repo note left for the next person editing that file.

If you need to confirm exactly which delimiters Nunjucks is configured with
for a given `@backstage/plugin-scaffolder-backend` version rather than
assuming `${{ }}`/`{% %}` are the defaults, grep the installed
`NunjucksWorkflowRunner` for `variableStart`/`blockStart` in
`node_modules/@backstage/plugin-scaffolder-backend/dist/`.
