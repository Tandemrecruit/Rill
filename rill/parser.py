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
    ListExpr,
    DictExpr,
    DictEntry,
    FieldExpr,
    IndexExpr,
    CallExpr,
    CallArg,
    Param,
    Target,
    NameTarget,
    IndexTarget,
    FieldTarget,
    Stmt,
    ShowStmt,
    SetStmt,
    ChangeStmt,
    StopStmt,
    SkipStmt,
    DefineStmt,
    GiveBackStmt,
    IfBranch,
    IfStmt,
    RepeatTimesStmt,
    RepeatWhileStmt,
    RepeatForRangeStmt,
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
        """
        Parse the next statement from the token stream and return its corresponding AST node.
        
        Supports the statement forms: `show`, `set`, `change`, `stop`, `skip`, `if`, `repeat`, `define`, and `give back`. Consumes the tokens that constitute the parsed statement and constructs the appropriate Stmt variant with a span covering the statement.
        
        Returns:
            Stmt: The AST node representing the parsed statement.
        
        Raises:
            RillParseError: If the upcoming tokens do not form a valid statement.
        """
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

        if self._match(TokenType.DEFINE):
            return self._define_statement(self._previous())

        if self._match(TokenType.GIVE):
            return self._give_back_statement(self._previous())

        raise self._error(self._peek(), "Expected a statement (show/set/change/if/repeat/define/give back).")

    def _require_newline(self, message: str) -> Token:
        """
        Ensure the next token is a newline.
        
        Parameters:
            message (str): Error message used to construct the parse error if a newline is not found.
        
        Returns:
            Token: The consumed NEWLINE token.
        
        Raises:
            RillParseError: If the next token is not a NEWLINE.
        """
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
                raise self._error(self._peek(), "Expected a newline after `otherwise`.")
            else_body = self._block({TokenType.END})
            break


        end_tok = self._consume(TokenType.END, "Expected `end` to close the `if` block.")
        return IfStmt(branches=branches, else_body=else_body, span=span_from_tokens(if_tok, end_tok))

    def _repeat_statement(self, repeat_tok: Token) -> Stmt:
        # repeat while <expr> NEWLINE <block> end
        # repeat <expr> times NEWLINE <block> end
        """
        Parse a `repeat` statement, supporting both `repeat while <expr>` and `repeat <expr> times` forms.
        
        Parses either a conditional repeat (`repeat while <expr>`) or a counted repeat (`repeat <expr> times`), consumes the body up to the closing `end`, and returns the corresponding AST statement node with a span covering the whole construct.
        
        Returns:
            RepeatWhileStmt or RepeatTimesStmt: A `RepeatWhileStmt` for the `repeat while` form, or a `RepeatTimesStmt` for the counted `repeat ... times` form.
        
        Raises:
            RillParseError: If required tokens are missing or the repeat syntax is malformed (for example missing `times`, missing newline after the header, or missing closing `end`).
        """
        if self._match(TokenType.WHILE):
            cond = self._expression()
            self._require_newline("Expected a newline after the `repeat while` condition.")
            body = self._block({TokenType.END})
            end_tok = self._consume(TokenType.END, "Expected `end` to close the `repeat` block.")
            return RepeatWhileStmt(condition=cond, body=body, span=span_from_tokens(repeat_tok, end_tok))

        # repeat for i from A to B (step S)?
        # repeat for i from A until B (step S)?
        if self._match(TokenType.FOR):
            var_tok = self._consume(TokenType.IDENT, "Expected a loop variable name after `repeat for`.")
            self._consume(TokenType.FROM, "Expected `from` after loop variable name.")
            start_expr = self._expression()

            inclusive: bool
            if self._match(TokenType.TO):
                inclusive = True
            elif self._match(TokenType.UNTIL):
                inclusive = False
            else:
                raise self._error(self._peek(), "Expected `to` or `until` after range start expression.")

            end_expr = self._expression()

            step_expr = None
            if self._match(TokenType.STEP):
                step_expr = self._expression()

            self._require_newline("Expected a newline after the `repeat for ...` header.")
            body = self._block({TokenType.END})
            end_tok = self._consume(TokenType.END, "Expected `end` to close the `repeat` block.")
            return RepeatForRangeStmt(
                var=var_tok.lexeme,
                start=start_expr,
                end=end_expr,
                inclusive=inclusive,
                step=step_expr,
                body=body,
                span=span_from_tokens(repeat_tok, end_tok),
            )

        count = self._expression()
        self._consume(TokenType.TIMES, "Expected `times` after repeat count.")
        self._require_newline("Expected a newline after `repeat ... times`.")
        body = self._block({TokenType.END})
        end_tok = self._consume(TokenType.END, "Expected `end` to close the `repeat` block.")
        return RepeatTimesStmt(count=count, body=body, span=span_from_tokens(repeat_tok, end_tok))


    def _define_statement(self, define_tok: Token) -> DefineStmt:
        # define <name> (taking <param>(, <param>)*)? NEWLINE <block> end
        """
        Parse a function definition statement and return a DefineStmt AST node.
        
        Parses a signature of the form:
          define <name> (taking <param> (',' <param>)*)? NEWLINE <block> end
        Parameters may have optional default expressions using `=`.
        
        Returns:
            DefineStmt: AST node with the function name, list of Param (each with name, optional default, and span),
                        the function body as a list of statements, and a span covering the entire definition.
        
        Raises:
            RillParseError: if the function name is missing, a parameter name is missing after `taking`,
                            no parameters follow `taking`, the signature is not terminated by a newline,
                            or the definition is not closed with `end`.
        """
        name_tok = self._consume(TokenType.IDENT, "Expected a function name after `define`.")
        params: List[Param] = []

        if self._match(TokenType.TAKING):
            if self._check(TokenType.NEWLINE):
                raise self._error(self._peek(), "Expected at least one parameter name after `taking`.")

            seen_default = False
            while True:
                p_tok = self._consume(TokenType.IDENT, "Expected a parameter name.")
                default: Optional[Expr] = None
                if self._match(TokenType.EQ):
                    seen_default = True
                    default = self._expression()
                    p_span = span_join(span_from_tokens(p_tok, p_tok), default.span)
                else:
                    if seen_default:
                        raise self._error(p_tok, "Required parameters must come before parameters with defaults.")
                    p_span = span_from_tokens(p_tok, p_tok)

                params.append(Param(name=p_tok.lexeme, default=default, span=p_span))

                if not self._match(TokenType.COMMA):
                    break

        self._require_newline("Expected a newline after the function signature.")
        body = self._block({TokenType.END})
        end_tok = self._consume(TokenType.END, "Expected `end` to close the function definition.")
        return DefineStmt(name=name_tok.lexeme, params=params, body=body, span=span_from_tokens(define_tok, end_tok))

    def _give_back_statement(self, give_tok: Token) -> GiveBackStmt:
        # give back <expr>?
        """
        Parse a `give back` statement and produce its corresponding AST node.
        
        Consumes the required `back` token after `give`. If the next token is a newline or EOF, returns a GiveBackStmt with `expr=None`; otherwise parses the following expression and returns a GiveBackStmt whose span covers from the initial `give` token through the expression.
        
        Parameters:
            give_tok (Token): The `give` token that begins the statement; used to compute the node span.
        
        Returns:
            GiveBackStmt: An AST node representing the parsed `give back` statement. If no expression is present, `expr` is `None`.
        """
        back_tok = self._consume(TokenType.BACK, "Expected `back` after `give`.")

        if self._check(TokenType.NEWLINE) or self._check(TokenType.EOF):
            return GiveBackStmt(expr=None, span=span_from_tokens(give_tok, back_tok))

        expr = self._expression()
        return GiveBackStmt(expr=expr, span=span_join(span_from_tokens(give_tok, back_tok), expr.span))

    def _target(self) -> Target:
        # v0: name, name[index], name.field, and chained combos
        """
        Parse an assignable target (a variable, indexed target, or field target) after a `change` statement.
        
        Parses an initial identifier and then any number of dot-field or bracket-index postfixes (e.g., `x`, `x.y`, `x[y]`, `x.y[z].w`), then converts the final expression into the corresponding Target variant.
        
        Returns:
            Target: A NameTarget for a bare identifier, an IndexTarget if the final form is an index expression, or a FieldTarget if the final form is a field expression.
        
        Raises:
            RillParseError: If the input does not form a valid assignment target.
        """
        name_tok = self._consume(TokenType.IDENT, "Expected a variable name after `change`.")
        base: Expr = NameExpr(name=name_tok.lexeme, span=span_from_tokens(name_tok, name_tok))

        while True:
            if self._match(TokenType.DOT):
                dot = self._previous()
                field = self._consume(TokenType.IDENT, "Expected a field name after `.`.")
                base = FieldExpr(object=base, name=field.lexeme, span=span_join(base.span, span_from_tokens(dot, field)))
                continue

            if self._match(TokenType.LBRACKET):
                lbr = self._previous()
                idx = self._expression()
                rbr = self._consume(TokenType.RBRACKET, "Expected `]` after index.")
                base = IndexExpr(collection=base, index=idx, span=span_join(base.span, span_from_tokens(lbr, rbr)))
                continue

            break

        # convert final postfix expression to an assignable target
        if isinstance(base, NameExpr):
            return NameTarget(name=base.name, span=base.span)
        if isinstance(base, IndexExpr):
            return IndexTarget(collection=base.collection, index=base.index, span=base.span)
        if isinstance(base, FieldExpr):
            return FieldTarget(object=base.object, name=base.name, span=base.span)

        raise self._error(self._peek(), "Invalid assignment target.")

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
        """
        Parse and apply postfix operators (function calls, indexing, and field access) to a primary expression.
        
        Continues consuming successive postfix forms after a primary: function calls with positional or named arguments (identifier = expression), indexing with square brackets, and dot field access. Stops when no postfix applies.
        
        Returns:
        	an Expr: the primary expression with any parsed CallExpr, IndexExpr, or FieldExpr postfixes applied (or the original primary if none).
        """
        expr = self._primary()
        while True:
            # function calls
            if self._match(TokenType.LPAREN):
                lpar = self._previous()
                args: List[CallArg] = []

                if not self._check(TokenType.RPAREN):
                    while True:
                        # named arg: ident = expr
                        if self._check(TokenType.IDENT) and self._peek_n(1).type == TokenType.EQ:
                            name_tok = self._consume(TokenType.IDENT, "expected argument name")
                            eq_tok = self._consume(TokenType.EQ, "expected '=' after argument name")
                            val = self._expression()
                            arg_span = span_join(span_from_tokens(name_tok, eq_tok), val.span)
                            args.append(CallArg(name=name_tok.lexeme, value=val, span=arg_span))
                        else:
                            val = self._expression()
                            args.append(CallArg(name=None, value=val, span=val.span))

                        if not self._match(TokenType.COMMA):
                            break

                rpar = self._consume(TokenType.RPAREN, "Expected `)` after arguments.")
                expr = CallExpr(callee=expr, args=args, span=span_join(expr.span, span_from_tokens(lpar, rpar)))
                continue

            # indexing
            if self._match(TokenType.LBRACKET):
                lbr = self._previous()
                idx = self._expression()
                rbr = self._consume(TokenType.RBRACKET, "Expected `]` after index.")
                expr = IndexExpr(collection=expr, index=idx, span=span_join(expr.span, span_from_tokens(lbr, rbr)))
                continue


            # field access
            if self._match(TokenType.DOT):
                dot = self._previous()
                name_tok = self._consume(TokenType.IDENT, "Expected a field name after `.`.")
                expr = FieldExpr(object=expr, name=name_tok.lexeme, span=span_join(expr.span, span_from_tokens(dot, name_tok)))
                continue

            break
        return expr

    def _primary(self) -> Expr:
        """
        Parse a primary expression and produce the corresponding AST node.
        
        Supported primary forms: numeric and string literals, boolean and empty literals, list and dict literals, identifiers (names), and parenthesized expressions. List literals produce a ListExpr, dict literals produce a DictExpr containing DictEntry items, and parenthesized inputs produce a GroupExpr.
        
        Returns:
            Expr: The AST node representing the parsed primary expression.
        
        Raises:
            RillParseError: If the next token does not begin any recognized primary form.
        """
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

        if self._match(TokenType.LBRACKET):
            lbr = self._previous()
            elements: List[Expr] = []
            if not self._check(TokenType.RBRACKET):
                while True:
                    elements.append(self._expression())
                    if not self._match(TokenType.COMMA):
                        break
            rbr = self._consume(TokenType.RBRACKET, "Expected `]` after list literal.")
            return ListExpr(elements=elements, span=span_from_tokens(lbr, rbr))

        if self._match(TokenType.LBRACE):
            lbr = self._previous()
            entries: List[DictEntry] = []
            if not self._check(TokenType.RBRACE):
                while True:
                    # key: IDENT or STRING
                    if self._match(TokenType.IDENT):
                        key_tok = self._previous()
                        key = key_tok.lexeme
                        key_span = span_from_tokens(key_tok, key_tok)
                    elif self._match(TokenType.STRING):
                        key_tok = self._previous()
                        key = key_tok.literal
                        key_span = span_from_tokens(key_tok, key_tok)
                    else:
                        raise self._error(self._peek(), "Expected a key (name or string) in dict literal.")

                    self._consume(TokenType.COLON, "Expected `:` after dict key.")
                    val = self._expression()
                    entries.append(DictEntry(key=str(key), value=val, span=span_join(key_span, val.span)))

                    if not self._match(TokenType.COMMA):
                        break
            rbr = self._consume(TokenType.RBRACE, "Expected `}` after dict literal.")
            return DictExpr(entries=entries, span=span_from_tokens(lbr, rbr))

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
        """
        Get the current lookahead token without advancing the parser.
        
        Returns:
            Token: The token at the parser's current index (the current lookahead). If the parser is at the end, this will be the EOF token.
        """
        return self.tokens[self._i]

    def _peek_n(self, n: int) -> Token:
        """
        Return the token that is n positions ahead of the current parser index without advancing the parser.
        
        Parameters:
            n (int): Number of tokens to look ahead (0 returns the current token).
        
        Returns:
            Token: The token at the lookahead position, or the last token if the requested position is past the end of the token list.
        """
        j = self._i + n
        if j >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[j]

    def _previous(self) -> Token:
        """
        Get the most recently consumed token.
        
        Returns:
            Token: The token immediately before the current parser position.
        """
        return self.tokens[self._i - 1]

    def _error(self, token: Token, message: str) -> RillParseError:
        return RillParseError(message, token)