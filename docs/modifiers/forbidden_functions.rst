ForbiddenFunctions
==================

Type: ``forbidden-functions``

Detects and reports calls to forbidden function names. Useful for enforcing code standards,
preventing deprecated API usage, or blocking unsafe operations.

.. autoclass:: any_hook.files_modifiers.forbidden_functions.ForbiddenFunctions
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

Configuration Parameters
------------------------

**ignore_pattern** (str, default: r"#\\s*ignore")
    Regex pattern to match ignore comments that suppress forbidden function warnings.

**forbidden_functions** (tuple[str, ...], required)
    Tuple of function names that should not be called in the codebase.

Usage Example
-------------

In your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: forbidden-functions
           args: ['--forbidden-functions=print,eval,exec']

With custom ignore pattern:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: forbidden-functions
           args:
             - '--forbidden-functions=print,eval'
             - '--ignore-pattern=#\\s*noqa'

Or programmatically:

.. code-block:: python

   from any_hook.files_modifiers.forbidden_functions import ForbiddenFunctions

   modifier = ForbiddenFunctions(
       forbidden_functions=("print", "eval", "exec"),
       ignore_pattern=r"#\s*allow"
   )
   # Use modifier.modify(file_data_list)

Suppressing Warnings
--------------------

Add a comment matching the ignore pattern on the same line as the function call:

.. code-block:: python

   print("temporary debug info")  # ignore

This call will not trigger a violation.

Limitations
-----------

This modifier only detects simple function calls like ``func()``. It does not detect:

* Method calls like ``obj.method()``
* Attribute access like ``module.func()``
* Dynamic calls via variables

For more sophisticated detection, consider using tools like ``flake8`` with custom plugins.
