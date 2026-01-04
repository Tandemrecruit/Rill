from __future__ import annotations
from .interpreter import Interpreter
from .runtime import RillRuntimeError

import argparse
import sys
from pathlib import Path

from .errors import RillLexError, format_rill_error
from .lexer import Lexer
from .parser import Parser, RillParseError


def _read_source(path: Path) -> str:
    """
    Read UTF-8 source text from the given file path, skipping a leading BOM if present.
    
    Parameters:
        path (Path): Path to the source file.
    
    Returns:
        source (str): File contents decoded as UTF-8 with any UTF-8 BOM removed.
    """
    return path.read_text(encoding="utf-8-sig")

def _print_error(source: str, filename: str, error: Exception) -> None:
    """
    Format and print a Rill diagnostic for an error found in the given source.
    
    Parameters:
        source (str): The source text in which the error occurred; used to show context and locations.
        filename (str): The path or name of the source file to display in the diagnostic.
        error (Exception): The error to format and print (e.g., lexer, parser, or runtime error).
    """
    print(format_rill_error(source, filename, error))


def _cmd_tokens(path: Path) -> int:
    """
    Lex and print all tokens from the Rill source file at the given path.
    
    Parameters:
        path (Path): Filesystem path to the .rill source file to lex.
    
    Returns:
        int: Exit code — `0` on success, `1` if a lexing error occurred.
    """
    src = _read_source(path)
    try:
        tokens = Lexer(src, filename=str(path)).lex()
    except RillLexError as e:
        _print_error(src, str(path), e)
        return 1

    for t in tokens:
        print(t)
    return 0


def _cmd_parse(path: Path) -> int:
    """
    Parse a Rill source file and print its AST.
    
    Parameters:
        path (Path): Path to the Rill source file to parse.
    
    Returns:
        int: Exit code: `0` on successful parse and print, `1` if a lexing or parsing error occurred (error details are printed).
    """
    src = _read_source(path)
    try:
        tokens = Lexer(src, filename=str(path)).lex()
    except RillLexError as e:
        print(str(e))
        return 1

    try:
        program = Parser(tokens, filename=str(path)).parse()
    except RillParseError as e:
        _print_error(src, str(path), e)
        return 1

    # v0: rely on dataclass repr for now
    print(program)
    return 0

def _cmd_run(path: Path) -> int:
    """
    Execute the Rill program at the given filesystem path.
    
    Reads the source file, lexes and parses it, and runs the resulting program. If a lexing, parsing, or runtime error occurs, a formatted error message is printed and the command returns a non-zero exit status.
    
    Returns:
        int: `0` on successful execution, `1` if a lexing, parsing, or runtime error occurred.
    """
    src = _read_source(path)
    try:
        tokens = Lexer(src, filename=str(path)).lex()
        program = Parser(tokens, filename=str(path)).parse()
        Interpreter().run(program)
        return 0
    except (RillLexError, RillParseError, RillRuntimeError) as e:
        _print_error(src, str(path), e)
        return 1

def main(argv: list[str] | None = None) -> int:
    """
    Command-line entry point for the Rill CLI.
    
    Parses command-line arguments and dispatches to the `tokens`, `parse`, or `run` subcommands.
    Supports the shorthand form `rill <file>` which is treated as `rill tokens <file>` for backward compatibility.
    
    Parameters:
        argv (list[str] | None): Arguments to parse (excluding the program name). If None, uses sys.argv[1:].
            If the first argument is not a flag and not one of the subcommands (`tokens`, `parse`, `run`),
            it is treated as a file path and the invocation is handled as the `tokens` command.
    
    Returns:
        int: Exit status code: `0` on success; `1` for lexing/parsing/runtime errors; `2` for unknown command or argument parsing failure.
    """

    if argv is None:
        argv = sys.argv[1:]

    # Backward compatible: if first arg isn't a known subcommand, treat it as the path
    if len(argv) >= 1 and not argv[0].startswith("-") and argv[0] not in {"tokens", "parse", "run"}:
        argv = ["tokens", *argv]


    parser = argparse.ArgumentParser(prog="rill", description="Rill v0 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_tokens = sub.add_parser("tokens", help="Print lexer tokens")
    p_tokens.add_argument("path", help="Path to a .rill file")

    p_parse = sub.add_parser("parse", help="Parse and print the AST")
    p_parse.add_argument("path", help="Path to a .rill file")

    p_run = sub.add_parser("run", help="Run the program")
    p_run.add_argument("path", help="Path to a .rill file")

    args = parser.parse_args(argv)
    path = Path(args.path)

    if args.cmd == "tokens":
        return _cmd_tokens(path)
    if args.cmd == "parse":
        return _cmd_parse(path)
    if args.cmd == "run":
        return _cmd_run(path)
    # argparse should prevent this, but keep a safe default
    print(f"Unknown command: {args.cmd}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())