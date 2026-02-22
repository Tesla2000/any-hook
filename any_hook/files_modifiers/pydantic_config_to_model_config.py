import re
from typing import Literal

import pydantic
from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import Arg
from libcst import Assign
from libcst import AssignEqual
from libcst import AssignTarget
from libcst import Call
from libcst import ClassDef
from libcst import ImportFrom
from libcst import IndentedBlock
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine
from libcst import SimpleWhitespace
from pydantic import ConfigDict
from pydantic import Field


class _PydanticConfigToModelConfigTransformer(IgnoreAwareTransformer):
    def __init__(
        self,
        ignore_pattern: re.Pattern[str],
        config_class_name: str,
        import_adder: ModuleImportAdder,
    ) -> None:
        super().__init__(ignore_pattern)
        self._import_adder = import_adder
        self._made_changes = False
        self._has_config_dict_import = False
        self._current_class_depth = 0
        self._config_class_name = config_class_name

    def visit_ClassDef(self, node: ClassDef) -> bool:
        self._current_class_depth += 1
        self._push_compound_ignore(node)
        return True

    def leave_ClassDef(self, _: ClassDef, updated_node: ClassDef) -> ClassDef:
        self._current_class_depth -= 1
        ignored = self._pop_compound_ignore()
        if self._current_class_depth != 0:
            return updated_node
        if ignored:
            return updated_node
        if not isinstance(updated_node.body, IndentedBlock):
            return updated_node
        new_body = []
        has_model_config = False
        for statement in updated_node.body.body:
            if (
                isinstance(statement, SimpleStatementLine)
                and len(statement.body) == 1
            ):
                body_item = statement.body[0]
                if isinstance(body_item, Assign):
                    for target in body_item.targets:
                        if (
                            isinstance(target.target, Name)
                            and target.target.value == "model_config"
                        ):
                            has_model_config = True
                            break
            if (
                not isinstance(statement, ClassDef)
                or statement.name.value != self._config_class_name
            ):
                new_body.append(statement)
                continue
            if has_model_config:
                new_body.append(statement)
                continue
            config_dict_args = self._extract_config_args(statement)
            if config_dict_args is None:
                new_body.append(statement)
                continue
            self._made_changes = True
            model_config_statement = SimpleStatementLine(
                body=[self._create_model_config_assignment(config_dict_args)],
                leading_lines=statement.leading_lines,
            )
            new_body.append(model_config_statement)
        if new_body != list(updated_node.body.body):
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        return updated_node

    @staticmethod
    def _extract_config_args(config_class: ClassDef) -> list[Arg] | None:
        if not isinstance(config_class.body, IndentedBlock):
            return None
        args = []
        for statement in config_class.body.body:
            if not isinstance(statement, SimpleStatementLine):
                continue
            for body_item in statement.body:
                if not isinstance(body_item, Assign):
                    continue
                for target in body_item.targets:
                    if not isinstance(target.target, Name):
                        continue
                    arg = Arg(
                        value=body_item.value,
                        keyword=Name(target.target.value),
                        equal=AssignEqual(
                            whitespace_before=SimpleWhitespace(""),
                            whitespace_after=SimpleWhitespace(""),
                        ),
                    )
                    args.append(arg)
        return args

    @staticmethod
    def _create_model_config_assignment(args: list[Arg]):
        return Assign(
            targets=[AssignTarget(target=Name("model_config"))],
            value=Call(
                func=Name(ConfigDict.__name__),
                args=args,
            ),
        )

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        if not node.module or not isinstance(node.module, Name):
            return False
        if node.module.value != pydantic.__name__:
            return False
        if isinstance(node.names, str):
            return False
        for alias in node.names:
            if alias.name.value == ConfigDict.__name__:
                self._has_config_dict_import = True
        return False

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._made_changes or self._has_config_dict_import:
            return updated_node
        return self._import_adder.add(
            updated_node, pydantic.__name__, [ConfigDict.__name__]
        )


class PydanticConfigToModelConfig(
    SeparateModifier[_PydanticConfigToModelConfigTransformer]
):
    """Migrates Pydantic v1 Config class to v2 model_config.

    Converts nested Config classes to model_config assignments using ConfigDict.
    This is part of the Pydantic v1 to v2 migration path. Automatically adds
    ConfigDict import if not already present.

    Examples:
        Before:
            >>> from pydantic import BaseModel
            >>> class User(BaseModel):
            ...     name: str
            ...     class Config:
            ...         frozen = True
            ...         extra = "forbid"

        After:
            >>> from pydantic import BaseModel, ConfigDict
            >>> class User(BaseModel):
            ...     name: str
            ...     model_config = ConfigDict(frozen=True, extra="forbid")

    Note:
        If a class already has model_config defined, the Config class is
        left unchanged to avoid conflicts.
    """

    type: Literal["pydantic-config-to-model-config"] = (
        "pydantic-config-to-model-config"
    )
    config_class_name: str = Field(
        default="Config",
        description="Name of the nested configuration class to convert. Defaults to 'Config'.",
    )
    import_adder: ModuleImportAdder = Field(default_factory=ModuleImportAdder)

    def _create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _PydanticConfigToModelConfigTransformer:
        return _PydanticConfigToModelConfigTransformer(
            ignore_pattern, self.config_class_name, self.import_adder
        )

    def _modify_file(self, file_data: FileData) -> bool:
        if f"class {self.config_class_name}" not in file_data.content:
            return False
        return super()._modify_file(file_data)
