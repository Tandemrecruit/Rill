from dataclasses import dataclass

@dataclass
class Span:
    line: int
    col: int
    end_col: int

class RillLexError(Exception):
    """Lexer error with location info."""

    def __init__(self, message: str, span: Span):
        super().__init__(f"Line {span.line}, col {span.col}: {message}")
        self.message = message
        self.span = span
