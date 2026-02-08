PydanticV1ToV2
==============

Type: ``pydantic-v1-to-v2``

Migrates ``pydantic.v1`` imports to direct ``pydantic`` imports, removing the v1 compatibility layer.

.. autoclass:: any_hook.files_modifiers.pydantic_v1_to_v2.PydanticV1ToV2
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
         - id: pydantic-v1-to-v2

Or programmatically:

.. code-block:: python

   from any_hook.files_modifiers.pydantic_v1_to_v2 import PydanticV1ToV2

   modifier = PydanticV1ToV2()
   # Use modifier.modify(file_data_list)

Related Modifiers
-----------------

* :doc:`pydantic_config_to_model_config` - Completes the Pydantic v1 to v2 migration by converting Config classes
