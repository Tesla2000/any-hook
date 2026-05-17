from libcst import ClassDef, parse_module

from any_hook.services.class_hierarchy_detector import ClassHierarchyDetector


class TestClassHierarchyDetector:
    def test_direct_inheritance(self):
        code = """
class User(BaseModel):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert detector.is_subclass_of(user_class, {"BaseModel"})

    def test_no_inheritance(self):
        code = """
class User:
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert not detector.is_subclass_of(user_class, {"BaseModel"})

    def test_indirect_inheritance(self):
        code = """
class Base(BaseModel):
    pass
class User(Base):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert detector.is_subclass_of(user_class, {"BaseModel"})

    def test_multiple_inheritance_levels(self):
        code = """
class Base(BaseModel):
    pass
class Middle(Base):
    pass
class User(Middle):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert detector.is_subclass_of(user_class, {"BaseModel"})

    def test_attribute_base_matching(self):
        code = """
import pydantic
class User(pydantic.BaseModel):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert detector.is_subclass_of(user_class, {"BaseModel"})

    def test_attribute_base_not_matching(self):
        code = """
import mymodule
class User(mymodule.MyBase):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert not detector.is_subclass_of(user_class, {"BaseModel"})

    def test_nested_attribute_base(self):
        code = """
import a
class User(a.b.MyBase):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert not detector.is_subclass_of(user_class, {"BaseModel"})

    def test_cycle_detection(self):
        code = """
class A(B):
    pass
class B(A):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        a_class = classes["A"]
        assert not detector.is_subclass_of(a_class, {"BaseModel"})

    def test_multiple_bases_first_matches(self):
        code = """
class User(BaseModel, Mixin):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert detector.is_subclass_of(user_class, {"BaseModel"})

    def test_multiple_bases_second_matches(self):
        code = """
class User(Mixin, BaseModel):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert detector.is_subclass_of(user_class, {"BaseModel"})

    def test_custom_target_bases(self):
        code = """
class User(CustomBase):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert detector.is_subclass_of(user_class, {"CustomBase"})
        assert not detector.is_subclass_of(user_class, {"BaseModel"})

    def test_multiple_target_bases(self):
        code = """
class User(CustomBase):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert detector.is_subclass_of(user_class, {"BaseModel", "CustomBase"})

    def test_invalid_base_expression(self):
        code = """
class User(42):
    pass
"""
        module = parse_module(code)
        classes = {
            item.name.value: item
            for item in module.body
            if isinstance(item, ClassDef)
        }
        detector = ClassHierarchyDetector(classes)
        user_class = classes["User"]
        assert not detector.is_subclass_of(user_class, {"BaseModel"})
