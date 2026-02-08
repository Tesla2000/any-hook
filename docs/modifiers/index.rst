File Modifiers
==============

File modifiers are the core components of any-hook. Each modifier either transforms Python
source files or detects violations in your code.

Modifier Types
--------------

There are two main categories of modifiers:

**Code Transformers**
  These modifiers automatically rewrite your code to modernize it or enforce patterns:

  * :doc:`object_to_any` - Convert ``object`` type hints to ``Any``
  * :doc:`pydantic_v1_to_v2` - Migrate ``pydantic.v1`` imports to ``pydantic``
  * :doc:`pydantic_config_to_model_config` - Convert Pydantic v1 Config classes to v2 model_config
  * :doc:`str_enum_inheritance` - Modernize string enums to use StrEnum

**Code Validators**
  These modifiers detect and report violations without changing code:

  * :doc:`local_imports` - Detect import statements inside functions/classes
  * :doc:`forbidden_functions` - Detect calls to forbidden function names
  * :doc:`workflow_env_to_example` - Extract environment variables from workflows

Available Modifiers
-------------------

.. toctree::
   :maxdepth: 1

   object_to_any
   pydantic_v1_to_v2
   pydantic_config_to_model_config
   str_enum_inheritance
   local_imports
   forbidden_functions
   workflow_env_to_example

Base Classes
------------

.. toctree::
   :maxdepth: 1

   base_modifier
