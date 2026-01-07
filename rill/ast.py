from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional
from .token import TokenType


@dataclass(frozen=True)
class NodeSpan:
    """Source span for AST nodes.

    - line/col are 1-based.
    - end positions are EXCLUSIVE.
    - indices are 0-based offsets into the original source string.
    """
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    start_index: int
    end_index: int


# ---------- Helper / Supporting Structures ----------
#
# These are supporting dataclasses referenced by AST nodes, but they are not
# themselves part of the Expr/Stmt inheritance tree.

@dataclass(frozen=True)
class CallArg:
    """Helper/supporting dataclass for CallExpr."""
    name: Optional[str]  # None for positional arg
    value: Expr
    span: NodeSpan


@dataclass(frozen=True)
class IfBranch:
    """Helper/supporting dataclass for IfStmt."""
    condition: Expr
    body: List[Stmt]
    span: NodeSpan


@dataclass(frozen=True)
class Param:
    """Helper/supporting dataclass for DefineStmt."""
    name: str
    default: Optional[Expr]
    span: NodeSpan

@dataclass(frozen=True)
class DictEntry:
    """Helper/supporting dataclass for DictExpr."""
    key: str
    value: Expr
    span: NodeSpan



# ---------- Expressions ----------

class Expr:
    span: NodeSpan


@dataclass(frozen=True)
class LiteralExpr(Expr):
    value: Any
    span: NodeSpan


@dataclass(frozen=True)
class NameExpr(Expr):
    name: str
    span: NodeSpan


@dataclass(frozen=True)
class UnaryExpr(Expr):
    op: TokenType
    right: Expr
    span: NodeSpan


@dataclass(frozen=True)
class BinaryExpr(Expr):
    left: Expr
    op: TokenType
    right: Expr
    span: NodeSpan


@dataclass(frozen=True)
class GroupExpr(Expr):
    expr: Expr
    span: NodeSpan

@dataclass(frozen=True)
class ListExpr(Expr):
    elements: List[Expr]
    span: NodeSpan


@dataclass(frozen=True)
class DictExpr(Expr):
    entries: List[DictEntry]
    span: NodeSpan


@dataclass(frozen=True)
class FieldExpr(Expr):
    object: Expr
    name: str
    span: NodeSpan



@dataclass(frozen=True)
class IndexExpr(Expr):
    collection: Expr
    index: Expr
    span: NodeSpan


@dataclass(frozen=True)
class CallExpr(Expr):
    callee: Expr
    args: List[CallArg]
    span: NodeSpan


# ---------- Assignment Targets ----------

class Target:
    span: NodeSpan


@dataclass(frozen=True)
class NameTarget(Target):
    name: str
    span: NodeSpan


@dataclass(frozen=True)
class IndexTarget(Target):
    collection: Expr
    index: Expr
    span: NodeSpan

@dataclass(frozen=True)
class FieldTarget(Target):
    object: Expr
    name: str
    span: NodeSpan



# ---------- Statements ----------

class Stmt:
    span: NodeSpan


@dataclass(frozen=True)
class DefineStmt(Stmt):
    name: str
    params: List[Param]
    body: List[Stmt]
    span: NodeSpan


@dataclass(frozen=True)
class GiveBackStmt(Stmt):
    expr: Optional[Expr]
    span: NodeSpan


@dataclass(frozen=True)
class ShowStmt(Stmt):
    expr: Expr
    span: NodeSpan


@dataclass(frozen=True)
class SetStmt(Stmt):
    name: str
    expr: Expr
    span: NodeSpan


@dataclass(frozen=True)
class ChangeStmt(Stmt):
    target: Target
    expr: Expr
    span: NodeSpan


@dataclass(frozen=True)
class StopStmt(Stmt):
    span: NodeSpan


@dataclass(frozen=True)
class SkipStmt(Stmt):
    span: NodeSpan


@dataclass(frozen=True)
class IfStmt(Stmt):
    branches: List[IfBranch]
    else_body: Optional[List[Stmt]]
    span: NodeSpan


@dataclass(frozen=True)
class RepeatTimesStmt(Stmt):
    count: Expr
    body: List[Stmt]
    span: NodeSpan


@dataclass(frozen=True)
class RepeatWhileStmt(Stmt):
    condition: Expr
    body: List[Stmt]
    span: NodeSpan


@dataclass(frozen=True)
class Program:
    statements: List[Stmt]
