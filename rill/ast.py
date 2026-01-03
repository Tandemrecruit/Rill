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
class IndexExpr(Expr):
    collection: Expr
    index: Expr
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


# ---------- Statements ----------

class Stmt:
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
class Program:
    statements: List[Stmt]
