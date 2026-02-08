# any-hook

A collection of customizable pre-commit hooks for Python code quality and transformation tasks.

## Description

`any-hook` is a flexible pre-commit hook framework that provides various code modifiers and validators for Python projects. It uses libcst for AST-based transformations and Pydantic for configuration management.

## Installation

```bash
pip install any-hook
```

For the workflow-env-to-example modifier, install with the optional dependency:

```bash
pip install any-hook[workflow-env-to-example]
```

## Available Modifiers

### object-to-any

Transforms `object` type hints to `Any` for better type checking compatibility.

**What it does:**
- Converts `object` to `Any` in type annotations
- Handles complex types: `list[object]`, `dict[str, object]`, `Union[object, str]`, etc.
- Automatically adds `from typing import Any` if not present
- Leaves non-annotation uses of `object` unchanged (constructors, isinstance, base classes)

**Example:**
```python
# Before
def foo(x: object) -> list[object]:
    return [x]

# After
from typing import Any
def foo(x: Any) -> list[Any]:
    return [x]
```

### local-imports

Detects and reports local imports (imports inside functions or classes).

**What it does:**
- Scans for import statements inside function and class definitions
- Reports violations with file path and import statement
- Respects `# ignore` comments to suppress specific warnings
- Returns non-zero exit code if violations are found

**Example:**
```python
# This will be flagged
def foo():
    import os  # Local import detected
    return os.path

# This will be ignored
def bar():
    import sys  # ignore
    return sys.version
```

### str-enum-tuple

Transforms string enums into tuples for better performance and immutability.

**What it does:**
- Converts string literal enums to tuple definitions
- Improves runtime performance
- Ensures immutability

### pydantic-v1-to-v2

Migrates Pydantic v1 imports to v2 compatibility imports.

**What it does:**
- Transforms `from pydantic import ...` to `from pydantic.v1 import ...`
- Handles various import patterns (simple, from, aliases, star imports)
- Preserves code structure and formatting

**Example:**
```python
# Before
from pydantic import BaseModel

# After
from pydantic.v1 import BaseModel
```

### workflow-env-to-example

Extracts environment variables from GitHub Actions workflow files and generates `.env.example`.

**What it does:**
- Parses GitHub Actions workflow YAML files
- Extracts environment variables from workflow, job, and step levels
- Filters out GitHub secrets and dynamic values
- Maintains existing `.env.example` entries
- Supports custom variable name exclusions

**Requirements:**
- PyYAML (install with `pip install any-hook[workflow-env-to-example]`)

**Example:**
```yaml
# .github/workflows/test.yml
env:
  DATABASE_URL: postgresql://localhost/db
  API_KEY: ${{ secrets.API_KEY }}  # Filtered out
```

Generates `.env.example`:
```bash
DATABASE_URL=postgresql://localhost/db
```

## Usage

### Command Line

```bash
# Basic usage
any-hook file1.py file2.py --modifiers '[{"type": "object-to-any"}]'

# Multiple modifiers
any-hook src/*.py --modifiers '[
    {"type": "object-to-any"},
    {"type": "local-imports"}
]'

# Workflow env extraction
any-hook --modifiers '[{
    "type": "workflow-env-to-example",
    "workflow_paths": [".github/workflows/test.yml"],
    "output_path": ".env.example",
    "ignored_names": ["SECRET_KEY", "API_TOKEN"]
}]'
```

### Pre-commit Integration

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Tesla2000/any-hook
    rev: v0.1.13  # Use the latest version
    hooks:
      - id: any-hook
        args:
          - --modifiers
          - |
            [
              {"type": "object-to-any"},
              {"type": "local-imports"}
            ]
```

### Configuration Examples

#### Check for Local Imports Only
```yaml
- id: any-hook
  args:
    - --modifiers
    - '[{"type": "local-imports"}]'
```

#### Transform object to Any
```yaml
- id: any-hook
  args:
    - --modifiers
    - '[{"type": "object-to-any"}]'
```

#### Migrate Pydantic v1 to v2
```yaml
- id: any-hook
  args:
    - --modifiers
    - '[{"type": "pydantic-v1-to-v2"}]'
```

#### Extract Workflow Environment Variables
```yaml
- id: any-hook
  args:
    - --modifiers
    - |
      [{
        "type": "workflow-env-to-example",
        "workflow_paths": [".github/workflows/ci.yml"],
        "output_path": ".env.example"
      }]
  pass_filenames: false
```

#### Combine Multiple Modifiers
```yaml
- id: any-hook
  args:
    - --modifiers
    - |
      [
        {"type": "object-to-any"},
        {"type": "local-imports"},
        {"type": "pydantic-v1-to-v2"}
      ]
```

## How It Works

1. **File Parsing**: Uses `libcst` to parse Python files into concrete syntax trees (CST)
2. **Transformation**: Applies configured modifiers to the CST
3. **Validation**: Checks for violations and reports them
4. **Output**: Writes transformed code back to files or reports errors
5. **Exit Code**: Returns non-zero if any modifier reports violations

## Development

### Running Tests

```bash
# Run all tests
python -m unittest discover -s any_hook -p "test_*.py"

# Run specific modifier tests
python -m unittest any_hook.files_modifiers.tests.test_object_to_any
python -m unittest any_hook.files_modifiers.tests.test_local_imports
```

### Project Structure

```
any-hook/
├── any_hook/
│   ├── __init__.py
│   ├── __main__.py          # CLI entry point
│   └── files_modifiers/
│       ├── _modifier.py     # Base modifier class
│       ├── object_to_any.py
│       ├── local_imports.py
│       ├── pydantic_v1_to_v2.py
│       ├── workflow_env_to_example.py
│       └── tests/
├── pyproject.toml
└── README.md
```

## Contributing

Contributions are welcome! To add a new modifier:

1. Create a new file in `any_hook/files_modifiers/`
2. Implement the `Modifier` base class
3. Add tests in `any_hook/files_modifiers/tests/`
4. Register the modifier in `any_hook/files_modifiers/__init__.py`

## License

See LICENSE file for details.

## Author

Tesla2000 (fratajczak124@gmail.com)
