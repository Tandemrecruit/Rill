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
    """
    Explicitly empty range: `until` is exclusive, so `from 1 until 1` executes zero iterations.
    """
    src = """set count to 0
repeat for i from 1 until 1
    change count to count + 1
end
show count
"""
    out = run_src(src)
    assert out == ["0"]


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


def test_repeat_for_range_step_validation():
    """
    Test that step=0 raises an error and that step direction must match range direction.
    """
    # Step cannot be zero
    src_zero_step = """repeat for i from 1 to 5 step 0
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"step.*cannot be 0"):
        run_src(src_zero_step)
    
    # Ascending range with negative step should error
    src_wrong_direction = """repeat for i from 1 to 5 step -1
    show i
end
"""
    with pytest.raises(RillRuntimeError, match="Ascending range requires a positive"):
        run_src(src_wrong_direction)
    
    # Descending range with positive step should error  
    src_wrong_direction2 = """repeat for i from 5 to 1 step 2
    show i
end
"""
    with pytest.raises(RillRuntimeError, match="Descending range requires a negative"):
        run_src(src_wrong_direction2)


def test_repeat_for_range_with_skip_and_stop():
    """
    Test that skip and stop work correctly within for-range loops.
    """
    # Test skip - should skip even numbers
    src_skip = """set total to 0
repeat for i from 1 to 10
    if i % 2 = 0
        skip
    end
    change total to total + i
end
show total
"""
    out = run_src(src_skip)
    assert out == ["25"]  # 1+3+5+7+9 = 25
    
    # Test stop - should stop at 5
    src_stop = """set total to 0
repeat for i from 1 to 10
    if i > 5
        stop
    end
    change total to total + i
end
show total
"""
    out2 = run_src(src_stop)
    assert out2 == ["15"]  # 1+2+3+4+5 = 15


def test_repeat_for_range_variable_scoping():
    """
    Test that the loop variable is scoped to the loop body and doesn't leak out.
    """
    src = """repeat for i from 1 to 3
    show i
end
show i
"""
    # Current runtime wording is "Unknown name `i`."
    with pytest.raises(RillRuntimeError, match=r"Unknown name"):
        run_src(src)
    
    # Test that loop variable shadows outer variable
    src2 = """set i to 99
repeat for i from 1 to 3
    show i
end
show i
"""
    out2 = run_src(src2)
    assert out2 == ["1", "2", "3", "99"]


def test_repeat_for_range_nested_loops():
    """
    Test nested for-range loops work correctly.
    """
    src = """set total to 0
repeat for i from 1 to 3
    repeat for j from 1 to 2
        change total to total + i * j
    end
end
show total
"""
    out = run_src(src)
    # i=1: j=1(1) + j=2(2) = 3
    # i=2: j=1(2) + j=2(4) = 6
    # i=3: j=1(3) + j=2(6) = 9
    # total = 3 + 6 + 9 = 18
    assert out == ["18"]


def test_repeat_for_range_with_expressions():
    """
    Test that start, end, and step can be expressions, not just literals.
    """
    src = """set a to 1
set b to 5
set s to 2
set total to 0
repeat for i from a to b step s
    change total to total + i
end
show total
"""
    out = run_src(src)
    assert out == ["9"]  # 1 + 3 + 5 = 9
    
    # Test with computed values
    src2 = """set total to 0
repeat for i from 2 * 1 to 3 + 2
    change total to total + i
end
show total
"""
    out2 = run_src(src2)
    assert out2 == ["14"]  # 2+3+4+5 = 14


def test_repeat_for_range_type_errors():
    """
    Test that non-integer start, end, or step values raise appropriate errors.
    """
    # Boolean start
    src_bool_start = """repeat for i from true to 5
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*start"):
        run_src(src_bool_start)
    
    # String end
    src_str_end = """repeat for i from 1 to "5"
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*end"):
        run_src(src_str_end)
    
    # Float step that's not a whole number
    src_float_step = """repeat for i from 1 to 5 step 1.5
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*whole.*step"):
        run_src(src_float_step)
    
    # Float start that IS a whole number should work
    src_float_whole = """set count to 0
repeat for i from 1.0 to 3.0
    change count to count + 1
end
show count
"""
    out = run_src(src_float_whole)
    assert out == ["3"]

    # Non-integer start
    src_nonint_start = """repeat for i from 1.5 to 5
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*start"):
        run_src(src_nonint_start)
    
    # Non-integer end
    src_nonint_end = """repeat for i from 1 to 5.5
    show i
end
"""
    with pytest.raises(RillRuntimeError, match=r"Expected.*end"):
        run_src(src_nonint_end)


def test_repeat_for_range_large_step():
    """
    Test ranges with step sizes larger than the range.
    """
    src = """set total to 0
repeat for i from 1 to 10 step 20
    change total to total + i
end
show total
"""
    out = run_src(src)
    assert out == ["1"]  # Only executes once with i=1
    
    # Descending with large negative step
    src2 = """set total to 0
repeat for i from 10 to 1 step -20
    change total to total + i
end
show total
"""
    out2 = run_src(src2)
    assert out2 == ["10"]  # Only executes once with i=10


def test_repeat_for_range_negative_values():
    """
    Test ranges that include negative numbers.
    """
    src = """set total to 0
repeat for i from -3 to 2
    change total to total + i
end
show total
"""
    out = run_src(src)
    assert out == ["-3"]  # -3 + -2 + -1 + 0 + 1 + 2 = -3
    
    # Descending with negatives
    src2 = """set total to 0
repeat for i from 2 to -3 step -1
    change total to total + i
end
show total
"""
    out2 = run_src(src2)
    assert out2 == ["-3"]


def test_repeat_for_range_until_vs_to():
    """
    Test the difference between inclusive 'to' and exclusive 'until'.
    """
    # Inclusive 'to' executes end value
    src_to = """set count to 0
repeat for i from 1 to 3
    change count to count + 1
end
show count
"""
    out_to = run_src(src_to)
    assert out_to == ["3"]

    # Exclusive 'until' does not execute end value
    src_until = """set count to 0
repeat for i from 1 until 3
    change count to count + 1
end
show count
"""
    out_until = run_src(src_until)
    assert out_until == ["2"]


def test_repeat_for_range_body_modifies_externals():
    """
    Test that the loop body can modify variables outside the loop scope.
    """
    src = """set total to 0
set multiplier to 2
repeat for i from 1 to 3
    change total to total + i * multiplier
end
show total
"""
    out = run_src(src)
    assert out == ["12"]


def test_repeat_for_range_with_function_calls():
    """
    Test for-range loops that call functions within the body.
    """
    src = """define double taking x
    give back x * 2
end

set total to 0
repeat for i from 1 to 3
    change total to total + double(i)
end
show total
"""
    out = run_src(src)
    assert out == ["12"]  # double(1) + double(2) + double(3) = 2+4+6 = 12
