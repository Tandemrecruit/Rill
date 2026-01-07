from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Optional

from .ast import (
    Program,
    Stmt,
    ShowStmt,
    SetStmt,
    ChangeStmt,
    StopStmt,
    SkipStmt,
    IfStmt,
    RepeatTimesStmt,
    RepeatWhileStmt,
    DefineStmt,
    GiveBackStmt,
    Expr,
    LiteralExpr,
    NameExpr,
    UnaryExpr,
    BinaryExpr,
    GroupExpr,
    IndexExpr,
    CallExpr,
    Target,
    NameTarget,
    IndexTarget,
    Param,
    CallArg,
    NodeSpan,
)
from .token import TokenType
from .runtime import Environment, RillRuntimeError, to_rill_string


class _StopLoop(Exception):
    pass


class _SkipLoop(Exception):
    pass


class _Return(Exception):
    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value


@dataclass(frozen=True)
class FunctionValue:
    name: str
    params: list[Param]
    body: list[Stmt]
    global_scope: dict[str, Any]
    span: NodeSpan


@dataclass
class Interpreter:
    output: Callable[[str], None]
    env: Environment

    def __init__(self, output: Optional[Callable[[str], None]] = None, env: Optional[Environment] = None) -> None:
        self.output = output or (lambda s: print(s))
        self.env = env or Environment()
        self._loop_depth = 0
        self._call_depth = 0

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

        if isinstance(stmt, DefineStmt):
            # v0: keep it simple and only allow top-level functions (no closures).
            if len(self.env.scopes) != 1:
                raise RillRuntimeError("Functions can only be defined at the top level in v0.", stmt.span)
            fn = FunctionValue(
                name=stmt.name,
                params=stmt.params,
                body=stmt.body,
                global_scope=self.env.scopes[0],
                span=stmt.span,
            )
            self.env.define(stmt.name, fn, stmt.span)
            return

        if isinstance(stmt, GiveBackStmt):
            if self._call_depth <= 0:
                raise RillRuntimeError("`give back` can only be used inside a function.", stmt.span)
            value = None if stmt.expr is None else self._eval_expr(stmt.expr)
            raise _Return(value)

        if isinstance(stmt, StopStmt):
            if self._loop_depth <= 0:
                raise RillRuntimeError("`stop` can only be used inside a repeat loop.", stmt.span)
            raise _StopLoop()

        if isinstance(stmt, SkipStmt):
            if self._loop_depth <= 0:
                raise RillRuntimeError("`skip` can only be used inside a repeat loop.", stmt.span)
            raise _SkipLoop()

        if isinstance(stmt, IfStmt):
            self._exec_if(stmt)
            return

        if isinstance(stmt, RepeatTimesStmt):
            self._exec_repeat_times(stmt)
            return

        if isinstance(stmt, RepeatWhileStmt):
            self._exec_repeat_while(stmt)
            return

        raise RillRuntimeError(f"Unsupported statement type: {type(stmt).__name__}", getattr(stmt, "span", None))

    def _exec_if(self, stmt: IfStmt) -> None:
        for br in stmt.branches:
            cond_val = self._eval_expr(br.condition)
            if not isinstance(cond_val, bool):
                raise RillRuntimeError("`if` condition must be true/false.", br.condition.span)
            if cond_val:
                self.env.push_scope()
                try:
                    for s in br.body:
                        self._exec_stmt(s)
                finally:
                    self.env.pop_scope()
                return

        if stmt.else_body is not None:
            self.env.push_scope()
            try:
                for s in stmt.else_body:
                    self._exec_stmt(s)
            finally:
                self.env.pop_scope()

    def _as_nonneg_int(self, value: Any, span) -> int:
        if isinstance(value, bool):
            raise RillRuntimeError("Expected a number.", span)
        if isinstance(value, int):
            n = value
        elif isinstance(value, float) and value.is_integer():
            n = int(value)
        else:
            raise RillRuntimeError("Repeat count must be a whole number.", span)
        if n < 0:
            raise RillRuntimeError("Repeat count cannot be negative.", span)
        return n

    def _exec_repeat_times(self, stmt: RepeatTimesStmt) -> None:
        count_val = self._eval_expr(stmt.count)
        n = self._as_nonneg_int(count_val, stmt.count.span)

        self._loop_depth += 1
        try:
            for _ in range(n):
                self.env.push_scope()
                try:
                    try:
                        for s in stmt.body:
                            self._exec_stmt(s)
                    except _SkipLoop:
                        continue
                    except _StopLoop:
                        break
                finally:
                    self.env.pop_scope()
        finally:
            self._loop_depth -= 1

    def _exec_repeat_while(self, stmt: RepeatWhileStmt) -> None:
        self._loop_depth += 1
        try:
            while True:
                cond_val = self._eval_expr(stmt.condition)
                if not isinstance(cond_val, bool):
                    raise RillRuntimeError("`repeat while` condition must be true/false.", stmt.condition.span)
                if not cond_val:
                    break

                self.env.push_scope()
                try:
                    try:
                        for s in stmt.body:
                            self._exec_stmt(s)
                    except _SkipLoop:
                        pass
                    except _StopLoop:
                        break
                finally:
                    self.env.pop_scope()
        finally:
            self._loop_depth -= 1

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
                    raise RillRuntimeError(
                        "Negative indices are not allowed. Use `last of ...` instead.", target.span
                    )
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

    def _call_function(self, fn: FunctionValue, args: list[CallArg], span) -> Any:
        # Evaluate arguments in caller environment first.
        positional: list[Any] = []
        named: dict[str, Any] = {}
        seen_named = False

        for a in args:
            if a.name is None:
                if seen_named:
                    raise RillRuntimeError("Positional arguments must come before named arguments.", a.span)
                positional.append(self._eval_expr(a.value))
            else:
                seen_named = True
                if a.name in named:
                    raise RillRuntimeError(f"Argument `{a.name}` provided multiple times.", a.span)
                named[a.name] = self._eval_expr(a.value)

        params = fn.params
        if len(positional) > len(params):
            raise RillRuntimeError(
                f"Too many arguments for `{fn.name}` (expected at most {len(params)}).", span
            )

        param_by_name = {p.name: p for p in params}

        local: dict[str, Any] = {}
        # bind positional
        for i, val in enumerate(positional):
            local[params[i].name] = val

        # bind named
        for name, val in named.items():
            p = param_by_name.get(name)
            if p is None:
                raise RillRuntimeError(f"Unknown parameter `{name}` for `{fn.name}`.", span)
            if name in local:
                raise RillRuntimeError(f"Parameter `{name}` already set by a positional argument.", span)
            local[name] = val

        saved_scopes = self.env.scopes
        self.env.scopes = [fn.global_scope, local]
        self._call_depth += 1
        try:
            # fill defaults
            for p in params:
                if p.name in local:
                    continue
                if p.default is not None:
                    local[p.name] = self._eval_expr(p.default)
                else:
                    raise RillRuntimeError(f"Missing argument `{p.name}` for `{fn.name}`.", span)

            try:
                for s in fn.body:
                    self._exec_stmt(s)
            except _Return as r:
                return r.value

            return None
        finally:
            self._call_depth -= 1
            self.env.scopes = saved_scopes

    def _eval_expr(self, expr: Expr) -> Any:
        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, NameExpr):
            return self.env.get(expr.name, expr.span)

        if isinstance(expr, GroupExpr):
            return self._eval_expr(expr.expr)

        if isinstance(expr, CallExpr):
            callee_val = self._eval_expr(expr.callee)
            if not isinstance(callee_val, FunctionValue):
                raise RillRuntimeError("Only functions can be called.", expr.span)
            return self._call_function(callee_val, expr.args, expr.span)

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
