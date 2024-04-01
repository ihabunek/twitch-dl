import re
import dataclasses

from dataclasses import Field, is_dataclass
from datetime import date, datetime
from dateutil import parser
from typing import Any, Generator, Type, TypeVar, Union, get_args, get_origin, Callable
from typing import get_type_hints

# Generic data class instance
T = TypeVar("T")

# Dict of data decoded from JSON
Data = dict[str, Any]


def snake_to_camel(name: str):
    def repl(match: re.Match[str]):
        return match.group(1).upper()

    return re.sub(r"_([a-z])", repl, name)


def from_dict(cls: Type[T], data: Data, key_fn: Callable[[str], str] = snake_to_camel) -> T:
    """Convert a nested dict into an instance of `cls`."""

    def _fields() -> Generator[tuple[str, Any], None, None]:
        hints = get_type_hints(cls)
        for field in dataclasses.fields(cls):
            field_type = _prune_optional(hints[field.name])

            dict_field_name = key_fn(field.name)
            if (value := data.get(dict_field_name)) is not None:
                field_value = _convert(field_type, value)
            else:
                field_value = _get_default_value(field)

            yield field.name, field_value

    return cls(**dict(_fields()))


def from_dict_list(cls: Type[T], data: list[Data]) -> list[T]:
    return [from_dict(cls, x) for x in data]


def _get_default_value(field: Field[Any]):
    if field.default is not dataclasses.MISSING:
        return field.default

    if field.default_factory is not dataclasses.MISSING:
        return field.default_factory()

    return None


def _convert(field_type: Type[Any], value: Any) -> Any:
    if value is None:
        return None

    if field_type in [str, int, bool, dict]:
        return value

    if field_type == datetime:
        return parser.parse(value)

    if field_type == date:
        return date.fromisoformat(value)

    if get_origin(field_type) == list:
        (inner_type,) = get_args(field_type)
        return [_convert(inner_type, x) for x in value]

    if is_dataclass(field_type):
        return from_dict(field_type, value)

    raise ValueError(f"Not implemented for type '{field_type}'")


def _prune_optional(field_type: Type[Any]):
    """For `Optional[<type>]` returns the encapsulated `<type>`."""
    if get_origin(field_type) == Union:
        args = get_args(field_type)
        if len(args) == 2 and args[1] == type(None):  # noqa
            return args[0]

    return field_type
