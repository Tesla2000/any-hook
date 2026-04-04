import re
from typing import ClassVar
from typing import Literal

import pydantic
from any_hook._file_data import FileData
from any_hook.files_modifiers._ignore_aware_transformer import (
    IgnoreAwareTransformer,
)
from any_hook.files_modifiers._import_adder import ModuleImportAdder
from any_hook.files_modifiers.separate_modifier import SeparateModifier
from libcst import AnnAssign
from libcst import Annotation
from libcst import Arg
from libcst import Assign
from libcst import AssignEqual
from libcst import Call
from libcst import ClassDef
from libcst import Comma
from libcst import ImportFrom
from libcst import IndentedBlock
from libcst import Index
from libcst import MaybeSentinel
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine
from libcst import SimpleWhitespace
from libcst import Subscript
from libcst import SubscriptElement
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
        self._has_class_var_import = False
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
        inline_args = list(updated_node.keywords)
        new_body = []
        has_model_config = False
        config_class_inserted = False
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
                elif isinstance(body_item, AnnAssign):
                    if (
                        isinstance(body_item.target, Name)
                        and body_item.target.value == "model_config"
                    ):
                        has_model_config = True
            if (
                isinstance(statement, ClassDef)
                and statement.name.value == self._config_class_name
                and not has_model_config
            ):
                config_dict_args = self._extract_config_args(statement)
                if config_dict_args is None:
                    new_body.append(statement)
                    continue
                self._made_changes = True
                config_class_inserted = True
                model_config_statement = SimpleStatementLine(
                    body=[
                        self._create_model_config_assignment(
                            inline_args + config_dict_args
                        )
                    ],
                    leading_lines=statement.leading_lines,
                )
                new_body.append(model_config_statement)
                continue
            new_body.append(statement)
        result = updated_node
        if inline_args and has_model_config and not config_class_inserted:
            new_body = self._merge_inline_args_into_model_config(
                new_body, inline_args
            )
            result = self._strip_keywords(updated_node)
            self._made_changes = True
        elif (
            inline_args and not has_model_config and not config_class_inserted
        ):
            self._made_changes = True
            result = self._strip_keywords(updated_node)
            model_config_statement = SimpleStatementLine(
                body=[self._create_model_config_assignment(inline_args)],
            )
            new_body.insert(0, model_config_statement)
        elif inline_args and not has_model_config and config_class_inserted:
            result = self._strip_keywords(updated_node)
        if (
            new_body != list(updated_node.body.body)
            or result is not updated_node
        ):
            return result.with_changes(
                body=result.body.with_changes(body=new_body)
            )
        return result

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
                    args.append(
                        Arg(
                            value=body_item.value,
                            keyword=Name(target.target.value),
                            equal=AssignEqual(
                                whitespace_before=SimpleWhitespace(""),
                                whitespace_after=SimpleWhitespace(""),
                            ),
                        )
                    )
        return args

    @staticmethod
    def _strip_keywords(node: ClassDef) -> ClassDef:
        bases = list(node.bases)
        if bases:
            bases[-1] = bases[-1].with_changes(comma=MaybeSentinel.DEFAULT)
        return node.with_changes(keywords=(), bases=bases)

    @classmethod
    def _merge_inline_args_into_model_config(
        cls, body: list, inline_args: list[Arg]
    ) -> list:
        inline_keys = {arg.keyword.value for arg in inline_args if arg.keyword}
        new_body = []
        for statement in body:
            if not (
                isinstance(statement, SimpleStatementLine)
                and len(statement.body) == 1
            ):
                new_body.append(statement)
                continue
            body_item = statement.body[0]
            if (
                isinstance(body_item, AnnAssign)
                and isinstance(body_item.target, Name)
                and body_item.target.value == "model_config"
            ):
                if not isinstance(body_item.value, Call):
                    new_body.append(statement)
                    continue
                existing_keys = {
                    arg.keyword.value
                    for arg in body_item.value.args
                    if arg.keyword
                }
                if inline_keys & existing_keys:
                    raise ValueError(
                        f"Conflicting model_config keys defined in both inline class kwargs and model_config: {inline_keys & existing_keys}"
                    )
                updated_value = cls._add_args_to_call(
                    body_item.value, inline_args
                )
                new_body.append(
                    statement.with_changes(
                        body=[body_item.with_changes(value=updated_value)]
                    )
                )
                continue
            if isinstance(body_item, Assign):
                target_names = {
                    t.target.value
                    for t in body_item.targets
                    if isinstance(t.target, Name)
                }
                if "model_config" in target_names:
                    if not isinstance(body_item.value, Call):
                        new_body.append(statement)
                        continue
                    existing_keys = {
                        arg.keyword.value
                        for arg in body_item.value.args
                        if arg.keyword
                    }
                    if inline_keys & existing_keys:
                        raise ValueError(
                            f"Conflicting model_config keys defined in both inline class kwargs and model_config: {inline_keys & existing_keys}"
                        )
                    updated_value = cls._add_args_to_call(
                        body_item.value, inline_args
                    )
                    upgraded = AnnAssign(
                        target=Name("model_config"),
                        annotation=Annotation(
                            annotation=Subscript(
                                value=Name(ClassVar.__name__),
                                slice=[
                                    SubscriptElement(
                                        slice=Index(
                                            value=Name(ConfigDict.__name__)
                                        )
                                    )
                                ],
                            ),
                        ),
                        value=updated_value,
                    )
                    new_body.append(statement.with_changes(body=[upgraded]))
                    continue
            new_body.append(statement)
        return new_body

    @staticmethod
    def _add_args_to_call(call: Call, new_args: list[Arg]) -> Call:
        existing_args = list(call.args)
        if existing_args:
            existing_args[-1] = existing_args[-1].with_changes(
                comma=Comma(whitespace_after=SimpleWhitespace(" "))
            )
        return call.with_changes(args=existing_args + new_args)

    @staticmethod
    def _create_model_config_assignment(args: list[Arg]) -> AnnAssign:
        return AnnAssign(
            target=Name("model_config"),
            annotation=Annotation(
                annotation=Subscript(
                    value=Name(ClassVar.__name__),
                    slice=[
                        SubscriptElement(
                            slice=Index(value=Name(ConfigDict.__name__))
                        )
                    ],
                ),
            ),
            value=Call(
                func=Name(ConfigDict.__name__),
                args=args,
            ),
        )

    def visit_ImportFrom(self, node: ImportFrom) -> bool:
        if not node.module or not isinstance(node.module, Name):
            return False
        if isinstance(node.names, str):
            return False
        if node.module.value == pydantic.__name__:
            for alias in node.names:
                if alias.name.value == ConfigDict.__name__:
                    self._has_config_dict_import = True
        if node.module.value == "typing":
            for alias in node.names:
                if alias.name.value == ClassVar.__name__:
                    self._has_class_var_import = True
        return False

    def leave_Module(self, _: Module, updated_node: Module) -> Module:
        if not self._made_changes:
            return updated_node
        if not self._has_config_dict_import:
            updated_node = self._import_adder.add(
                updated_node, pydantic.__name__, [ConfigDict.__name__]
            )
        if not self._has_class_var_import:
            updated_node = self._import_adder.add(
                updated_node, "typing", [ClassVar.__name__]
            )
        return updated_node


class PydanticConfigToModelConfig(
    SeparateModifier[_PydanticConfigToModelConfigTransformer]
):
    """Migrates Pydantic v1 Config class to v2 model_config.

    Converts nested Config classes to model_config assignments using ConfigDict.
    This is part of the Pydantic v1 to v2 migration path. Automatically adds
    ConfigDict and ClassVar imports if not already present.

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
            >>> from typing import ClassVar
            >>> class User(BaseModel):
            ...     name: str
            ...     model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

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

    def create_transformer(
        self, ignore_pattern: re.Pattern[str]
    ) -> _PydanticConfigToModelConfigTransformer:
        return _PydanticConfigToModelConfigTransformer(
            ignore_pattern, self.config_class_name, self.import_adder
        )

    def _modify_file(self, file_data: FileData) -> bool:
        if f"class {self.config_class_name}" not in file_data.content:
            has_inline_kwargs = any(
                "(" in line and "=" in line
                for line in file_data.content.splitlines()
                if line.startswith("class ")
            )
            if not has_inline_kwargs:
                return False
        return super()._modify_file(file_data)
