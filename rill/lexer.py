from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .errors import RillLexError, Span
from .token import Token, TokenType, KEYWORDS


@dataclass
class Lexer:
    source: str
    filename: str = "<memory>"

    def __post_init__(self) -> None:
        self._i = 0
        self._line = 1
        self._col = 1
        self._tokens: List[Token] = []

    def lex(self) -> List[Token]:
        while not self._is_at_end():
            ch = self._peek()

            # whitespace (but not newline)
            if ch in (" ", "\t", "\r"):
                self._advance()
                continue

            # comments
            if ch == "#":
                self._consume_comment()
                continue

            # newline
            if ch == "\n":
                self._emit(TokenType.NEWLINE, "\n", None, self._line, self._col)
                self._advance_newline()
                continue

            # strings
            if ch in ("\"", "'"):
                self._lex_string()
                continue

            # numbers
            if ch.isdigit():
                self._lex_number()
                continue

            # identifiers / keywords
            if ch.isalpha() or ch == "_":
                self._lex_ident_or_keyword()
                continue

            # two-char operators
            if ch == "!" and self._peek_next() == "=":
                line, col = self._line, self._col
                self._advance(); self._advance()
                self._emit(TokenType.NEQ, "!=", None, line, col)
                continue

            if ch == "<" and self._peek_next() == "=":
                line, col = self._line, self._col
                self._advance(); self._advance()
                self._emit(TokenType.LTE, "<=", None, line, col)
                continue

            if ch == ">" and self._peek_next() == "=":
                line, col = self._line, self._col
                self._advance(); self._advance()
                self._emit(TokenType.GTE, ">=", None, line, col)
                continue

            # single-char tokens
            single = {
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "*": TokenType.STAR,
                "/": TokenType.SLASH,
                "%": TokenType.PERCENT,
                "=": TokenType.EQ,
                "<": TokenType.LT,
                ">": TokenType.GT,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                ":": TokenType.COLON,
                ",": TokenType.COMMA,
                ".": TokenType.DOT,
            }
            if ch in single:
                ttype = single[ch]
                line, col = self._line, self._col
                self._advance()
                self._emit(ttype, ch, None, line, col)
                continue

            # unknown character
            span = Span(self._line, self._col, self._col)
            raise RillLexError(f"Unexpected character {ch!r}.", span)

        self._emit(TokenType.EOF, "", None, self._line, self._col)
        return self._tokens

    # ---------- lex helpers ----------

    def _emit(self, ttype: TokenType, lexeme: str, literal: Optional[object], line: int, col: int) -> None:
        self._tokens.append(Token(ttype, lexeme, literal, line, col))

    def _is_at_end(self) -> bool:
        return self._i >= len(self.source)

    def _peek(self) -> str:
        return "\0" if self._is_at_end() else self.source[self._i]

    def _peek_next(self) -> str:
        j = self._i + 1
        return "\0" if j >= len(self.source) else self.source[j]

    def _advance(self) -> str:
        ch = self.source[self._i]
        self._i += 1
        self._col += 1
        return ch

    def _advance_newline(self) -> None:
        # consumes '\n'
        self._i += 1
        self._line += 1
        self._col = 1

    def _consume_comment(self) -> None:
        # consume until newline or EOF (do not emit token)
        while not self._is_at_end() and self._peek() != "\n":
            self._advance()

    def _lex_ident_or_keyword(self) -> None:
        line, col = self._line, self._col
        start = self._i
        while not self._is_at_end():
            ch = self._peek()
            if ch.isalnum() or ch == "_":
                self._advance()
            else:
                break
        lexeme = self.source[start:self._i]
        key = lexeme.lower()
        ttype = KEYWORDS.get(key, TokenType.IDENT)
        lit = None
        if ttype == TokenType.TRUE:
            lit = True
        elif ttype == TokenType.FALSE:
            lit = False
        self._emit(ttype, lexeme, lit, line, col)

    def _lex_number(self) -> None:
        line, col = self._line, self._col
        start = self._i
        # int part
        while self._peek().isdigit():
            self._advance()
        # optional fractional part
        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()  # consume '.'
            while self._peek().isdigit():
                self._advance()
        lexeme = self.source[start:self._i]
        # parse as int if no dot, else float
        literal = float(lexeme) if "." in lexeme else int(lexeme)
        self._emit(TokenType.NUMBER, lexeme, literal, line, col)

    def _lex_string(self) -> None:
        quote = self._peek()
        line, col = self._line, self._col
        start_i = self._i
        self._advance()  # consume opening quote
    
        chars: List[str] = []
    
        while True:
            if self._is_at_end():
                raise RillLexError("Unterminated string literal.", Span(line, col, self._col))
    
            ch = self._peek()
    
            if ch == "\n":
                # strings cannot contain raw newlines in v1
                raise RillLexError("Newline in string literal. Use \\n escape or join lines.", Span(self._line, self._col, self._col))
    
            if ch == quote:
                self._advance()  # consume closing quote
                break
    
            if ch == "\\":  # escape sequence
                esc_line, esc_col = self._line, self._col
                self._advance()  # consume backslash
                esc = self._peek()
                if esc == "\0":
                    raise RillLexError("Unterminated escape sequence in string.", Span(esc_line, esc_col, esc_col))
    
                if esc == "n":
                    chars.append("\n"); self._advance(); continue
                if esc == "t":
                    chars.append("\t"); self._advance(); continue
                if esc == "r":
                    chars.append("\r"); self._advance(); continue
                if esc == "\\":  # literal backslash
                    chars.append("\\"); self._advance(); continue
                if esc == '"' and quote == '"':
                    chars.append('"'); self._advance(); continue
                if esc == "'" and quote == "'":
                    chars.append("'"); self._advance(); continue
    
                # Allow escaping the other quote too (harmless and familiar)
                if esc == '"' and quote == "'":
                    chars.append('"'); self._advance(); continue
                if esc == "'" and quote == '"':
                    chars.append("'"); self._advance(); continue
    
                raise RillLexError(f"Unknown escape sequence \\{esc}.", Span(esc_line, esc_col, esc_col))
    
            # normal character
            chars.append(ch)
            self._advance()
    
        lexeme = self.source[start_i:self._i]  # include quotes
        literal = "".join(chars)
        self._emit(TokenType.STRING, lexeme, literal, line, col)
