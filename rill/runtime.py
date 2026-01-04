from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .ast import NodeSpan

from .errors import RillRuntimeError



@dataclass
class Environment:
    """Lexical environment with block scopes.

    - `set` defines in the *current* scope only.
    - `change` updates the nearest existing name walking outward.
    """
    scopes: List[Dict[str, Any]]

    def __init__(self) -> None:
        self.scopes = [{}]  # global scope

    def push_scope(self) -> None:
        self.scopes.append({})

    def pop_scope(self) -> None:
        if len(self.scopes) <= 1:
            # never pop the global scope
            return
        self.scopes.pop()

    def define(self, name: str, value: Any, span: Optional[NodeSpan] = None) -> None:
        current = self.scopes[-1]
        if name in current:
            raise RillRuntimeError(f"Cannot `set` `{name}` because it already exists in this block. Use `change`.", span)
        current[name] = value

    def assign(self, name: str, value: Any, span: Optional[NodeSpan] = None) -> None:
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = value
                return
        raise RillRuntimeError(f"Cannot `change` `{name}` because it does not exist. Use `set` first.", span)

    def get(self, name: str, span: Optional[NodeSpan] = None) -> Any:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise RillRuntimeError(f"Unknown name `{name}`.", span)


def to_rill_string(value: Any) -> str:
    if value is None:
        return "empty"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
