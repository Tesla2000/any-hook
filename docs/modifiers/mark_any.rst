MarkAny
=======

Type: ``mark-any``

Detects and reports usages of ``Any`` in type annotations, without modifying files. Unlike
``AnyToObject``, this modifier only flags violations for review rather than rewriting them.

.. autoclass:: any_hook.files_modifiers.mark_any.MarkAny
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

Configuration Parameters
------------------------

**ignore_pattern** (str, default: r"#\\s*ignore")
    Regex pattern to match ignore comments that suppress ``Any`` usage warnings.

Usage Example
-------------

In your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: mark-any

With custom ignore pattern:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: mark-any
           args: ['--ignore-pattern=#\\s*noqa']

Or programmatically:

.. code-block:: python

   from any_hook.files_modifiers.mark_any import MarkAny

   modifier = MarkAny(ignore_pattern=r"#\s*skip")
   # Use modifier.modify(file_data_list)

Suppressing Warnings
--------------------

Add a comment matching the ignore pattern on the same line as the annotation:

.. code-block:: python

   def foo(x: Any) -> Any:  # ignore
       return x

This usage will not trigger a violation.
