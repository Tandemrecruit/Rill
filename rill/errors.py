from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .ast import NodeSpan
from .token import Token

def span_from_token(token: Token) -> NodeSpan:
    return NodeSpan(
        start_line=token.line,
        start_col=token.col,
        end_line=token.end_line,
        end_col=token.end_col,
        start_index=token.start_index,
        end_index=token.end_index,
    )

@dataclass(frozen=True)
class _LineInfo:
    text: str
    caret: str


def _line_and_caret(source: str, span: NodeSpan) -> _LineInfo:
    lines = source.splitlines()
    if not (1 <= span.start_line <= len(lines)):
        return _LineInfo(text="", caret="")
    
    line_text = lines[span.start_line - 1]
    # columns are 1-based; underline is half-open [start_col, end_col]
    start_col = max(1, span.start_col)
    end_col = max(start_col + 1, span.end_col) if span.end_line == span.start_line else len(line_text) + 1

    # Clamp to visible range (allow caret at EOL)
    max_col = len(line_text) + 1
    start_col = min(start_col, max_col)
    end_col = min(max(end_col, start_col + 1), max_col)

    prefix = " " * (start_col - 1)
    carets = "^" * max(1, end_col - start_col)
    return _LineInfo(text=line_text, caret=prefix + carets)

def format_rill_error(source: str, filename: str, error: Exception) -> str:
    """Render a Rill error with a source line + caret underline when possible."""
    message = getattr(error, "message", str(error))
    span = getattr(error, "span", None)

    if not isinstance(span, NodeSpan):
        #Fall back to whatever the exception already formats.
        return str(error)

    header = f"{filename}:{span.start_line}:{span.start_col}: {error.__class__.__name__}: {message}"
    info = _line_and_caret(source, span)
    if info.text:
        return "\n".join([header, info.text, info.caret])
    return header

class RillError(Exception):
    """Base error type for Rill with optional span."""

    def __init__(self, message: str, span: Optional[NodeSpan] = None):
        self.message = message
        self.span = span
        if span is not None:
            super().__init__(f"Line {span.start_line}, col {span.start_col}: {message}")
        else:
            super().__init__(message)

class RillLexError(RillError):
    """Lexer error with location info."""

    
class RillParseError(RillError):
    def __init__(self, message: str, token: Token):
        self.token = token
        super().__init__(message, span_from_token(token))

class RillRuntimeError(RillError):
    pass