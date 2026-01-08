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
    RepeatForRangeStmt,
    DefineStmt,
    GiveBackStmt,
    Expr,
    LiteralExpr,
    NameExpr,
    UnaryExpr,
    BinaryExpr,
    GroupExpr,
    ListExpr,
    DictExpr,
    FieldExpr,
    IndexExpr,
    CallExpr,
    Target,
    NameTarget,
    IndexTarget,
    FieldTarget,
    Param,
    CallArg,
    NodeSpan,
)
from .token import TokenType
from .runtime import Environment, to_rill_string
from .errors import RillRuntimeError, FieldTypeError, FieldNotFoundError


class _StopLoop(Exception):
    pass


class _SkipLoop(Exception):
    pass


class _Return(Exception):
    def __init__(self, value: Any) -> None:
        """
        Initialize the exception with the value to be returned from a function.
        
        Parameters:
            value: The value to carry as the function's return value when this exception is raised.
        """
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
        """
        Create a new Interpreter, configuring its output sink and initial environment.
        
        Initializes the output callable (used for ShowStmt output), the runtime Environment, and internal counters for loop and call nesting.
        
        Parameters:
            output (Callable[[str], None], optional): Function to receive interpreter output strings. Defaults to printing to stdout.
            env (Environment, optional): Preexisting runtime environment to use. Defaults to a new Environment() instance.
        """
        self.output = output or (lambda s: print(s))
        self.env = env or Environment()
        self._loop_depth = 0
        self._call_depth = 0

    def run(self, program: Program) -> None:
        """
        Execute all top-level statements in the given program in order.
        
        Each statement's effects are applied to the interpreter's environment and may produce output via the interpreter's configured output callable.
        
        Parameters:
            program (Program): The parsed program AST whose top-level statements will be executed.
        """
        for stmt in program.statements:
            self._exec_stmt(stmt)

    # ---------- statements ----------

    def _exec_stmt(self, stmt: Stmt) -> None:
        """
        Execute a single AST statement node in the interpreter.
        
        Performs the action represented by `stmt`, which may mutate the environment, emit output, define functions, control loop execution, or trigger a function return.
        
        Parameters:
            stmt (Stmt): The AST statement node to execute.
        
        Raises:
            RillRuntimeError: If the statement is unsupported or used in an invalid context (e.g., defining a function outside top level, `give back` outside a function, or `stop`/`skip` outside a loop).
            _Return: Raised to signal a function return with an optional return value.
            _StopLoop: Raised to signal termination of the nearest enclosing repeat loop.
            _SkipLoop: Raised to signal skipping the remainder of the current loop iteration.
        """
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

        if isinstance(stmt, RepeatForRangeStmt):
            self._exec_repeat_for_range(stmt)
            return

        raise RillRuntimeError(f"Unsupported statement type: {type(stmt).__name__}", getattr(stmt, "span", None))

    def _exec_if(self, stmt: IfStmt) -> None:
        """
        Execute an if-statement by evaluating branches in order and running the first matching branch body (or the else body if provided).
        
        Parameters:
            stmt (IfStmt): AST node containing ordered branches (each with a condition and body) and an optional else_body.
        
        Raises:
            RillRuntimeError: If any branch condition does not evaluate to a boolean.
        
        Description:
            For each branch, evaluates its condition; when a condition is true, executes that branch's body in a new scope and stops. If no branch matches and an else_body exists, executes the else_body in a new scope. Each executed branch or else body runs with its own pushed scope which is popped after execution.
        """
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

    def _as_int(self, value: Any, span, *, what: str = "number") -> int:
        """
        Convert a value to a whole integer or raise a runtime error.
        
        Parameters:
            value: The value to coerce to an int.
            span: AST node span used for error reporting when raising.
            what (str): Noun used in error messages (defaults to "number").
        
        Returns:
            int: The integer value (floats that represent whole numbers are converted).
        
        Raises:
            RillRuntimeError: If `value` is a boolean or not a whole number.
        """
        if isinstance(value, bool):
            raise RillRuntimeError(f"Expected a {what}.", span)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        raise RillRuntimeError(f"Expected a whole {what}.", span)

    def _as_nonneg_int(self, value: Any, span) -> int:
        """
        Convert a runtime value into a non-negative integer suitable for repeat counts.
        
        Parameters:
            value: The value to coerce (may be int or float with integer value).
            span: AST node span used for error reporting.
        
        Returns:
            The coerced integer value, guaranteed to be greater than or equal to zero.
        
        Raises:
            RillRuntimeError: If `value` is a boolean, not a whole number, or is negative.
        """
        n = self._as_int(value, span, what="repeat count")
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
        """
        Execute a `repeat while` loop statement until its condition becomes false.
        
        Evaluates the loop condition before each iteration and, while it is `True`, pushes a new scope and executes the loop body statements. Manages loop nesting depth for runtime checks. Handles loop-control exceptions so that `_SkipLoop` skips the remainder of the current iteration and `_StopLoop` exits the loop. Raises a runtime error if the loop condition does not evaluate to a boolean.
        """
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

    def _exec_repeat_for_range(self, stmt: RepeatForRangeStmt) -> None:
        """
        Execute a for-range repeat statement, iterating from start to end with an optional step.
        
        Evaluates the `start`, `end`, and optional `step` expressions, enforces integer-only bounds and valid step semantics (non-zero and directionally consistent), and for each iteration pushes a new scope, binds the loop variable to the current index, executes the loop body, and then pops the scope. Honors the statement's `inclusive` flag when testing the end condition and supports `SkipStmt` (skips remainder of iteration) and `StopStmt` (breaks out of the loop) control flow.
        
        Parameters:
            stmt (RepeatForRangeStmt): AST node describing the for-range loop (contains `start`, `end`, optional `step`, loop `var`, `inclusive` flag, and loop `body`).
        
        Raises:
            RillRuntimeError: If `start`, `end`, or `step` are not whole numbers, if `step` is zero, or if `step` direction is inconsistent with `start`/`end`.
        """
        start_val = self._eval_expr(stmt.start)
        end_val = self._eval_expr(stmt.end)

        start_i = self._as_int(start_val, stmt.start.span, what="start")
        end_i = self._as_int(end_val, stmt.end.span, what="end")

        # step rules
        if stmt.step is None:
            if start_i > end_i:
                raise RillRuntimeError(
                    "Range is descending but no `step` was provided. Use `step -1` for a countdown.",
                    stmt.span,
                )
            step_i = 1
        else:
            step_val = self._eval_expr(stmt.step)
            step_i = self._as_int(step_val, stmt.step.span, what="step")

        if step_i == 0:
            raise RillRuntimeError("`step` cannot be 0.", stmt.span)

        # direction checks (only meaningful when start != end)
        if start_i < end_i and step_i < 0:
            raise RillRuntimeError("Ascending range requires a positive `step`.", stmt.span)
        if start_i > end_i and step_i > 0:
            raise RillRuntimeError("Descending range requires a negative `step`.", stmt.span)

        def should_continue(i: int) -> bool:
            """
            Determine whether the loop should continue for the current index `i` based on the loop's step direction, end bound, and inclusivity.
            
            Parameters:
                i (int): The current loop index.
            
            Returns:
                bool: `True` if `i` is within the loop bounds (taking `step_i` sign and `stmt.inclusive` into account), `False` otherwise.
            """
            if step_i > 0:
                return i <= end_i if stmt.inclusive else i < end_i
            else:
                return i >= end_i if stmt.inclusive else i > end_i

        self._loop_depth += 1
        try:
            i = start_i
            while should_continue(i):
                self.env.push_scope()
                try:
                    self.env.define(stmt.var, i, stmt.span)
                    broke = False
                    try:
                        for s in stmt.body:
                            self._exec_stmt(s)
                    except _SkipLoop:
                        pass
                    except _StopLoop:
                        broke = True
                finally:
                    self.env.pop_scope()

                if broke:
                    break

                i += step_i
        finally:
            self._loop_depth -= 1


    def _assign_target(self, target: Target, value: Any) -> None:
        """
        Assign a value to a target location: a variable name, an indexed element, or an object field.
        
        NameTarget binds the value in the current environment. IndexTarget assigns into a list (requires an integer index that is >= 0 and less than the list length) or into a dict by key. FieldTarget assigns a named field on a dict-like object.
        
        Parameters:
            target (Target): The assignment target (NameTarget, IndexTarget, or FieldTarget).
            value (Any): The value to assign.
        
        Raises:
            RillRuntimeError: If the target type is unsupported; if IndexTarget is used on a non-list/non-dict; if a list index is not an integer, is negative, or is out of range.
            FieldTypeError: If FieldTarget is used on a non-dict object.
        """
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

        if isinstance(target, FieldTarget):
            obj = self._eval_expr(target.object)
            if not isinstance(obj, dict):
                raise FieldTypeError("assignment", target.span)
            obj[target.name] = value
            return

        raise RillRuntimeError(f"Unsupported target type: {type(target).__name__}", getattr(target, "span", None))

    # ---------- expressions ----------

    def _call_function(self, fn: FunctionValue, args: list[CallArg], span) -> Any:
        # Evaluate arguments in caller environment first.
        """
        Invoke a user-defined function with the given arguments and return its result.
        
        Parameters:
            fn (FunctionValue): The function value to call.
            args (List[CallArg]): Evaluated call arguments (positional and/or named).
            span: Source span used for error reporting when argument/arity checks fail.
        
        Returns:
            The value produced by the function body, or `None` if the function did not return a value.
        
        Raises:
            RillRuntimeError: If arguments violate ordering/duplication rules, unknown parameters are provided, required parameters are missing, or too many positional arguments are passed.
        """
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
        """
        Evaluate an AST expression and produce its runtime value.
        
        Parameters:
            expr (Expr): The expression AST node to evaluate.
        
        Returns:
            Any: The value produced by evaluating the expression (e.g. numbers, booleans, strings, lists, dicts, function values, or None).
        
        Raises:
            RillRuntimeError: If evaluation fails due to type errors, invalid operations (unsupported operators, bad indexing, comparison/type mismatches), out-of-range indices, unknown map keys, division/modulo by zero, calling a non-function, or other runtime validation errors.
        """
        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, NameExpr):
            return self.env.get(expr.name, expr.span)

        if isinstance(expr, GroupExpr):
            return self._eval_expr(expr.expr)

        if isinstance(expr, ListExpr):
            return [self._eval_expr(e) for e in expr.elements]

        if isinstance(expr, DictExpr):
            d: dict[Any, Any] = {}
            for ent in expr.entries:
                if ent.key in d:
                    raise RillRuntimeError(f"Duplicate key `{ent.key}` in record/map literal.", ent.span)
                d[ent.key] = self._eval_expr(ent.value)
            return d

        if isinstance(expr, FieldExpr):
            obj = self._eval_expr(expr.object)
            if not isinstance(obj, dict):
                raise FieldTypeError("access", expr.span)
            if expr.name not in obj:
                raise FieldNotFoundError(expr.name, expr.span)
            return obj[expr.name]

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