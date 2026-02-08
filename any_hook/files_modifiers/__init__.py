from typing import Annotated
from typing import Union

from any_hook.files_modifiers.object_to_any import ObjectToAny
from pydantic import Field

AnyModifier = Annotated[Union[ObjectToAny], Field(discriminator="type")]
__all__ = [
    "ObjectToAny",
    "AnyModifier",
]
try:
    from any_hook.files_modifiers.workflow_env_to_example import (
        WorkflowEnvToExample,
    )

    AnyModifier = Annotated[
        Union[AnyModifier, WorkflowEnvToExample], Field(discriminator="type")
    ]
    __all__.append("WorkflowEnvToExample")
except ImportError as e:
    print(
        f"Package necessary to use workflow-env-to-example is not installed, "
        f"workflow-env-to-example is disabled.\n{e}"
    )
