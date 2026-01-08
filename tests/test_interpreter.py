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
    """
    Given a descending `for` range (`i from 5 to 1`) with no explicit `step`, running the program raises a `RillRuntimeError`.
    """
    src = """repeat for i from 5 to 1
    show i
end
"""
    with pytest.raises(RillRuntimeError):
        run_src(src)


def test_repeat_for_range_zero_step_raises_error():
    """Zero step should raise a RillRuntimeError."""
    src = """repeat for i from 1 to 5 step 0
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"step.*cannot be 0"):
        run_src(src)


def test_repeat_for_range_non_integer_start_end_step():
    """Non-integer start/end/step inputs should raise validation errors."""
    # Non-integer start
    src1 = """repeat for i from 1.5 to 5
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*start"):
        run_src(src1)

    # Non-integer end
    src2 = """repeat for i from 1 to 5.5
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*end"):
        run_src(src2)

    # Non-integer step
    src3 = """repeat for i from 1 to 5 step 1.5
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*whole.*step"):
        run_src(src3)

    # Boolean start (should error with "Expected a start")
    src4 = """repeat for i from true to 5
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*start"):
        run_src(src4)

    # String end (should error with "Expected a whole end")
    src5 = """repeat for i from 1 to "5"
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*whole.*end"):
        run_src(src5)


def test_repeat_for_range_single_iteration():
    """Single-iteration range (from 1 to 1) should execute once."""
    src = """set count to 0
repeat for i from 1 to 1
    change count to count + 1
    show i
end
show count
"""
    out = run_src(src)
    assert out == ["1", "1"]


def test_repeat_for_range_empty_range():
    """Explicitly empty ranges (e.g., from 5 to 1 without negative step) produce zero iterations."""
    # Ascending empty range (5 to 1 without step)
    src1 = """set count to 0
repeat for i from 5 to 1
    change count to count + 1
end
show count
"""
    with pytest.raises(RillRuntimeError, match=r"Range is descending but no `step`"):
        run_src(src1)

    # Explicitly empty range with positive step (5 to 1 step 1)
    src2 = """set count to 0
repeat for i from 5 to 1 step 1
    change count to count + 1
end
show count
"""
    with pytest.raises(RillRuntimeError, match=r"Descending range requires a negative `step`"):
        run_src(src2)

    # Empty range: from 1 until 1 (exclusive, should be zero iterations)
    src3 = """set count to 0
repeat for i from 1 until 1
    change count to count + 1
end
show count
"""
    out3 = run_src(src3)
    assert out3 == ["0"]


def test_repeat_for_range_stop_skip_control_flow():
    """Loop control flow (stop/skip) inside range loops behaves as expected."""
    # stop inside range loop
    src1 = """set count to 0
repeat for i from 1 to 10
    change count to count + 1
    if i = 5
        stop
    end
end
show count
"""
    out1 = run_src(src1)
    assert out1 == ["5"]  # Should stop at i=5, so count is 5 (1, 2, 3, 4, 5)

    # skip inside range loop
    src2 = """set count to 0
repeat for i from 1 to 5
    if i = 3
        skip
    end
    change count to count + 1
end
show count
"""
    out2 = run_src(src2)
    assert out2 == ["4"]  # Should skip i=3, so count is 4 (1, 2, 4, 5)

    # stop with descending range
    src3 = """set count to 0
repeat for i from 10 to 1 step -1
    change count to count + 1
    if i = 5
        stop
    end
end
show count
"""
    out3 = run_src(src3)
    assert out3 == ["6"]  # Should stop at i=5, so count is 6 (10, 9, 8, 7, 6, 5)

    # skip with until (exclusive)
    src4 = """set count to 0
repeat for i from 0 until 5
    if i = 2
        skip
    end
    change count to count + 1
end
show count
"""
    out4 = run_src(src4)
    assert out4 == ["4"]  # Should skip i=2, so count is 4 (0, 1, 3, 4)