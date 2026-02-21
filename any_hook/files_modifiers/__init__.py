from typing import Annotated
from typing import Union

from any_hook.files_modifiers.forbidden_functions import ForbiddenFunctions
from any_hook.files_modifiers.local_imports import LocalImports
from any_hook.files_modifiers.object_to_any import ObjectToAny
from any_hook.files_modifiers.pydantic_config_to_model_config import (
    PydanticConfigToModelConfig,
)
from any_hook.files_modifiers.pydantic_v1_to_v2 import PydanticV1ToV2
from any_hook.files_modifiers.str_enum_inheritance import StrEnumInheritance
from any_hook.files_modifiers.utcnow_to_datetime_now import UtcNowToDatetimeNow
from pydantic import Field

AnyModifier = Annotated[
    Union[
        ObjectToAny,
        PydanticConfigToModelConfig,
        PydanticV1ToV2,
        StrEnumInheritance,
        LocalImports,
        ForbiddenFunctions,
        UtcNowToDatetimeNow,
    ],
    Field(discriminator="type"),
]
__all__ = [
    "ObjectToAny",
    "PydanticConfigToModelConfig",
    "PydanticV1ToV2",
    "StrEnumInheritance",
    "LocalImports",
    "ForbiddenFunctions",
    "UtcNowToDatetimeNow",
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
