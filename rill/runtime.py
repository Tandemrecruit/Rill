from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .ast import NodeSpan


class RillRuntimeError(Exception):
    def __init__(self, message: str, span: Optional[NodeSpan] = None):
        if span is not None:
            super().__init__(f"Line {span.start_line}, col {span.start_col}: {message}")
        else:
            super().__init__(message)
        self.message = message
        self.span = span


@dataclass
class Environment:
    values: Dict[str, Any]

    def __init__(self) -> None:
        self.values = {}

    def define(self, name: str, value: Any, span: Optional[NodeSpan] = None) -> None:
        if name in self.values:
            raise RillRuntimeError(f"Cannot `set` `{name}` because it already exists. Use `change` to update.", span)
        self.values[name] = value

    def assign(self, name: str, value: Any, span: Optional[NodeSpan] = None) -> None:
        if name not in self.values:
            raise RillRuntimeError(f"Cannot `change` `{name}` because it does not exist. Use `set` to create it first.", span)
        self.values[name] = value

    def get(self, name: str, span: Optional[NodeSpan] = None) -> Any:
        if name not in self.values:
            raise RillRuntimeError(f"Unknown name `{name}`.", span)
        return self.values[name]


def to_rill_string(value: Any) -> str:
    if value is None:
        return "empty"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
