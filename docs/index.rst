any-hook Documentation
======================

Welcome to any-hook's documentation. This package provides a collection of pre-commit hooks
and file modifiers for Python projects.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modifiers/index
   api/reference

Overview
--------

**any-hook** is a versatile collection of Python code modifiers and validators designed to work
as pre-commit hooks. Each modifier can either transform your code (like upgrading Pydantic v1 to v2)
or detect violations (like forbidden function calls or local imports).

Quick Start
-----------

Install any-hook:

.. code-block:: bash

   pip install any-hook

Configure in your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/Tesla2000/any-hook
       rev: v0.1.16
       hooks:
         - id: your-hook-name

Features
--------

* **Code Transformers**: Automatically modernize your codebase
* **Code Validators**: Enforce coding standards and best practices
* **Pydantic Configuration**: Type-safe, validated configuration using Pydantic models
* **Flexible Outputs**: Configure where violations and changes are reported

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
