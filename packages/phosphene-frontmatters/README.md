# phosphene.frontmatters

**High-Fidelity Markdown Frontmatter Synchronization**

`phosphene.frontmatters` is a specialized engine for reading, validating, and synchronizing YAML frontmatter in Markdown documents while preserving human-authored formatting, comments, and structure.

## Key Features

- **Polite Automation**: Uses a "Shadow Patch" pattern to project updates from an "Ideal" model onto a preserved `ruamel.yaml` shadow object.
- **Open-World Support**: Natively supports the `OpenRecord` protocol, allowing for high-fidelity synchronization of un-schemaed metadata without discarding unknown fields.
- **Comment Preservation**: Ensures that human-authored comments (inline and block) are maintained during automated synchronization.
- **High-Fidelity Extraction**: Manually parses `---` delimiters to capture exact raw YAML strings, bypassing destructive higher-level abstractions.
- **Bare Key Migration**: Automatically detects and migrates legacy "bare key" frontmatter (YAML at the start of a file without delimiters) to standard `---` blocks.
- **Morphological Control**: Supports `YamlStyle` annotations (via `typing.Annotated`) to enforce specific YAML styles like block scalars (`|`, `>`) or double-quoted strings.
- **BDD-Verified**: Hardened through a rigorous Behavior-Driven Development (BDD) suite enforcing synchronization precision.

## Installation

```bash
# Using uv (recommended)
uv add phosphene-frontmatters
```

## Quick Start

### Basic Synchronization

```python
from pydantic import BaseModel
from phosphene.frontmatters import parse, write

class RegistryModel(BaseModel):
    uri: str
    status: str

text = """---
# Registry Info
uri: platform.skills/precision
status: living  # current state
---
# Content
Body text.
"""

# Load with high-fidelity shadow preservation
result = parse(text, model_cls=RegistryModel)

# Update the "Ideal" model
result.model.status = "settled"

# Save back with preserved comments
updated_text = write(result)
print(updated_text)
# Output will maintain '# Registry Info' and '# current state'
```

### Using YamlStyle Annotations

```python
from typing import Annotated
from phosphene.frontmatters.annotations import YamlStyle

class DocumentModel(BaseModel):
    description: Annotated[str, YamlStyle(scalar_style="|")]
```

## Development

### Running Tests

Execute the BDD verification suite:

```bash
uv run behave
```

Execute unit tests:

```bash
uv run pytest
```

## License

MIT © 2026 Edward Phillips (phosphene.com)
