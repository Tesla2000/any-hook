import builtins

from libcst import BaseExpression, Index, Name, Subscript, SubscriptElement

from any_hook.services._class_hierarchy_detector import _extract_base_name


def _extract_annotated_exceptions(
    annotation: BaseExpression | None,
) -> frozenset[str]:
    if (
        not isinstance(annotation, Subscript)
        or not isinstance(annotation.value, Name)
        or annotation.value.value != "Annotated"
        or len(annotation.slice) < 2
    ):
        return frozenset()
    names = (
        _extract_base_name(element.slice.value)
        for element in annotation.slice[1:]
        if isinstance(element, SubscriptElement)
        and isinstance(element.slice, Index)
    )
    return frozenset(name for name in names if name is not None)


def _builtin_type(name: str) -> type | None:
    candidate = vars(builtins).get(name)
    return candidate if isinstance(candidate, type) else None


def _is_covered(raised: str, declared: frozenset[str]) -> bool:
    if raised in declared:
        return True
    raised_type = _builtin_type(raised)
    if raised_type is None:
        return False
    declared_types = (_builtin_type(name) for name in declared)
    return any(
        declared_type is not None and issubclass(raised_type, declared_type)
        for declared_type in declared_types
    )
