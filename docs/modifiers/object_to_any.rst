ObjectToAny
===========

Type: ``object-to-any``

Converts all uses of ``object`` in type annotations to ``Any`` for better type checking compatibility.

.. autoclass:: any_hook.files_modifiers.object_to_any.ObjectToAny
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

Configuration
-------------

This modifier has no additional configuration parameters beyond the base :class:`~any_hook.files_modifiers._modifier.Modifier` class.

Usage Example
-------------

In your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: object-to-any

Or programmatically:

.. code-block:: python

   from any_hook.files_modifiers.object_to_any import ObjectToAny
   from any_hook._file_data import FileData

   modifier = ObjectToAny()
   # Use modifier.modify(file_data_list)
