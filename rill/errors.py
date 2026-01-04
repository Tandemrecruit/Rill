from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .ast import NodeSpan
from .token import Token

def span_from_token(token: Token) -> NodeSpan:
    """
    Convert a Token into a NodeSpan preserving its line/column and index positions.
    
    Returns:
        NodeSpan: A NodeSpan populated with the token's `start_line`, `start_col`,
        `end_line`, `end_col`, `start_index`, and `end_index`.
    """
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
    """
    Compute the source line text and a caret underline corresponding to the given span's start line.
    
    If the span's start_line is outside the source, returns an _LineInfo with empty `text` and `caret`.
    Columns are interpreted as 1-based and the underline covers the half-open range [start_col, end_col). If the span is multi-line, the underline extends to the end of the start line. The computed caret is clamped to the visible range of the line (a caret is allowed at end-of-line) and always contains at least one `^` character.
    
    Parameters:
        source (str): Full source text (may contain multiple lines).
        span (NodeSpan): Span whose start_line/start_col/end_col determine the underline.
    
    Returns:
        _LineInfo: Immutable container with:
            text (str): The text of the span's start line (empty if start_line invalid).
            caret (str): A string of spaces and `^` characters that underlines the span on that line.
    """
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
    """
    Render an error message that includes the source line and a caret underline when the error provides a NodeSpan.
    
    If `error` has a `span` attribute of type `NodeSpan`, the returned string begins with
    "filename:start_line:start_col: ExceptionName: message" and, when the source line is available,
    is followed by the source line and a caret underline pointing at the span. If the error does not
    provide a `NodeSpan`, the function falls back to the exception's default string representation.
    
    Parameters:
        source (str): Full source text used to extract the relevant line for the span.
        filename (str): Filename or label shown in the message header.
        error (Exception): The exception to render; if it has a `message` attribute it will be used,
            and if it has a `span` attribute that is a `NodeSpan` it will be used to produce the caret.
    
    Returns:
        str: A formatted error message including header, and optionally the source line and caret underline.
    """
    message = getattr(error, "message", str(error))
    span = getattr(error, "span", None)

    if not isinstance(span, NodeSpan):
        # Fall back to whatever the exception already formats.
        return str(error)

    header = f"{filename}:{span.start_line}:{span.start_col}: {error.__class__.__name__}: {message}"
    info = _line_and_caret(source, span)
    if info.text:
        return f"{header}\n{info.text}\n{info.caret}"
    return header

class RillError(Exception):
    """Base error type for Rill with optional span."""

    def __init__(self, message: str, span: Optional[NodeSpan] = None) -> None:
        """
        Initialize a RillError with a human-readable message and optional source span.
        
        If `span` is provided, the exception's base message is prefixed with
        "Line {start_line}, col {start_col}:" where `start_line` and `start_col` are
        taken from the span; otherwise the plain `message` is used.
        
        Parameters:
            message (str): The error message.
            span (Optional[NodeSpan]): Optional source span indicating the location of the error; stored on the instance as `span`.
        """
        self.message = message
        self.span = span
        if span is not None:
            super().__init__(f"Line {span.start_line}, col {span.start_col}: {message}")
        else:
            super().__init__(message)

class RillLexError(RillError):
    """Lexer error with location info."""

    
class RillParseError(RillError):
    def __init__(self, message: str, token: Token) -> None:
        """
        Initialize a parse error with a message and a token-defined source span.
        
        Parameters:
            message (str): Human-readable error message.
            token (Token): Token whose position will be used as the error span; stored on the exception as `token`.
        """
        self.token = token
        super().__init__(message, span_from_token(token))

class RillRuntimeError(RillError):
    pass