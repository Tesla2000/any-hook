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


_BUILTIN_EXCEPTIONS: dict[str, type[BaseException]] = {
    name: obj
    for name, obj in vars(builtins).items()
    if isinstance(obj, type) and issubclass(obj, BaseException)
}


def _is_covered(raised: str, declared: frozenset[str]) -> bool:
    if raised in declared:
        return True
    raised_type = _BUILTIN_EXCEPTIONS.get(raised)
    if raised_type is None:
        return False
    declared_types = (_BUILTIN_EXCEPTIONS.get(name) for name in declared)
    return any(
        declared_type is not None and issubclass(raised_type, declared_type)
        for declared_type in declared_types
    )
