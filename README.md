# any-hook

[![codecov](https://codecov.io/gh/Tesla2000/any-hook/branch/main/graph/badge.svg)](https://codecov.io/gh/Tesla2000/any-hook)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![PyPI version](https://badge.fury.io/py/any-hook.svg)](https://pypi.org/project/any-hook/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A collection of customizable pre-commit hooks for Python code quality and transformation tasks.

## Description

`any-hook` is a flexible pre-commit hook framework that provides various code modifiers and validators for Python projects. It uses libcst for AST-based transformations and Pydantic for configuration management.

## Table of Contents

- [Installation](#installation)
- [Available Modifiers](#available-modifiers)
  - [agito](#agito)
  - [any-to-object](#any-to-object)
  - [check-untracked](#check-untracked)
  - [combine-with](#combine-with)
  - [field-validator-check](#field-validator-check)
  - [forbidden-functions](#forbidden-functions)
  - [generate-stubs](#generate-stubs)
  - [len-as-bool](#len-as-bool)
  - [local-imports](#local-imports)
  - [local-imports-to-top](#local-imports-to-top)
  - [object-to-any](#object-to-any)
  - [open-to-path](#open-to-path)
  - [pydantic-config-to-model-config](#pydantic-config-to-model-config)
  - [pydantic-v1-to-v2](#pydantic-v1-to-v2)
  - [remove-f-prefix](#remove-f-prefix)
  - [return-tuple-parens-drop](#return-tuple-parens-drop)
  - [str-enum-inheritance](#str-enum-inheritance)
  - [test-if-checker](#test-if-checker)
  - [typing-to-builtin](#typing-to-builtin)
  - [utcnow-to-datetime-now](#utcnow-to-datetime-now)
  - [workflow-env-to-example](#workflow-env-to-example)
- [Documentation](#documentation)

## Documentation

For comprehensive documentation including detailed API reference and configuration options for all modifiers, see the [full documentation](https://github.com/Tesla2000/any-hook/tree/main/docs).

To build the documentation locally:

```bash
pip install -e ".[docs]"
cd docs
make html
```

Then open `docs/_build/html/index.html` in your browser.

## Installation

```bash
pip install any-hook
```

For the workflow-env-to-example modifier, install with the optional dependency:

```bash
pip install any-hook[workflow-env-to-example]
```

For the generate-stubs modifier, install with the optional dependency:

```bash
pip install any-hook[generate-stubs]
```

## Available Modifiers

All modifiers share the following common options:

| Option | Default | Description |
|---|---|---|
| `excluded_paths` | `[]` | Glob patterns for paths to skip (e.g. `"tests/*"`, `"*/migrations/*"`). Cannot be combined with `included_paths`. |
| `included_paths` | `[]` | Glob patterns for paths to include. When set, only matching files are processed. Cannot be combined with `excluded_paths`. |
| `ignore_pattern` | `#\s*ignore` | Regex matched against inline comments to suppress a violation on that line. |

**Example:**
```json
{
  "type": "local-imports",
  "excluded_paths": ["tests/*", "scripts/*"]
}
```

```json
{
  "type": "forbidden-functions",
  "forbidden_functions": ["print"],
  "included_paths": ["src/*"],
  "ignore_pattern": "#\\s*noqa"
}
```

### any-to-object

Transforms `Any` type hints to `object`.

**What it does:**
- Converts `Any` to `object` in type annotations
- Handles complex types: `list[Any]`, `dict[str, Any]`, `Union[Any, str]`, etc.
- Removes `from typing import Any` if it becomes unused (or removes just the alias from a multi-import)
- Leaves non-annotation uses of `Any` unchanged

**Example:**
```python
# Before
from typing import Any
def foo(x: Any) -> list[Any]:
    return [x]

# After
def foo(x: object) -> list[object]:
    return [x]
```

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

### local-imports-to-top

Moves local imports to module level.

**What it does:**
- Converts imports found inside functions or classes to top-level imports
- By default, only moves external and standard library imports
- Keeps project-local (src) imports in their local scopes by default
- Respects `# ignore` comments to suppress specific imports
- Deduplicates imports to avoid duplicating existing top-level imports

**Options:**
- `include_src_imports` (default: `false`) — if `true`, also move relative imports and project-local absolute imports to the top level

**Example — default behavior (external/builtin only):**
```python
# Before
def process():
    import json
    from typing import Dict
    from . import utils
    return json.dumps({})

# After
import json
from typing import Dict
def process():
    from . import utils
    return json.dumps({})
```

**Example — with include_src_imports=true:**
```python
# Before
def process():
    import json
    from . import utils
    return json.dumps({})

# After
import json
from . import utils
def process():
    return json.dumps({})
```

### str-enum-inheritance

Modernizes string enum definitions to use `StrEnum` (Python 3.11+).

**What it does:**
- Converts classes inheriting from both `str` and `Enum` to use `StrEnum`
- Optionally replaces string values with `auto()` when the value matches the member name in lowercase
- Automatically updates imports (`StrEnum`, `auto`), removing `Enum` if no longer needed

**Options:**
- `convert_to_auto` (default: `true`) — replace matching string values with `auto()`
- `convert_existing_str_enum` (default: `true`) — also apply `auto()` conversion to existing `StrEnum` classes

**Example:**
```python
# Before
from enum import Enum
class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

# After
from enum import StrEnum, auto
class Status(StrEnum):
    ACTIVE = auto()
    INACTIVE = auto()
```

### pydantic-config-to-model-config

Migrates Pydantic v1 config patterns to v2 `model_config: ClassVar[ConfigDict] = ConfigDict(...)`.

**What it does:**
- Converts inner `Config` classes to `model_config` assignments using `ConfigDict`
- Converts inline class keyword arguments (`class Foo(BaseModel, frozen=True)`) to `model_config`
- When both a `Config` class and inline kwargs are present, merges them into a single `ConfigDict` call
- When inline kwargs exist alongside an existing `model_config`, merges non-conflicting keys into the existing `ConfigDict`; raises an error if the same key is defined in both places
- Adds `ClassVar[ConfigDict]` type annotation to created or upgraded `model_config` assignments; preserves existing annotations
- Automatically adds `ConfigDict` and `ClassVar` imports if not present

**Options:**
- `config_class_name` (default: `"Config"`) — name of the nested config class to convert

**Example — nested Config class:**
```python
# Before
from pydantic import BaseModel
class User(BaseModel):
    name: str
    class Config:
        frozen = True
        extra = "forbid"

# After
from typing import ClassVar
from pydantic import BaseModel, ConfigDict
class User(BaseModel):
    name: str
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
```

**Example — inline class kwargs:**
```python
# Before
from pydantic import BaseModel
class User(BaseModel, frozen=True):
    name: str

# After
from typing import ClassVar
from pydantic import BaseModel, ConfigDict
class User(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    name: str
```

**Limitations:**
- Only transforms classes that explicitly inherit from `BaseModel` (or its subclasses) defined within the same file. Classes inheriting from Pydantic models imported from other files are not transformed, as the modifier cannot verify their inheritance chain across file boundaries.

### check-untracked

Checks for untracked files in specified directories and signals the hook to fail if any are found.

**What it does:**
- Scans the git index for untracked (`??`) files under the configured directories
- Returns exit code 1 if any untracked files are found (prompting the user to explicitly stage them), 0 otherwise
- Does not stage any files — leaves the decision to the developer

**Options:**
- `directories` (required) — tuple of directory paths to check for untracked files

**Example:**
```json
{"type": "check-untracked", "directories": ["src/generated", "docs"]}
```

**Configuration:**
```yaml
- repo: local
  hooks:
    - id: any-hook
      args:
        - --modifiers
        - '[{"type": "check-untracked", "directories": ["src/generated"]}]'
```

### combine-with

Combines nested `with` and `async with` statements into a single multi-item context manager.

**What it does:**
- Merges consecutive nested `with` or `async with` blocks into a single statement with multiple context items
- Only merges when both nesting levels have the same type (both sync or both async)
- Preserves context item ordering and `as` clauses
- Leaves mixed sync/async nesting unchanged (a `with` wrapping `async with` or vice versa cannot be merged)

**Example:**
```python
# Before
with A:
    with B:
        body

# After
with A, B:
    body
```

**Async example:**
```python
# Before
async with A:
    async with B:
        body

# After
async with A, B:
    body
```

**Mixed sync/async (unchanged):**
```python
# Before — left as-is
with A:
    async with B:
        body
```

### generate-stubs

Generates type stub (`.pyi`) files for specified directories and post-processes them to produce accurate Pydantic model constructors.

**What it does:**
- Runs `stubgen` (from mypy) on the configured directories, writing stubs to `output_dir` (default: `out/`)
- Post-processes each generated stub to replace the generic `**data: Any` constructor on Pydantic models with a precise keyword-only `__init__` signature derived from the class fields
- Excludes `ClassVar` fields and private fields (names starting with `_`) from the generated `__init__`
- Detects Pydantic models by import (`BaseModel`, `BaseSettings`, `RootModel` from `pydantic` or `pydantic.v1`) and by inheritance from already-detected model classes
- Returns exit code 1 if any stub files were created or modified (prompting the user to stage and re-commit)

**Requirements:**
- mypy (install with `pip install any-hook[generate-stubs]`)

**Options:**
- `directories` (required) — source directories to pass to `stubgen`
- `output_dir` (default: `"out"`) — directory where stubs are written

**Example — source model:**
```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int = 30
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    _cache: str  # private field
```

**Generated stub (after post-processing):**
```python
class User(BaseModel):
    name: str
    age: int = ...
    model_config: ClassVar[ConfigDict]
    _cache: str
    def __init__(self, *, name: str, age: int = ...) -> None: ...
```

**Configuration:**
```yaml
- repo: local
  hooks:
    - id: any-hook
      args:
        - --modifiers
        - '[{"type": "generate-stubs", "directories": ["src"], "output_dir": "stubs"}]'
      pass_filenames: false
```

### forbidden-functions

Detects calls to forbidden function names.

**What it does:**
- Reports any direct function calls matching the specified names
- Useful for banning `print`, `eval`, deprecated helpers, etc.
- Only detects simple calls (`func()`) — method calls (`obj.func()`) are not flagged

**Options:**
- `forbidden_functions` (required) — tuple of function names to ban

**Example:**
```python
# Flagged
print("debug info")
result = eval(user_input)

# Suppressed
print("temporary debug")  # ignore
```

**Configuration:**
```json
{"type": "forbidden-functions", "forbidden_functions": ["print", "eval"]}
```

### field-validator-check

Detects misused Pydantic `@field_validator` decorators.

**What it does:**
- Reports validators where `cls` is not used in the method body and the validated fields do not include `"*"`
- Suggests that such validators can likely be simplified

**Example:**
```python
# Flagged — cls unused and field is not "*"
@field_validator("name")
@classmethod
def validate_name(cls, v):
    return v.strip()

# OK — uses "*"
@field_validator("*")
@classmethod
def validate_all(cls, v):
    return cls._clean(v)
```

### utcnow-to-datetime-now

Migrates deprecated `datetime.utcnow()` to timezone-aware `datetime.now(UTC)`.

**What it does:**
- Converts `datetime.utcnow()` → `datetime.now(UTC)` (class-style import)
- Converts `datetime.datetime.utcnow()` → `datetime.datetime.now(datetime.UTC)` (module-style import)
- Converts bare `datetime.utcnow` references to `lambda: datetime.now(UTC)`
- Automatically adds `UTC` to the `datetime` import when needed

**Example:**
```python
# Before
from datetime import datetime
now = datetime.utcnow()
factory = datetime.utcnow

# After
from datetime import datetime, UTC
now = datetime.now(UTC)
factory = lambda: datetime.now(UTC)
```

### len-as-bool

Removes unnecessary `len()` calls in boolean contexts.

**What it does:**
- Simplifies `if len(x):` → `if x:`
- Simplifies `if not len(x):` → `if not x:`
- Simplifies `bool(len(x))` → `bool(x)`
- Also applies to `while` conditions

**Example:**
```python
# Before
if len(items):
    process(items)
while len(queue):
    queue.pop()

# After
if items:
    process(items)
while queue:
    queue.pop()
```

### test-if-checker

Detects conditional logic in test functions that should be parametrized instead.

**What it does:**
- Identifies `if`/`elif`/`else` statements in test functions
- Detects inline if expressions (ternary operator) in test code
- Allows conditional logic in nested function definitions (test helpers/factories)
- Respects parametrization decorators and other configured ignore decorators
- Reports file path and line number in standard format

**Violations detected:**
- Top-level conditional statements in test functions
- Ternary (inline if) expressions in test code
- Nested if statements that can be parametrized

**Options:**
- `test_file_pattern` (default: `test_.*\.py$`) — regex to identify test files
- `test_function_pattern` (default: `^test_`) — regex to identify test functions
- `ignored_decorators` (default: `("pytest.mark.parametrize",)`) — decorators that suppress checks

**Examples:**
```python
# Violation — should use parametrize
def test_values():
    if value > 0:
        assert True
    else:
        assert False

# Allowed — parametrized test
@pytest.mark.parametrize("value", [1, 2, 3])
def test_with_params(value):
    assert value > 0

# Allowed — nested function (test helper)
def test_something():
    def validate(x):
        if x < 0:
            return False
        return True
    assert validate(10)

# Allowed — custom decorator
@pytest.mark.skip
def test_skipped():
    if condition:
        assert True
```

### typing-to-builtin

Modernizes type hints from `typing` module to builtin equivalents (Python 3.9+).

**What it does:**
- Converts `Dict` → `dict`, `List` → `list`, `Set` → `set`, `FrozenSet` → `frozenset`, `Tuple` → `tuple`, `Type` → `type`
- Only replaces names used in annotations
- Automatically removes now-unused `typing` imports

**Example:**
```python
# Before
from typing import Dict, List
def foo(x: Dict[str, List[int]]) -> None:
    pass

# After
def foo(x: dict[str, list[int]]) -> None:
    pass
```

### return-tuple-parens-drop

Removes redundant parentheses from single-line tuple return values.

**What it does:**
- Converts `return (a, b)` → `return a, b` for one-liner returns
- Leaves multi-line tuples unchanged
- Leaves empty tuples `return ()` and single non-tuple values `return (x)` unchanged

**Example:**
```python
# Before
def foo():
    return (x, y)

# After
def foo():
    return x, y
```

### remove-f-prefix

Removes the `f` prefix from f-strings that contain no placeholders.

**What it does:**
- Converts `f"text"` → `"text"` when the string has no `{...}` expressions
- Handles all quote styles: `f"..."`, `f'...'`, `f"""..."""`, `f'''...'''`
- Leaves f-strings with placeholders unchanged

**Example:**
```python
# Before
x = f"hello world"
msg = f"""no placeholders here"""

# After
x = "hello world"
msg = """no placeholders here"""
```

### open-to-path

Converts `with open()` context managers to `Path.read_text` / `write_text` / `read_bytes` / `write_bytes` calls.

**What it does:**
- Replaces single-body `with open(path) as f: content = f.read()` with `content = Path(path).read_text()`
- Handles all common modes: `"r"` / `"rt"` / default → `read_text`, `"rb"` → `read_bytes`, `"w"` / `"wt"` → `write_text`, `"wb"` → `write_bytes`
- Passes through compatible kwargs: `encoding`, `errors` (text modes); `newline` (write only)
- Supports multiple opens in one `with` statement when each body statement uses one handle
- Automatically adds `from pathlib import Path` if not present
- Skips if body has multiple statements per handle, unknown mode, or incompatible kwargs (`closefd`, etc.)

**Example:**
```python
# Before
with open("data.txt", encoding="utf-8") as f:
    content = f.read()

with open("out.txt", "w") as a, open("log.txt", "w") as b:
    a.write(result)
    b.write(summary)

# After
from pathlib import Path
content = Path("data.txt").read_text(encoding="utf-8")
Path("out.txt").write_text(result)
Path("log.txt").write_text(summary)
```

### agito

Named after the shikigami from *Jujutsu Kaisen* born when Sukuna, wielding Megumi's Ten Shadows Technique, sacrifices all other shikigami and fuses them into one overwhelming entity — all except the Divine General Mahoraga. Agito fuses the power of every modifier it holds, running their transformations in a single CST pass per file instead of one pass each.

**What it does:**
- Merges all transformer-based modifiers (`SeparateModifier` subclasses) into one tree traversal per file
- Eliminates redundant CST walks and reduces file writes to at most one per file
- Checker-type modifiers (`forbidden-functions`, `field-validator-check`, `local-imports`) run after the combined transform since they only read the tree
- `workflow-env-to-example` is the Mahoraga of the system — too autonomous to be absorbed and should be kept outside Agito

**Options:**
- `modifiers` (required) — list of modifier configs to combine

**Example:**
```json
{
  "type": "agito",
  "modifiers": [
    {"type": "len-as-bool"},
    {"type": "typing-to-builtin"},
    {"type": "return-tuple-parens-drop"},
    {"type": "forbidden-functions", "forbidden_functions": ["print"]}
  ]
}
```

**Pre-commit shortcut:** set `convert_to_agito: true` (the default) on the CLI and pass modifiers normally — the runner wraps them in Agito automatically.

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
