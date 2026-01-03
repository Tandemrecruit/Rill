from __future__ import annotations

import pytest

from rill.lexer import Lexer
from rill.parser import Parser
from rill.interpreter import Interpreter
from rill.runtime import RillRuntimeError


def run_src(src: str) -> list[str]:
    tokens = Lexer(src).lex()
    program = Parser(tokens).parse()
    out: list[str] = []
    Interpreter(output=out.append).run(program)
    return out


def test_run_set_show_change_math():
    src = "\n".join([
        "set x to 2 + 3 * 4",
        "show x",
        "change x to x + 1",
        "show x",
        "show x % 2",
        "",
    ])
    out = run_src(src)
    assert out == ["14", "15", "1"]


def test_set_existing_errors():
    src = "set x to 1\nset x to 2\n"
    with pytest.raises(RillRuntimeError):
        run_src(src)


def test_change_missing_errors():
    src = "change x to 1\n"
    with pytest.raises(RillRuntimeError):
        run_src(src)


def test_boolean_ops():
    src = "show true and false\nshow true or false\nshow not false\n"
    out = run_src(src)
    assert out == ["false", "true", "true"]
