from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from any_hook._file_data import FileData
from any_hook.files_modifiers.str_enum_inheritance import StrEnumInheritance
from libcst import parse_module
from tests.modifiers._base import TransformerTestCase


class TestStrEnumInheritance(TransformerTestCase):
    def test_converts_str_enum_inheritance_to_strenum(self):
        original_code = dedent("""
            from enum import Enum

            class MyEnum(str, Enum):
                A = "a"
                B = "b"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum

            class MyEnum(StrEnum):
                A = "a"
                B = "b"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_converts_enum_str_inheritance_to_strenum(self):
        original_code = dedent("""
            from enum import Enum

            class MyEnum(Enum, str):
                A = "a"
                B = "b"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum

            class MyEnum(StrEnum):
                A = "a"
                B = "b"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_keeps_enum_import_when_still_used(self):
        original_code = dedent("""
            from enum import Enum

            class MyStrEnum(str, Enum):
                A = "a"

            class MyIntEnum(Enum):
                B = 1
        """).strip()
        expected_code = dedent("""
            from enum import Enum, StrEnum

            class MyStrEnum(StrEnum):
                A = "a"

            class MyIntEnum(Enum):
                B = 1
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_handles_multiple_str_enum_classes(self):
        original_code = dedent("""
            from enum import Enum

            class Status(str, Enum):
                ACTIVE = "active"
                INACTIVE = "inactive"

            class Color(Enum, str):
                RED = "red"
                BLUE = "blue"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum

            class Status(StrEnum):
                ACTIVE = "active"
                INACTIVE = "inactive"

            class Color(StrEnum):
                RED = "red"
                BLUE = "blue"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_does_not_modify_single_enum_inheritance(self):
        original_code = dedent("""
            from enum import Enum

            class MyEnum(Enum):
                A = 1
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance()
            result = modifier.modify([file_data])
            self.assertFalse(result)
            self.assertEqual(file_path.read_text(), original_code)

    def test_does_not_modify_int_enum_inheritance(self):
        original_code = dedent("""
            from enum import Enum

            class MyEnum(int, Enum):
                A = 1
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance()
            result = modifier.modify([file_data])
            self.assertFalse(result)
            self.assertEqual(file_path.read_text(), original_code)

    def test_does_not_modify_three_base_classes(self):
        original_code = dedent("""
            from enum import Enum

            class MyEnum(str, Enum, SomeOther):
                A = "a"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance()
            result = modifier.modify([file_data])
            self.assertFalse(result)
            self.assertEqual(file_path.read_text(), original_code)

    def test_creates_enum_import_when_not_present(self):
        original_code = dedent("""
            from enum import Enum

            class MyEnum(str, Enum):
                A = "a"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum

            class MyEnum(StrEnum):
                A = "a"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_preserves_existing_strenum_import(self):
        original_code = dedent("""
            from enum import Enum, StrEnum

            class ExistingStrEnum(StrEnum):
                X = "x"

            class NewStrEnum(str, Enum):
                A = "a"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum

            class ExistingStrEnum(StrEnum):
                X = "x"

            class NewStrEnum(StrEnum):
                A = "a"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(
                convert_to_auto=False, convert_existing_str_enum=False
            )
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_does_not_modify_files_without_enum(self):
        original_code = dedent("""
            class MyClass(str):
                pass
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance()
            result = modifier.modify([file_data])
            self.assertFalse(result)
            self.assertEqual(file_path.read_text(), original_code)

    def test_does_not_modify_files_without_str(self):
        original_code = dedent("""
            from enum import Enum

            class MyEnum(Enum):
                A = 1
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance()
            result = modifier.modify([file_data])
            self.assertFalse(result)
            self.assertEqual(file_path.read_text(), original_code)

    def test_preserves_other_enum_imports(self):
        original_code = dedent("""
            from enum import Enum, IntEnum

            class MyEnum(str, Enum):
                A = "a"
        """).strip()
        expected_code = dedent("""
            from enum import IntEnum, StrEnum

            class MyEnum(StrEnum):
                A = "a"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_handles_import_star(self):
        original_code = dedent("""
            from enum import *

            class MyEnum(str, Enum):
                A = "a"
        """).strip()
        expected_code = dedent("""
            from enum import *

            class MyEnum(StrEnum):
                A = "a"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_mixed_enums_with_methods(self):
        original_code = dedent("""
            from enum import Enum

            class Status(str, Enum):
                ACTIVE = "active"

                def is_active(self) -> bool:
                    return self == Status.ACTIVE

            class Priority(Enum):
                HIGH = 1
        """).strip()
        expected_code = dedent("""
            from enum import Enum, StrEnum

            class Status(StrEnum):
                ACTIVE = "active"

                def is_active(self) -> bool:
                    return self == Status.ACTIVE

            class Priority(Enum):
                HIGH = 1
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_converts_to_auto_when_enabled(self):
        original_code = dedent("""
            from enum import Enum

            class Status(str, Enum):
                ACTIVE = "active"
                INACTIVE = "inactive"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum, auto

            class Status(StrEnum):
                ACTIVE = auto()
                INACTIVE = auto()
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=True)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_does_not_convert_to_auto_when_disabled(self):
        original_code = dedent("""
            from enum import Enum

            class Status(str, Enum):
                ACTIVE = "active"
                INACTIVE = "inactive"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum

            class Status(StrEnum):
                ACTIVE = "active"
                INACTIVE = "inactive"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=False)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_converts_to_auto_only_matching_values(self):
        original_code = dedent("""
            from enum import Enum

            class Status(str, Enum):
                ACTIVE = "active"
                CUSTOM = "custom_value"
                PENDING = "pending"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum, auto

            class Status(StrEnum):
                ACTIVE = auto()
                CUSTOM = "custom_value"
                PENDING = auto()
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=True)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_preserves_existing_auto_import(self):
        original_code = dedent("""
            from enum import Enum, auto

            class Status(str, Enum):
                ACTIVE = "active"
                PENDING = "pending"
        """).strip()
        expected_code = dedent("""
            from enum import auto, StrEnum

            class Status(StrEnum):
                ACTIVE = auto()
                PENDING = auto()
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=True)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_handles_uppercase_values(self):
        original_code = dedent("""
            from enum import Enum

            class Status(str, Enum):
                ACTIVE = "ACTIVE"
                PENDING = "pending"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum, auto

            class Status(StrEnum):
                ACTIVE = "ACTIVE"
                PENDING = auto()
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=True)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_handles_annotated_assignments_with_auto(self):
        original_code = dedent("""
            from enum import Enum

            class Status(str, Enum):
                ACTIVE: str = "active"
                PENDING: str = "pending"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum, auto

            class Status(StrEnum):
                ACTIVE: str = auto()
                PENDING: str = auto()
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=True)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_does_not_convert_non_matching_case(self):
        original_code = dedent("""
            from enum import Enum

            class Status(str, Enum):
                active = "Active"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum

            class Status(StrEnum):
                active = "Active"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(convert_to_auto=True)
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_converts_existing_str_enum_to_auto(self):
        original_code = dedent("""
            from enum import StrEnum

            class Status(StrEnum):
                ACTIVE = "active"
                PENDING = "pending"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum, auto

            class Status(StrEnum):
                ACTIVE = auto()
                PENDING = auto()
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(
                convert_to_auto=True, convert_existing_str_enum=True
            )
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_does_not_convert_existing_str_enum_when_flag_disabled(self):
        original_code = dedent("""
            from enum import StrEnum

            class Status(StrEnum):
                ACTIVE = "active"
                PENDING = "pending"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(
                convert_to_auto=True, convert_existing_str_enum=False
            )
            result = modifier.modify([file_data])
            self.assertFalse(result)
            self.assertEqual(file_path.read_text(), original_code)

    def test_converts_existing_str_enum_with_mixed_values(self):
        original_code = dedent("""
            from enum import StrEnum

            class Status(StrEnum):
                ACTIVE = "active"
                CUSTOM = "custom_status"
                PENDING = "pending"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum, auto

            class Status(StrEnum):
                ACTIVE = auto()
                CUSTOM = "custom_status"
                PENDING = auto()
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(
                convert_to_auto=True, convert_existing_str_enum=True
            )
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_converts_both_new_and_existing_str_enum(self):
        original_code = dedent("""
            from enum import Enum, StrEnum

            class ExistingStrEnum(StrEnum):
                ACTIVE = "active"

            class NewStrEnum(str, Enum):
                PENDING = "pending"
        """).strip()
        expected_code = dedent("""
            from enum import StrEnum, auto

            class ExistingStrEnum(StrEnum):
                ACTIVE = auto()

            class NewStrEnum(StrEnum):
                PENDING = auto()
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(
                convert_to_auto=True, convert_existing_str_enum=True
            )
            result = modifier.modify([file_data])
            self.assertTrue(result)
            self.assertEqual(file_path.read_text(), expected_code)

    def test_existing_str_enum_without_convert_to_auto(self):
        original_code = dedent("""
            from enum import StrEnum

            class Status(StrEnum):
                ACTIVE = "active"
                PENDING = "pending"
        """).strip()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.py"
            file_path.write_text(original_code)
            file_data = FileData(
                path=file_path,
                content=original_code,
                module=parse_module(original_code),
            )
            modifier = StrEnumInheritance(
                convert_to_auto=False, convert_existing_str_enum=True
            )
            result = modifier.modify([file_data])
            self.assertFalse(result)
            self.assertEqual(file_path.read_text(), original_code)
