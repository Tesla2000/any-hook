WorkflowEnvToExample
====================

Type: ``workflow-env-to-example``

Extracts environment variables from GitHub Actions workflow files (or similar YAML configs) and
maintains a ``.env.example`` file with all discovered variables.

.. autoclass:: any_hook.files_modifiers.workflow_env_to_example.WorkflowEnvToExample
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

Configuration Parameters
------------------------

**workflow_paths** (tuple[Path, ...], required)
    Paths to workflow files to extract env variables from

**output_path** (Path, default: Path(".env.example"))
    Path to the .env.example file to write to

**source_comment_prefix** (str, default: "# From: ")
    Prefix used for source comments in the output file

**ignored_names** (tuple[str, ...], default: ())
    Environment variable names to ignore and not add to .env.example

Usage Example
-------------

In your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: workflow-env-to-example
           args:
             - '--workflow-paths=.github/workflows/test.yml'
             - '--workflow-paths=.github/workflows/deploy.yml'

With ignored variables:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: workflow-env-to-example
           args:
             - '--workflow-paths=.github/workflows/test.yml'
             - '--ignored-names=GITHUB_TOKEN,CI'

Or programmatically:

.. code-block:: python

   from pathlib import Path
   from any_hook.files_modifiers.workflow_env_to_example import WorkflowEnvToExample

   modifier = WorkflowEnvToExample(
       workflow_paths=(
           Path(".github/workflows/test.yml"),
           Path(".github/workflows/deploy.yml"),
       ),
       output_path=Path(".env.example"),
       ignored_names=("GITHUB_TOKEN", "CI")
   )
   # Use modifier.modify(file_data_list)

How It Works
------------

1. Scans specified workflow files for ``env:`` sections
2. Extracts variable names and values
3. Skips variables with template syntax like ``${{ secrets.FOO }}``
4. Preserves existing variables in ``.env.example``
5. Adds new variables under source file section headers
6. Groups variables by source file

Example Output
--------------

Given workflow file ``.github/workflows/test.yml``:

.. code-block:: yaml

   jobs:
     test:
       env:
         DATABASE_URL: postgres://localhost
         API_KEY: ""
         SECRET: ${{ secrets.API_SECRET }}

Generates ``.env.example``:

.. code-block:: text

   # From: .github/workflows/test.yml
   DATABASE_URL=postgres://localhost
   API_KEY=

Note that ``SECRET`` is excluded because it uses GitHub Actions template syntax.

Notes
-----

* Existing variables are never overwritten or modified
* Variables with ``${{`` in their value are automatically excluded
* Source sections are preserved across runs
* New variables are added to existing source sections when possible
