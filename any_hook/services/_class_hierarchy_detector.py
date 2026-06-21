from libcst import Attribute, BaseExpression, ClassDef, Name


def _extract_base_name(base_value: BaseExpression) -> str | None:
    """Extract class name from a base expression (Name or nested Attribute).

    For Attributes, extracts the final name (e.g., 'BaseModel' from 'a.b.BaseModel').
    Returns None for invalid base expressions (Call, Lambda, etc).
    """
    if isinstance(base_value, Name):
        return base_value.value
    if isinstance(base_value, Attribute):
        return base_value.attr.value
    return None


class _ClassHierarchyDetector:
    """Recursively detects if a class is a subclass of target base classes.

    Note: Detection is limited to classes defined within the same module.
    Classes inherited from other files cannot be verified as subclasses.
    """

    def __init__(self, class_definitions: dict[str, ClassDef]) -> None:
        self._class_definitions = class_definitions

    def is_subclass_of(
        self,
        node: ClassDef,
        target_bases: set[str],
        visited: set[str] | None = None,
    ) -> bool:
        """Recursively check if a class is a subclass of any target base.

        Args:
            node: The class definition to check
            target_bases: Set of target base class names to check against
            visited: Set of class names already checked (for cycle detection)

        Returns:
            True if the class is a subclass of any target base
        """
        if visited is None:
            visited = set()

        for base in node.bases:
            base_class_name = _extract_base_name(base.value)
            if base_class_name is None:
                continue
            if self._check_base(base_class_name, target_bases, visited):
                return True

        return False

    def _check_base(
        self, base_class_name: str, target_bases: set[str], visited: set[str]
    ) -> bool:
        """Check if a base class matches targets or has target in its hierarchy."""
        if base_class_name in target_bases:
            return True
        if (
            base_class_name not in visited
            and base_class_name in self._class_definitions
        ):
            visited.add(base_class_name)
            if self.is_subclass_of(
                self._class_definitions[base_class_name], target_bases, visited
            ):
                return True
        return False
