# Template: Library / Package

README template for a shared library or package published to npm, Maven, PyPI, NuGet or similar. Replace `{placeholders}` with actual values.

---

# {Library Name}

{One-sentence description of what this library does — under 120 characters.}

[![CI]({ci-badge-url})]({ci-url})
[![License: {license}]({license-badge-url})]({license-url})

## Installation

```bash
# npm
npm install {package-name}

# yarn
yarn add {package-name}
```

{Or for JVM:}

```kotlin
dependencies {
    implementation("{group-id}:{artifact-id}:{version}")
}
```

## Usage

```{language}
import { {mainExport} } from '{package-name}'

{minimal-working-example}
```

## API

### `{functionName}({params})`

{Description of what it does.}

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| {name} | {type} | {description} |

**Returns:** {return type and description}

{Repeat for main exports. For large APIs, link to generated docs.}

## Compatibility

| Platform / Runtime | Version |
|---|---|
| {Node.js} | {≥ 22} |
| {TypeScript} | {≥ 5.0} |

## Examples

### {Use case 1}

```{language}
{code example}
```

### {Use case 2}

```{language}
{code example}
```

{For more examples, see [`examples/`](examples/).}

## Development

```bash
git clone https://github.com/{org}/{library-name}
cd {library-name}
{install-command}
{test-command}
{build-command}
```

## Contributing

1. Fork and clone the repo
2. Create a branch from `main`
3. Run `{check-command}` before pushing
4. Open a PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

[{License}](LICENSE)
