from typing import Annotated
from typing import Union

from any_hook.files_modifiers._base import Modifier
from any_hook.files_modifiers.agito import Agito
from any_hook.files_modifiers.any_to_object import AnyToObject
from any_hook.files_modifiers.check_untracked import CheckUntracked
from any_hook.files_modifiers.field_validator_check import FieldValidatorCheck
from any_hook.files_modifiers.forbidden_functions import ForbiddenFunctions
from any_hook.files_modifiers.len_as_bool import LenAsBool
from any_hook.files_modifiers.local_imports import LocalImports
from any_hook.files_modifiers.object_to_any import ObjectToAny
from any_hook.files_modifiers.open_to_path import OpenToPath
from any_hook.files_modifiers.pydantic_config_to_model_config import (
    PydanticConfigToModelConfig,
)
from any_hook.files_modifiers.pydantic_v1_to_v2 import PydanticV1ToV2
from any_hook.files_modifiers.remove_f_prefix import RemoveFPrefix
from any_hook.files_modifiers.return_tuple_parens_drop import (
    ReturnTupleParensDrop,
)
from any_hook.files_modifiers.str_enum_inheritance import StrEnumInheritance
from any_hook.files_modifiers.typing_to_builtin import TypingToBuiltin
from any_hook.files_modifiers.utcnow_to_datetime_now import UtcNowToDatetimeNow
from pydantic import Field

AnyModifier = Annotated[
    Union[
        AnyToObject,
        ObjectToAny,
        PydanticConfigToModelConfig,
        PydanticV1ToV2,
        StrEnumInheritance,
        LocalImports,
        ForbiddenFunctions,
        FieldValidatorCheck,
        UtcNowToDatetimeNow,
        LenAsBool,
        TypingToBuiltin,
        ReturnTupleParensDrop,
        RemoveFPrefix,
        OpenToPath,
        CheckUntracked,
        Agito,
    ],
    Field(discriminator="type"),
]
__all__ = [
    "Modifier",
    "Agito",
    "AnyToObject",
    "ObjectToAny",
    "RemoveFPrefix",
    "PydanticConfigToModelConfig",
    "PydanticV1ToV2",
    "StrEnumInheritance",
    "LocalImports",
    "ForbiddenFunctions",
    "FieldValidatorCheck",
    "UtcNowToDatetimeNow",
    "LenAsBool",
    "TypingToBuiltin",
    "ReturnTupleParensDrop",
    "CheckUntracked",
    "OpenToPath",
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
try:
    from any_hook.files_modifiers.generate_stubs import GenerateStubs

    AnyModifier = Annotated[
        Union[AnyModifier, GenerateStubs], Field(discriminator="type")
    ]
    __all__.append("GenerateStubs")
except ImportError as e:
    print(
        f"Package necessary to use generate-stubs is not installed, "
        f"generate-stubs is disabled.\n{e}"
    )
Agito.model_rebuild(_types_namespace={"AnyModifier": AnyModifier})
