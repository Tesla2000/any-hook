LocalImports
============

Type: ``local-imports``

Detects and reports import statements that appear inside function or class definitions rather than
at module level. Local imports can hide dependencies and make code harder to maintain.

.. autoclass:: any_hook.files_modifiers.local_imports.LocalImports
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

Configuration Parameters
------------------------

**ignore_pattern** (str, default: r"#\\s*ignore")
    Regex pattern to match ignore comments that suppress local import warnings.

Usage Example
-------------

In your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: local-imports

With custom ignore pattern:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: local-imports
           args: ['--ignore-pattern=#\\s*noqa']

Or programmatically:

.. code-block:: python

   from any_hook.files_modifiers.local_imports import LocalImports

   modifier = LocalImports(ignore_pattern=r"#\s*skip")
   # Use modifier.modify(file_data_list)

Suppressing Warnings
--------------------

Add a comment matching the ignore pattern on the same line as the import:

.. code-block:: python

   def dynamic_loader():
       import importlib  # ignore
       return importlib.import_module("plugin")

This import will not trigger a violation.
