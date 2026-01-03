from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .ast import (
    Program,
    Stmt,
    ShowStmt,
    SetStmt,
    ChangeStmt,
    Expr,
    LiteralExpr,
    NameExpr,
    UnaryExpr,
    BinaryExpr,
    GroupExpr,
    IndexExpr,
    Target,
    NameTarget,
    IndexTarget,
)
from .token import TokenType
from .runtime import Environment, RillRuntimeError, to_rill_string


@dataclass
class Interpreter:
    output: Callable[[str], None]
    env: Environment

    def __init__(self, output: Optional[Callable[[str], None]] = None, env: Optional[Environment] = None) -> None:
        self.output = output or (lambda s: print(s))
        self.env = env or Environment()

    def run(self, program: Program) -> None:
        for stmt in program.statements:
            self._exec_stmt(stmt)

    # ---------- statements ----------

    def _exec_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, ShowStmt):
            val = self._eval_expr(stmt.expr)
            self.output(to_rill_string(val))
            return

        if isinstance(stmt, SetStmt):
            val = self._eval_expr(stmt.expr)
            self.env.define(stmt.name, val, stmt.span)
            return

        if isinstance(stmt, ChangeStmt):
            val = self._eval_expr(stmt.expr)
            self._assign_target(stmt.target, val)
            return

        raise RillRuntimeError(f"Unsupported statement type: {type(stmt).__name__}", getattr(stmt, "span", None))

    def _assign_target(self, target: Target, value: Any) -> None:
        if isinstance(target, NameTarget):
            self.env.assign(target.name, value, target.span)
            return

        if isinstance(target, IndexTarget):
            coll = self._eval_expr(target.collection)
            idx = self._eval_expr(target.index)

            # list assignment
            if isinstance(coll, list):
                if not isinstance(idx, int):
                    raise RillRuntimeError("List index must be an integer.", target.span)
                if idx < 0:
                    raise RillRuntimeError("Negative indices are not allowed. Use `last of ...` instead.", target.span)
                if idx >= len(coll):
                    raise RillRuntimeError(f"List index {idx} is out of range (length {len(coll)}).", target.span)
                coll[idx] = value
                return

            # map/dict assignment
            if isinstance(coll, dict):
                coll[idx] = value
                return

            raise RillRuntimeError("Index assignment requires a list or map.", target.span)

        raise RillRuntimeError(f"Unsupported target type: {type(target).__name__}", getattr(target, "span", None))

    # ---------- expressions ----------

    def _eval_expr(self, expr: Expr) -> Any:
        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, NameExpr):
            return self.env.get(expr.name, expr.span)

        if isinstance(expr, GroupExpr):
            return self._eval_expr(expr.expr)

        if isinstance(expr, IndexExpr):
            coll = self._eval_expr(expr.collection)
            idx = self._eval_expr(expr.index)

            if isinstance(coll, list):
                if not isinstance(idx, int):
                    raise RillRuntimeError("List index must be an integer.", expr.span)
                if idx < 0:
                    raise RillRuntimeError("Negative indices are not allowed. Use `last of ...` instead.", expr.span)
                if idx >= len(coll):
                    raise RillRuntimeError(f"List index {idx} is out of range (length {len(coll)}).", expr.span)
                return coll[idx]

            if isinstance(coll, dict):
                if idx not in coll:
                    raise RillRuntimeError(f"Map key {idx!r} not found.", expr.span)
                return coll[idx]

            raise RillRuntimeError("Indexing requires a list or map.", expr.span)

        if isinstance(expr, UnaryExpr):
            right = self._eval_expr(expr.right)

            if expr.op == TokenType.NOT:
                if not isinstance(right, bool):
                    raise RillRuntimeError("`not` expects a boolean.", expr.span)
                return not right

            if expr.op == TokenType.MINUS:
                self._require_number(right, expr.span)
                return -right

            raise RillRuntimeError(f"Unsupported unary operator: {expr.op.name}", expr.span)

        if isinstance(expr, BinaryExpr):
            left = self._eval_expr(expr.left)
            right = self._eval_expr(expr.right)
            op = expr.op

            # boolean ops (strict)
            if op == TokenType.AND:
                self._require_bool(left, expr.span)
                self._require_bool(right, expr.span)
                return left and right
            if op == TokenType.OR:
                self._require_bool(left, expr.span)
                self._require_bool(right, expr.span)
                return left or right

            # equality
            if op == TokenType.EQ:
                return left == right
            if op == TokenType.NEQ:
                return left != right

            # comparisons (numbers or text, same-type)
            if op in (TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
                if type(left) is not type(right):
                    raise RillRuntimeError("Cannot compare values of different types.", expr.span)
                if not isinstance(left, (int, float, str)):
                    raise RillRuntimeError("Comparison requires numbers or text.", expr.span)

                if op == TokenType.LT:
                    return left < right
                if op == TokenType.LTE:
                    return left <= right
                if op == TokenType.GT:
                    return left > right
                if op == TokenType.GTE:
                    return left >= right

            # arithmetic
            if op == TokenType.PLUS:
                if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    return left + right
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                raise RillRuntimeError("`+` supports number+number or text+text.", expr.span)

            if op == TokenType.MINUS:
                self._require_number(left, expr.span)
                self._require_number(right, expr.span)
                return left - right

            if op == TokenType.STAR:
                self._require_number(left, expr.span)
                self._require_number(right, expr.span)
                return left * right

            if op == TokenType.SLASH:
                self._require_number(left, expr.span)
                self._require_number(right, expr.span)
                if right == 0:
                    raise RillRuntimeError("Division by zero.", expr.span)
                return left / right  # real division

            if op == TokenType.PERCENT:
                self._require_number(left, expr.span)
                self._require_number(right, expr.span)
                if right == 0:
                    raise RillRuntimeError("Modulo by zero.", expr.span)
                return left % right

            raise RillRuntimeError(f"Unsupported binary operator: {op.name}", expr.span)

        raise RillRuntimeError(f"Unsupported expression type: {type(expr).__name__}", getattr(expr, "span", None))

    @staticmethod
    def _require_number(v: Any, span) -> None:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise RillRuntimeError("Expected a number.", span)

    @staticmethod
    def _require_bool(v: Any, span) -> None:
        if not isinstance(v, bool):
            raise RillRuntimeError("Expected a boolean.", span)
