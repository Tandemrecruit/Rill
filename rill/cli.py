from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import RillLexError
from .lexer import Lexer
from .parser import Parser, RillParseError


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _cmd_tokens(path: Path) -> int:
    src = _read_source(path)
    try:
        tokens = Lexer(src, filename=str(path)).lex()
    except RillLexError as e:
        print(str(e))
        return 1

    for t in tokens:
        print(t)
    return 0


def _cmd_parse(path: Path) -> int:
    src = _read_source(path)
    try:
        tokens = Lexer(src, filename=str(path)).lex()
    except RillLexError as e:
        print(str(e))
        return 1

    try:
        program = Parser(tokens, filename=str(path)).parse()
    except RillParseError as e:
        print(str(e))
        return 1

    # v0: rely on dataclass repr for now
    print(program)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Rill CLI.

    Supported forms:
      - rill <file>                (defaults to `tokens`)
      - rill tokens <file>
      - rill parse <file>
    """

    if argv is None:
        argv = sys.argv[1:]

    # Backward compatible: if first arg isn't a known subcommand, treat it as the path
    if len(argv) >= 1 and argv[0] not in {"tokens", "parse"}:
        argv = ["tokens", *argv]

    parser = argparse.ArgumentParser(prog="rill", description="Rill v0 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_tokens = sub.add_parser("tokens", help="Print lexer tokens")
    p_tokens.add_argument("path", help="Path to a .rill file")

    p_parse = sub.add_parser("parse", help="Parse and print the AST")
    p_parse.add_argument("path", help="Path to a .rill file")

    args = parser.parse_args(argv)
    path = Path(args.path)

    if args.cmd == "tokens":
        return _cmd_tokens(path)
    if args.cmd == "parse":
        return _cmd_parse(path)

    # argparse should prevent this, but keep a safe default
    print(f"Unknown command: {args.cmd}")
    return 2
