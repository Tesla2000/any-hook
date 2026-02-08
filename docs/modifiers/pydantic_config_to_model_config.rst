PydanticConfigToModelConfig
===========================

Type: ``pydantic-config-to-model-config``

Converts Pydantic v1 nested Config classes to v2 model_config assignments using ConfigDict.

.. autoclass:: any_hook.files_modifiers.pydantic_config_to_model_config.PydanticConfigToModelConfig
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

Configuration Parameters
------------------------

**config_class_name** (str, default: "Config")
    Name of the nested configuration class to convert. Defaults to 'Config'.

Usage Example
-------------

In your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: pydantic-config-to-model-config

With custom config class name:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: pydantic-config-to-model-config
           args: ['--config-class-name=Settings']

Or programmatically:

.. code-block:: python

   from any_hook.files_modifiers.pydantic_config_to_model_config import PydanticConfigToModelConfig

   modifier = PydanticConfigToModelConfig(config_class_name="MyConfig")
   # Use modifier.modify(file_data_list)

Related Modifiers
-----------------

* :doc:`pydantic_v1_to_v2` - Handles the import migration part of Pydantic v1 to v2
