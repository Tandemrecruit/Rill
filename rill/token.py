from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

class TokenType(Enum):
    # structural
    NEWLINE = auto()
    EOF = auto()

    # literals + identifiers
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()

    # keywords
    SET = auto()
    CHANGE = auto()
    IF = auto()
    OTHERWISE = auto()
    REPEAT = auto()
    FOR = auto()
    EACH = auto()
    DEFINE = auto()
    GIVE = auto()
    BACK = auto()
    SHOW = auto()
    ASK = auto()
    STOP = auto()
    SKIP = auto()
    USE = auto()
    CHECK = auto()
    EXPECT = auto()
    END = auto()
    FROM = auto()
    TO = auto()
    UNTIL = auto()
    STEP = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    EMPTY = auto()
    RECORD = auto()
    MAP = auto()
    TRUE = auto()
    FALSE = auto()
    AS = auto()

    # operators / punctuation
    PLUS = auto()        # +
    MINUS = auto()       # -
    STAR = auto()        # *
    SLASH = auto()       # /
    PERCENT = auto()     # %
    EQ = auto()          # =
    NEQ = auto()         # !=
    LT = auto()          # <
    LTE = auto()         # <=
    GT = auto()          # >
    GTE = auto()         # >=

    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    COLON = auto()       # :
    COMMA = auto()       # ,
    DOT = auto()         # .

KEYWORDS = {
    "set": TokenType.SET,
    "change": TokenType.CHANGE,
    "if": TokenType.IF,
    "otherwise": TokenType.OTHERWISE,
    "repeat": TokenType.REPEAT,
    "for": TokenType.FOR,
    "each": TokenType.EACH,
    "define": TokenType.DEFINE,
    "give": TokenType.GIVE,
    "back": TokenType.BACK,
    "show": TokenType.SHOW,
    "ask": TokenType.ASK,
    "stop": TokenType.STOP,
    "skip": TokenType.SKIP,
    "use": TokenType.USE,
    "check": TokenType.CHECK,
    "expect": TokenType.EXPECT,
    "end": TokenType.END,
    "from": TokenType.FROM,
    "to": TokenType.TO,
    "until": TokenType.UNTIL,
    "step": TokenType.STEP,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "empty": TokenType.EMPTY,
    "record": TokenType.RECORD,
    "map": TokenType.MAP,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "as": TokenType.AS,
}

@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    literal: Any

    # 1-based, start position
    line: int
    col: int

    # 1-based, end position (EXCLUSIVE)
    end_line: int
    end_col: int

    # 0-based offsets into the original source (end_index is EXCLUSIVE)
    start_index: int
    end_index: int

    def __repr__(self) -> str:
        lit = f", literal={self.literal!r}" if self.literal is not None else ""
        span = f"{self.line}:{self.col}-{self.end_line}:{self.end_col}"
        idx = f"{self.start_index}-{self.end_index}"
        return f"Token({self.type.name}, {self.lexeme!r}{lit}, span={span}, idx={idx})"
