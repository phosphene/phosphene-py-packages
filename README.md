# phosphene-py-packages

Public distribution repository for Phosphene ecosystem Python packages.

This repository provides standalone distributions of core Phosphene libraries for consumption by autonomous agents, external tools, and sub-projects without requiring private repository tokens or submodules.

---

## Included Packages

| Package | Description | Version |
|---|---|---|
| **`phosphene-core`** | Shared foundation models & axiomatic base classes (`InvariantStatic`, `MutableDynamic`, etc.) | `0.1.0` |
| **`phosphene-mdrag`** | Extensible Scientific Markdown Orchestration engine (block rules, morphisms, discovery) | `0.1.0` |
| **`phosphene-frontmatters`** | Graduated discovery registry & contract management for platform markdown assets | `0.1.0` |
| **`phosphene-spatiograph`** | Canonical Spatio-Graphic Archival Engine, RO-Crate 1.1 Packaging, BagIt Intake & IIIF 3.0 Projection | `0.1.0` |

---

## Installation

### 1. Using `uv` (Recommended)

You can install individual packages directly via Git subdirectories without needing personal access tokens:

```bash
# Add phosphene-mdrag
uv add "phosphene-mdrag @ git+https://github.com/phosphene/phosphene-py-packages.git#subdirectory=packages/phosphene-mdrag"

# Add phosphene-frontmatters
uv add "phosphene-frontmatters @ git+https://github.com/phosphene/phosphene-py-packages.git#subdirectory=packages/phosphene-frontmatters"

# Add phosphene-core
uv add "phosphene-core @ git+https://github.com/phosphene/phosphene-py-packages.git#subdirectory=packages/phosphene-core"
```

Or declare them directly in your project's `pyproject.toml`:

```toml
[project]
dependencies = [
    "phosphene-mdrag",
]

[tool.uv.sources]
phosphene-mdrag = { git = "https://github.com/phosphene/phosphene-py-packages.git", subdirectory = "packages/phosphene-mdrag" }
```

### 2. Pre-Built Wheels via GitHub Releases

Tagged releases provide `.whl` artifacts attached directly to GitHub Releases:

```bash
uv pip install "https://github.com/phosphene/phosphene-py-packages/releases/download/v0.1.0/phosphene_mdrag-0.1.0-py3-none-any.whl"
```

---

## CI / Release Automation

* **Build & Verification:** Every push and pull request triggers `.github/workflows/build-and-release.yml`, which builds wheels for all packages in `packages/*` and tests cross-package imports in a clean virtual environment.
* **Release Publishing:** Pushing a tag (e.g. `v0.1.0` or `pkg-mdrag-0.1.0`) automatically builds and publishes the distribution wheels as release assets on GitHub Releases.
