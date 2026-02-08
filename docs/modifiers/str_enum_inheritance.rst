StrEnumInheritance
==================

Type: ``str-enum-inheritance``

Modernizes string enum definitions by converting classes that inherit from both ``str`` and ``Enum``
to use the ``StrEnum`` base class (Python 3.11+). Optionally converts string values to ``auto()``.

.. autoclass:: any_hook.files_modifiers.str_enum_inheritance.StrEnumInheritance
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

Configuration Parameters
------------------------

**convert_to_auto** (bool, default: True)
    Convert string enum values to auto() when the value matches the member name in lowercase.

**convert_existing_str_enum** (bool, default: True)
    Also process classes already using StrEnum (for auto() conversion).

Usage Example
-------------

In your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: str-enum-inheritance

Disable auto() conversion:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: str-enum-inheritance
           args: ['--no-convert-to-auto']

Or programmatically:

.. code-block:: python

   from any_hook.files_modifiers.str_enum_inheritance import StrEnumInheritance

   # With auto() conversion
   modifier = StrEnumInheritance(convert_to_auto=True)

   # Without auto() conversion
   modifier = StrEnumInheritance(convert_to_auto=False)
   # Use modifier.modify(file_data_list)

Notes
-----

The ``auto()`` conversion only applies when the string value matches the member name in lowercase.
For example, ``ACTIVE = "active"`` becomes ``ACTIVE = auto()``, but ``ACTIVE = "enabled"`` remains unchanged.
