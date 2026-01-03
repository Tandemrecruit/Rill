from __future__ import annotations

import argparse
from pathlib import Path

from .lexer import Lexer
from .errors import RillLexError

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rill", description="Rill v0 lexer prototype")
    parser.add_argument("path", help="Path to a .rill file")
    args = parser.parse_args(argv)

    path = Path(args.path)
    src = path.read_text(encoding="utf-8")

    try:
        tokens = Lexer(src, filename=str(path)).lex()
    except RillLexError as e:
        print(str(e))
        return 1

    for t in tokens:
        print(t)

    return 0
