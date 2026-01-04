from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .ast import NodeSpan
from .errors import RillLexError
from .token import Token, TokenType, KEYWORDS


@dataclass
class Lexer:
    source: str
    filename: str = "<memory>"

    def __post_init__(self) -> None:
        self._i = 0               # 0-based index into source
        self._line = 1            # 1-based
        self._col = 1             # 1-based
        self._tokens: List[Token] = []

    def lex(self) -> List[Token]:
        """
        Tokenizes the lexer's source into a sequence of Token objects.
        
        Processes the input string from the current position until end-of-file, emitting tokens for newlines, whitespace-separated symbols, comments (skipped), strings, numbers, identifiers/keywords, two-character operators, and single-character tokens. Always emits a terminating EOF token at the current position.
        
        Returns:
            List[Token]: A list of tokens produced from the source, including a final EOF token.
        
        Raises:
            RillLexError: If an unexpected character or other lexing error (e.g., unterminated string or invalid escape) is encountered; the error includes a NodeSpan locating the problem.
        """
        while not self._is_at_end():
            ch = self._peek()

            # newline handling (supports \n and \r\n, and treats bare \r as newline)
            if ch == "\n" or ch == "\r":
                self._lex_newline()
                continue

            # whitespace (but not newline)
            if ch in (" ", "\t"):
                self._advance()
                continue

            # comments
            if ch == "#":
                self._consume_comment()
                continue

            # strings
            if ch in ('"', "'"):
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
                self._lex_two_char(TokenType.NEQ)
                continue
            if ch == "<" and self._peek_next() == "=":
                self._lex_two_char(TokenType.LTE)
                continue
            if ch == ">" and self._peek_next() == "=":
                self._lex_two_char(TokenType.GTE)
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
                self._lex_one_char(single[ch])
                continue

            # unknown character
            raise RillLexError(
                f"Unexpected character {ch!r}.",
                NodeSpan(
                    start_line=self._line,
                    start_col=self._col,
                    end_line=self._line,
                    end_col=self._col,
                    start_index=self._i,
                    end_index=self._i,
                ),
            )

        # EOF token at current position
        self._emit_range(
            TokenType.EOF,
            start_i=self._i,
            end_i=self._i,
            literal=None,
            start_line=self._line,
            start_col=self._col,
            end_line=self._line,
            end_col=self._col,
        )
        return self._tokens

    # ---------- core helpers ----------

    def _emit_range(
        self,
        ttype: TokenType,
        start_i: int,
        end_i: int,
        literal: Optional[object],
        start_line: int,
        start_col: int,
        end_line: int,
        end_col: int,
    ) -> None:
        lexeme = self.source[start_i:end_i]
        self._tokens.append(
            Token(
                type=ttype,
                lexeme=lexeme,
                literal=literal,
                line=start_line,
                col=start_col,
                end_line=end_line,
                end_col=end_col,
                start_index=start_i,
                end_index=end_i,
            )
        )

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

    def _advance_newline(self, length: int) -> None:
        # consumes 1 char (\n or \r) or 2 chars (\r\n)
        self._i += length
        self._line += 1
        self._col = 1

    def _consume_comment(self) -> None:
        # consume until newline or EOF (do not emit token)
        while not self._is_at_end():
            ch = self._peek()
            if ch == "\n" or ch == "\r":
                return
            self._advance()

    # ---------- lexing routines ----------

    def _lex_newline(self) -> None:
        start_i = self._i
        start_line = self._line
        start_col = self._col

        if self._peek() == "\r" and self._peek_next() == "\n":
            self._advance_newline(2)
        else:
            self._advance_newline(1)

        end_i = self._i
        end_line = self._line
        end_col = self._col

        self._emit_range(
            TokenType.NEWLINE,
            start_i=start_i,
            end_i=end_i,
            literal=None,
            start_line=start_line,
            start_col=start_col,
            end_line=end_line,
            end_col=end_col,
        )

    def _lex_one_char(self, ttype: TokenType) -> None:
        start_i = self._i
        start_line = self._line
        start_col = self._col

        self._advance()

        self._emit_range(
            ttype,
            start_i=start_i,
            end_i=self._i,
            literal=None,
            start_line=start_line,
            start_col=start_col,
            end_line=self._line,
            end_col=self._col,
        )

    def _lex_two_char(self, ttype: TokenType) -> None:
        start_i = self._i
        start_line = self._line
        start_col = self._col

        self._advance()
        self._advance()

        self._emit_range(
            ttype,
            start_i=start_i,
            end_i=self._i,
            literal=None,
            start_line=start_line,
            start_col=start_col,
            end_line=self._line,
            end_col=self._col,
        )

    def _lex_ident_or_keyword(self) -> None:
        start_i = self._i
        start_line = self._line
        start_col = self._col

        while not self._is_at_end():
            ch = self._peek()
            if ch.isalnum() or ch == "_":
                self._advance()
            else:
                break

        end_i = self._i
        lexeme = self.source[start_i:end_i]
        key = lexeme.lower()
        ttype = KEYWORDS.get(key, TokenType.IDENT)

        literal = None
        if ttype == TokenType.TRUE:
            literal = True
        elif ttype == TokenType.FALSE:
            literal = False

        self._emit_range(
            ttype,
            start_i=start_i,
            end_i=end_i,
            literal=literal,
            start_line=start_line,
            start_col=start_col,
            end_line=self._line,
            end_col=self._col,
        )

    def _lex_number(self) -> None:
        start_i = self._i
        start_line = self._line
        start_col = self._col

        while self._peek().isdigit():
            self._advance()

        # optional fractional part
        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()  # '.'
            while self._peek().isdigit():
                self._advance()

        end_i = self._i
        lexeme = self.source[start_i:end_i]
        literal = float(lexeme) if "." in lexeme else int(lexeme)

        self._emit_range(
            TokenType.NUMBER,
            start_i=start_i,
            end_i=end_i,
            literal=literal,
            start_line=start_line,
            start_col=start_col,
            end_line=self._line,
            end_col=self._col,
        )

    def _lex_string(self) -> None:
        """
        Lexes a string literal from the current source position and emits a STRING token.
        
        Parses characters between matching single or double quotes, interprets standard escapes (`\n`, `\t`, `\r`, `\\`, `\"`, `\'`), and records the resulting string as the token literal. Emits a token whose span covers the opening quote through the closing quote.
        
        Raises:
            RillLexError: If the string is not terminated before EOF.
            RillLexError: If a raw newline is encountered inside the string.
            RillLexError: If an escape sequence is unterminated (EOF immediately after backslash).
            RillLexError: If an unknown escape sequence is encountered.
        """
        quote = self._peek()
        start_i = self._i
        start_line = self._line
        start_col = self._col

        self._advance()  # opening quote
        chars: List[str] = []

        while True:
            if self._is_at_end():
                raise RillLexError(
                    "Unterminated string literal.",
                    NodeSpan(
                        start_line=start_line,
                        start_col=start_col,
                        end_line=start_line,
                        end_col=start_col +1,
                        start_index=start_i,
                        end_index=start_i + 1,
                    ),
                )

            ch = self._peek()

            # no raw newlines inside strings in v1
            if ch == "\n" or ch == "\r":
                raise RillLexError(
                    "Newline in string literal. Use \\n escape or join lines.",
                    NodeSpan(
                        start_line=self._line,
                        start_col=self._col,
                        end_line=self._line,
                        end_col=self._col + 1,
                        start_index=self._i,
                        end_index=min(len(self.source), self._i + 1),
                    ),
                )

            if ch == quote:
                self._advance()  # closing quote
                break

            if ch == "\\":  # escape
                esc_line, esc_col, esc_i = self._line, self._col, self._i
                self._advance()  # backslash
                esc = self._peek()
                if esc == "\0":
                    raise RillLexError(
                        "Unterminated escape sequence in string.",
                        NodeSpan(
                            start_line=esc_line,
                            start_col=esc_col,
                            end_line=esc_line,
                            end_col=esc_col + 1,
                            start_index=esc_i,
                            end_index=min(len(self.source), esc_i + 1),
                        ),
                    )

                if esc == "n":
                    chars.append("\n")
                    self._advance()
                    continue
                if esc == "t":
                    chars.append("\t")
                    self._advance() 
                    continue
                if esc == "r":
                    chars.append("\r")
                    self._advance() 
                    continue
                if esc == "\\":
                    chars.append("\\")
                    self._advance() 
                    continue
                if esc == '"':
                    chars.append('"') 
                    self._advance() 
                    continue
                if esc == "'":
                    chars.append("'") 
                    self._advance() 
                    continue

                raise RillLexError(
                    f"Unknown escape sequence \\\\{esc}.",
                    NodeSpan(
                        start_line=esc_line,
                        start_col=esc_col,
                        end_line=esc_line,
                        end_col=esc_col + 1,
                        start_index=esc_i,
                        end_index=min(len(self.source), esc_i + 1),
                    ),
                )

            chars.append(ch)
            self._advance()

        end_i = self._i
        literal = "".join(chars)

        self._emit_range(
            TokenType.STRING,
            start_i=start_i,
            end_i=end_i,
            literal=literal,
            start_line=start_line,
            start_col=start_col,
            end_line=self._line,
            end_col=self._col,
        )