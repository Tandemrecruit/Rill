from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set

from .token import Token, TokenType
from .errors import RillParseError
from .ast import (
    Program,
    NodeSpan,
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
    Stmt,
    ShowStmt,
    SetStmt,
    ChangeStmt,
    StopStmt,
    SkipStmt,
    IfBranch,
    IfStmt,
    RepeatTimesStmt,
    RepeatWhileStmt,
)


def span_from_tokens(start: Token, end: Token) -> NodeSpan:
    """
    Create a NodeSpan covering the range from the `start` token to the `end` token, inclusive.
    
    Returns:
        NodeSpan: Span whose start line/column and start index are taken from `start`, and whose end line/column and end index are taken from `end`.
    """
    return NodeSpan(
        start_line=start.line,
        start_col=start.col,
        end_line=end.end_line,
        end_col=end.end_col,
        start_index=start.start_index,
        end_index=end.end_index,
    )


def span_join(a: NodeSpan, b: NodeSpan) -> NodeSpan:
    """Join two spans from a.start -> b.end."""
    return NodeSpan(
        start_line=a.start_line,
        start_col=a.start_col,
        end_line=b.end_line,
        end_col=b.end_col,
        start_index=a.start_index,
        end_index=b.end_index,
    )


@dataclass
class Parser:
    tokens: List[Token]
    filename: str = "<memory>"

    def __post_init__(self) -> None:
        self._i = 0

    # ---------- entrypoint ----------

    def parse(self) -> Program:
        statements: List[Stmt] = []
        self._consume_newlines()
        while not self._check(TokenType.EOF):
            statements.append(self._statement())
            self._consume_newlines()
        return Program(statements)

    # ---------- statements ----------

    def _statement(self) -> Stmt:
        if self._match(TokenType.SHOW):
            start = self._previous()
            expr = self._expression()
            return ShowStmt(expr=expr, span=span_join(span_from_tokens(start, start), expr.span))

        if self._match(TokenType.SET):
            start = self._previous()
            name_tok = self._consume(TokenType.IDENT, "Expected a variable name after `set`.")
            self._consume(TokenType.TO, "Expected `to` after variable name.")
            expr = self._expression()
            return SetStmt(name=name_tok.lexeme, expr=expr, span=span_join(span_from_tokens(start, start), expr.span))

        if self._match(TokenType.CHANGE):
            start = self._previous()
            target = self._target()
            self._consume(TokenType.TO, "Expected `to` after change target.")
            expr = self._expression()
            return ChangeStmt(target=target, expr=expr, span=span_join(span_from_tokens(start, start), expr.span))

        if self._match(TokenType.STOP):
            t = self._previous()
            return StopStmt(span=span_from_tokens(t, t))

        if self._match(TokenType.SKIP):
            t = self._previous()
            return SkipStmt(span=span_from_tokens(t, t))

        if self._match(TokenType.IF):
            return self._if_statement(self._previous())

        if self._match(TokenType.REPEAT):
            return self._repeat_statement(self._previous())

        raise self._error(self._peek(), "Expected a statement (show/set/change/if/repeat).")

    def _require_newline(self, message: str) -> Token:
        if self._match(TokenType.NEWLINE):
            return self._previous()
        raise self._error(self._peek(), message)

    def _block(self, until: Set[TokenType]) -> List[Stmt]:
        """Parse statements until one of `until` is encountered (not consumed)."""
        statements: List[Stmt] = []
        self._consume_newlines()
        while not self._check(TokenType.EOF) and not self._check_any(until):
            statements.append(self._statement())
            self._consume_newlines()
        return statements

    def _if_statement(self, if_tok: Token) -> IfStmt:
        # if <expr> NEWLINE <block> (otherwise if <expr> NEWLINE <block>)* (otherwise NEWLINE <block>)? end
        """
        Parse an if/otherwise/end construct and produce the corresponding IfStmt AST node.
        
        Parses an initial `if` condition and its then-block, followed by zero or more `otherwise if` branches and an optional plain `otherwise` block, and consumes the closing `end` token. Each branch's span covers its condition through the last statement of its body when a body is present.
        
        Parameters:
            if_tok (Token): The `IF` token that starts the construct; used to form the overall span of the resulting IfStmt.
        
        Returns:
            IfStmt: An AST node containing the list of IfBranch entries, an optional else_body list of statements, and a span from `if_tok` to the closing `end` token.
        
        Raises:
            RillParseError: On syntax errors such as a missing newline after the `if` / `otherwise if` condition, a missing newline after a plain `otherwise`, or a missing closing `end`.
        """
        branches: List[IfBranch] = []
        else_body: Optional[List[Stmt]] = None

        cond = self._expression()
        self._require_newline("Expected a newline after the `if` condition.")
        then_body = self._block({TokenType.OTHERWISE, TokenType.END})
        branches.append(IfBranch(condition=cond, body=then_body, span=span_join(cond.span, then_body[-1].span) if then_body else cond.span))

        while self._match(TokenType.OTHERWISE):
            other_tok = self._previous()

            if self._match(TokenType.IF):
                cond2 = self._expression()
                self._require_newline("Expected a newline after the `otherwise if` condition.")
                body2 = self._block({TokenType.OTHERWISE, TokenType.END})
                branches.append(
                    IfBranch(
                        condition=cond2,
                        body=body2,
                        span=span_join(cond2.span, body2[-1].span) if body2 else cond2.span,
                    )
                )
                continue

            # plain otherwise
            if not self._match(TokenType.NEWLINE):
                raise self._error(self.peek(), "Expected a newline after `otherwise`.")
            else_body = self._block({TokenType.END})
            break


        end_tok = self._consume(TokenType.END, "Expected `end` to close the `if` block.")
        return IfStmt(branches=branches, else_body=else_body, span=span_from_tokens(if_tok, end_tok))

    def _repeat_statement(self, repeat_tok: Token) -> Stmt:
        # repeat while <expr> NEWLINE <block> end
        # repeat <expr> times NEWLINE <block> end
        if self._match(TokenType.WHILE):
            cond = self._expression()
            self._require_newline("Expected a newline after the `repeat while` condition.")
            body = self._block({TokenType.END})
            end_tok = self._consume(TokenType.END, "Expected `end` to close the `repeat` block.")
            return RepeatWhileStmt(condition=cond, body=body, span=span_from_tokens(repeat_tok, end_tok))

        count = self._expression()
        self._consume(TokenType.TIMES, "Expected `times` after repeat count.")
        self._require_newline("Expected a newline after `repeat ... times`.")
        body = self._block({TokenType.END})
        end_tok = self._consume(TokenType.END, "Expected `end` to close the `repeat` block.")
        return RepeatTimesStmt(count=count, body=body, span=span_from_tokens(repeat_tok, end_tok))

    def _target(self) -> Target:
        # v0: IDENT or IDENT[expr]
        name_tok = self._consume(TokenType.IDENT, "Expected a variable name after `change`.")
        name_span = span_from_tokens(name_tok, name_tok)
        base_expr = NameExpr(name=name_tok.lexeme, span=name_span)

        if self._match(TokenType.LBRACKET):
            idx = self._expression()
            rbr = self._consume(TokenType.RBRACKET, "Expected `]` after index.")
            return IndexTarget(collection=base_expr, index=idx, span=span_from_tokens(name_tok, rbr))

        return NameTarget(name=name_tok.lexeme, span=name_span)

    # ---------- expressions ----------

    def _expression(self) -> Expr:
        return self._or()

    def _or(self) -> Expr:
        expr = self._and()
        while self._match(TokenType.OR):
            op = self._previous()
            right = self._and()
            expr = BinaryExpr(left=expr, op=op.type, right=right, span=span_join(expr.span, right.span))
        return expr

    def _and(self) -> Expr:
        expr = self._comparison()
        while self._match(TokenType.AND):
            op = self._previous()
            right = self._comparison()
            expr = BinaryExpr(left=expr, op=op.type, right=right, span=span_join(expr.span, right.span))
        return expr

    def _comparison(self) -> Expr:
        expr = self._term()
        while self._match(TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
            op = self._previous()
            right = self._term()
            expr = BinaryExpr(left=expr, op=op.type, right=right, span=span_join(expr.span, right.span))
        return expr

    def _term(self) -> Expr:
        expr = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op = self._previous()
            right = self._factor()
            expr = BinaryExpr(left=expr, op=op.type, right=right, span=span_join(expr.span, right.span))
        return expr

    def _factor(self) -> Expr:
        expr = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._previous()
            right = self._unary()
            expr = BinaryExpr(left=expr, op=op.type, right=right, span=span_join(expr.span, right.span))
        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.NOT, TokenType.MINUS):
            op = self._previous()
            right = self._unary()
            return UnaryExpr(op=op.type, right=right, span=span_join(span_from_tokens(op, op), right.span))
        return self._postfix()

    def _postfix(self) -> Expr:
        expr = self._primary()
        while True:
            if self._match(TokenType.LBRACKET):
                lbr = self._previous()
                idx = self._expression()
                rbr = self._consume(TokenType.RBRACKET, "Expected `]` after index.")
                expr = IndexExpr(collection=expr, index=idx, span=span_from_tokens(lbr, rbr))
                continue
            break
        return expr

    def _primary(self) -> Expr:
        if self._match(TokenType.NUMBER):
            t = self._previous()
            return LiteralExpr(value=t.literal, span=span_from_tokens(t, t))

        if self._match(TokenType.STRING):
            t = self._previous()
            return LiteralExpr(value=t.literal, span=span_from_tokens(t, t))

        if self._match(TokenType.TRUE):
            t = self._previous()
            return LiteralExpr(value=True, span=span_from_tokens(t, t))

        if self._match(TokenType.FALSE):
            t = self._previous()
            return LiteralExpr(value=False, span=span_from_tokens(t, t))

        if self._match(TokenType.EMPTY):
            t = self._previous()
            return LiteralExpr(value=None, span=span_from_tokens(t, t))

        if self._match(TokenType.IDENT):
            t = self._previous()
            return NameExpr(name=t.lexeme, span=span_from_tokens(t, t))

        if self._match(TokenType.LPAREN):
            lpar = self._previous()
            expr = self._expression()
            rpar = self._consume(TokenType.RPAREN, "Expected `)` after expression.")
            return GroupExpr(expr=expr, span=span_from_tokens(lpar, rpar))

        raise self._error(self._peek(), "Expected an expression.")

    # ---------- utilities ----------

    def _consume_newlines(self) -> None:
        while self._match(TokenType.NEWLINE):
            pass

    def _match(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _consume(self, ttype: TokenType, message: str) -> Token:
        if self._check(ttype):
            return self._advance()
        raise self._error(self._peek(), message)

    def _check(self, ttype: TokenType) -> bool:
        if self._is_at_end():
            return ttype == TokenType.EOF
        return self._peek().type == ttype

    def _check_any(self, types: Set[TokenType]) -> bool:
        if self._is_at_end():
            return TokenType.EOF in types
        return self._peek().type in types

    def _advance(self) -> Token:
        if not self._is_at_end():
            self._i += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        return self.tokens[self._i]

    def _previous(self) -> Token:
        return self.tokens[self._i - 1]

    def _error(self, token: Token, message: str) -> RillParseError:
        return RillParseError(message, token)