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


def test_if_executes_branch_and_scopes():
    src = "\n".join([
        "set x to 0",
        "if true",
        "    set y to 1",
        "    change x to 5",
        "otherwise",
        "    change x to 9",
        "end",
        "show x",
        "",
    ])
    out = run_src(src)
    assert out == ["5"]

    # y is block-scoped: should error outside
    src2 = "\n".join([
        "if true",
        "    set y to 1",
        "end",
        "show y",
        "",
    ])
    with pytest.raises(RillRuntimeError):
        run_src(src2)

def test_repeat_times_and_stop_skip():
    src = "\n".join([
        "set total to 0",
        "repeat 5 times",
        "    change total to total + 1",
        "end",
        "show total",
        "",
    ])
    out = run_src(src)
    assert out == ["5"]

    # stop at 3
    src2 = "\n".join([
        "set x to 0",
        "repeat 10 times",
        "    if x = 3",
        "        stop",
        "    end",
        "    change x to x + 1",
        "end",
        "show x",
        "",
    ])
    out2 = run_src(src2)
    assert out2 == ["3"]

    # skip when x = 3
    src3 = "\n".join([
        "set x to 0",
        "set c to 0",
        "repeat 5 times",
        "    change x to x + 1",
        "    if x = 3",
        "        skip",
        "    end",
        "    change c to c + 1",
        "end",
        "show c",
        "",
    ])
    out3 = run_src(src3)
    assert out3 == ["4"]

def test_repeat_allows_set_each_iteration():
    src = "\n".join([
        "repeat 2 times",
        "    set t to 1",
        "end",
        "show 0",
        "",
    ])
    out = run_src(src)
    assert out == ["0"]

def test_repeat_for_range_inclusive_until_and_step():
    # inclusive `to`
    src = """set total to 0
repeat for i from 1 to 5
    change total to total + i
end
show total
"""
    out = run_src(src)
    assert out == ["15"]

    # exclusive `until`
    src2 = """set c to 0
repeat for i from 0 until 5
    change c to c + 1
end
show c
"""
    out2 = run_src(src2)
    assert out2 == ["5"]

    # descending with explicit negative step
    src3 = """set total to 0
repeat for i from 5 to 1 step -1
    change total to total + i
end
show total
"""
    out3 = run_src(src3)
    assert out3 == ["15"]


def test_repeat_for_range_descending_requires_step():
    src = """repeat for i from 5 to 1
    show i
end
"""
    with pytest.raises(RillRuntimeError):
        run_src(src)
