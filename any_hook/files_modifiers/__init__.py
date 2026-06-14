import logging
from typing import TYPE_CHECKING, Annotated, Union

from pydantic import Field

from any_hook.files_modifiers._base import Modifier
from any_hook.files_modifiers.agito import Agito
from any_hook.files_modifiers.any_to_object import AnyToObject
from any_hook.files_modifiers.check_untracked import CheckUntracked
from any_hook.files_modifiers.combine_with import CombineWith
from any_hook.files_modifiers.comment_detector import CommentDetector
from any_hook.files_modifiers.field_validator_check import FieldValidatorCheck
from any_hook.files_modifiers.forbidden_functions import ForbiddenFunctions
from any_hook.files_modifiers.len_as_bool import LenAsBool
from any_hook.files_modifiers.local_imports import LocalImports
from any_hook.files_modifiers.local_imports_to_top import LocalImportsToTop
from any_hook.files_modifiers.object_to_any import ObjectToAny
from any_hook.files_modifiers.open_to_path import OpenToPath
from any_hook.files_modifiers.private_import_detector import (
    PrivateImportDetector,
)
from any_hook.files_modifiers.pydantic_config_to_model_config import (
    PydanticConfigToModelConfig,
)
from any_hook.files_modifiers.pydantic_v1_to_v2 import PydanticV1ToV2
from any_hook.files_modifiers.remove_f_prefix import RemoveFPrefix
from any_hook.files_modifiers.return_tuple_parens_drop import (
    ReturnTupleParensDrop,
)
from any_hook.files_modifiers.str_enum_inheritance import StrEnumInheritance
from any_hook.files_modifiers.test_if_checker import TestIfChecker
from any_hook.files_modifiers.typing_to_builtin import TypingToBuiltin
from any_hook.files_modifiers.utcnow_to_datetime_now import UtcNowToDatetimeNow

_logger = logging.getLogger(__name__)
_modifier_types: list[type] = [
    AnyToObject,
    ObjectToAny,
    PydanticConfigToModelConfig,
    PydanticV1ToV2,
    StrEnumInheritance,
    LocalImports,
    LocalImportsToTop,
    ForbiddenFunctions,
    FieldValidatorCheck,
    UtcNowToDatetimeNow,
    LenAsBool,
    TypingToBuiltin,
    ReturnTupleParensDrop,
    RemoveFPrefix,
    OpenToPath,
    CheckUntracked,
    TestIfChecker,
    Agito,
    CombineWith,
    CommentDetector,
    PrivateImportDetector,
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
    "LocalImportsToTop",
    "ForbiddenFunctions",
    "FieldValidatorCheck",
    "UtcNowToDatetimeNow",
    "LenAsBool",
    "TypingToBuiltin",
    "ReturnTupleParensDrop",
    "CheckUntracked",
    "OpenToPath",
    "CombineWith",
    "TestIfChecker",
    "CommentDetector",
    "PrivateImportDetector",
    "AnyModifier",
]
try:
    from any_hook.files_modifiers.workflow_env_to_example import (
        WorkflowEnvToExample,
    )

    _modifier_types.append(WorkflowEnvToExample)
    __all__.append("WorkflowEnvToExample")
except ImportError as e:  # pragma: no cover
    _logger.warning(
        "Package necessary to use workflow-env-to-example is not installed, "
        f"workflow-env-to-example is disabled.\n{e}"
    )
try:
    from any_hook.files_modifiers.generate_stubs import GenerateStubs

    _modifier_types.append(GenerateStubs)
    __all__.append("GenerateStubs")
except ImportError as e:  # pragma: no cover
    _logger.warning(
        "Package necessary to use generate-stubs is not installed, "
        f"generate-stubs is disabled.\n{e}"
    )
if TYPE_CHECKING:
    AnyModifier = Annotated[
        Union[
            AnyToObject,
            ObjectToAny,
            PydanticConfigToModelConfig,
            PydanticV1ToV2,
            StrEnumInheritance,
            LocalImports,
            LocalImportsToTop,
            ForbiddenFunctions,
            FieldValidatorCheck,
            UtcNowToDatetimeNow,
            LenAsBool,
            TypingToBuiltin,
            ReturnTupleParensDrop,
            RemoveFPrefix,
            OpenToPath,
            CheckUntracked,
            TestIfChecker,
            Agito,
            CombineWith,
            CommentDetector,
            PrivateImportDetector,
            WorkflowEnvToExample,
            GenerateStubs,
        ],
        Field(discriminator="type"),
    ]
else:
    AnyModifier = Annotated[
        Union.__getitem__(tuple(_modifier_types)),
        Field(discriminator="type"),
    ]
Agito.model_rebuild(_types_namespace={"AnyModifier": AnyModifier})
