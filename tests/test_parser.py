from rill.lexer import Lexer
import pytest
from rill.parser import Parser
from rill.errors import RillParseError
from rill.ast import (
    Program,
    ShowStmt,
    SetStmt,
    ChangeStmt,
    BinaryExpr,
    UnaryExpr,
    LiteralExpr,
    NameExpr,
    IndexExpr,
    NameTarget,
    IndexTarget,
    RepeatForRangeStmt,
)
from rill.token import TokenType


def parse(src: str) -> Program:
    tokens = Lexer(src).lex()
    return Parser(tokens).parse()


def test_parse_simple_program():
    prog = parse(
        "set x to 2 + 3 * 4\n"
        "show x\n"
        "change x to x + 1\n"
        "show x % 2\n"
    )
    assert len(prog.statements) == 4
    assert isinstance(prog.statements[0], SetStmt)
    assert isinstance(prog.statements[1], ShowStmt)
    assert isinstance(prog.statements[2], ChangeStmt)
    assert isinstance(prog.statements[3], ShowStmt)


def test_precedence_mul_before_add():
    prog = parse("show 2 + 3 * 4\n")
    stmt = prog.statements[0]
    assert isinstance(stmt, ShowStmt)
    expr = stmt.expr
    assert isinstance(expr, BinaryExpr)
    assert expr.op == TokenType.PLUS
    assert isinstance(expr.left, LiteralExpr)
    assert expr.left.value == 2
    assert isinstance(expr.right, BinaryExpr)
    assert expr.right.op == TokenType.STAR
    assert expr.right.left.value == 3
    assert expr.right.right.value == 4


def test_unary_minus_binds_tight():
    prog = parse("show -1 + 2\n")
    expr = prog.statements[0].expr
    assert isinstance(expr, BinaryExpr)
    assert expr.op == TokenType.PLUS
    assert isinstance(expr.left, UnaryExpr)
    assert expr.left.op == TokenType.MINUS
    assert expr.left.right.value == 1


def test_and_or_precedence():
    prog = parse("show true or false and false\n")
    expr = prog.statements[0].expr
    assert isinstance(expr, BinaryExpr)
    assert expr.op == TokenType.OR
    assert expr.left.value is True
    assert isinstance(expr.right, BinaryExpr)
    assert expr.right.op == TokenType.AND


def test_grouping_overrides_precedence():
    prog = parse("show (2 + 3) * 4\n")
    expr = prog.statements[0].expr
    assert isinstance(expr, BinaryExpr)
    assert expr.op == TokenType.STAR
    # Parentheses force (2+3) to be evaluated before * 4
    from rill.ast import GroupExpr
    assert isinstance(expr.left, GroupExpr)
    inner = expr.left.expr
    assert isinstance(inner, BinaryExpr)
    assert inner.op == TokenType.PLUS
    assert inner.left.value == 2
    assert inner.right.value == 3
    assert expr.right.value == 4


def test_index_expression():
    prog = parse("show names[0]\n")
    expr = prog.statements[0].expr
    assert isinstance(expr, IndexExpr)
    assert isinstance(expr.collection, NameExpr)
    assert expr.collection.name == "names"
    assert expr.index.value == 0


def test_change_target_name_and_index():
    prog = parse("change x to 1\nchange names[0] to 2\n")
    s0 = prog.statements[0]
    s1 = prog.statements[1]
    assert isinstance(s0, ChangeStmt)
    assert isinstance(s0.target, NameTarget)
    assert s0.target.name == "x"

    assert isinstance(s1, ChangeStmt)
    assert isinstance(s1.target, IndexTarget)
    assert s1.target.index.value == 0


def test_parse_if_otherwise():
    src = "if true\nshow 1\notherwise\nshow 2\nend\n"
    program = Parser(Lexer(src).lex()).parse()
    assert len(program.statements) == 1
    assert program.statements[0].__class__.__name__ == "IfStmt"

def test_parse_repeat_times_and_while():
    src = "repeat 3 times\nshow 1\nend\nrepeat while false\nshow 2\nend\n"
    program = Parser(Lexer(src).lex()).parse()
    assert program.statements[0].__class__.__name__ == "RepeatTimesStmt"
    assert program.statements[1].__class__.__name__ == "RepeatWhileStmt"

def test_parse_repeat_for_range_to_and_until():
    """
    Given source containing two repeat-for-range blocks (one using "to", one using "until" with a step), parsing should produce two top-level RepeatForRangeStmt nodes.
    """
    src = """repeat for i from 1 to 3
show i
end
repeat for j from 0 until 2 step 1
show j
end
"""
    program = Parser(Lexer(src).lex()).parse()

    # First statement: repeat for i from 1 to 3
    stmt0 = program.statements[0]
    assert isinstance(stmt0, RepeatForRangeStmt)
    assert stmt0.var == "i"
    assert isinstance(stmt0.start, LiteralExpr)
    assert stmt0.start.value == 1
    assert isinstance(stmt0.end, LiteralExpr)
    assert stmt0.end.value == 3
    assert stmt0.inclusive is True
    assert stmt0.step is None
    
    # Second statement: repeat for j from 0 until 2 step 1
    stmt1 = program.statements[1]
    assert isinstance(stmt1, RepeatForRangeStmt)
    assert stmt1.var == "j"
    assert isinstance(stmt1.start, LiteralExpr)
    assert stmt1.start.value == 0
    assert isinstance(stmt1.end, LiteralExpr)
    assert stmt1.end.value == 2
    assert stmt1.inclusive is False
    assert isinstance(stmt1.step, LiteralExpr)
    assert stmt1.step.value == 1
def test_parse_repeat_for_range_fields():
    """
    Test that RepeatForRangeStmt fields are populated correctly for both 'to' and 'until'.
    """
    src_to = """repeat for x from 1 to 10 step 2
show x
end
"""
    program = Parser(Lexer(src_to).lex()).parse()
    stmt = program.statements[0]
    assert stmt.__class__.__name__ == "RepeatForRangeStmt"
    assert stmt.var == "x"
    assert stmt.inclusive is True
    assert stmt.step is not None
    
    src_until = """repeat for y from 0 until 5
show y
end
"""
    program2 = Parser(Lexer(src_until).lex()).parse()
    stmt2 = program2.statements[0]
    assert stmt2.__class__.__name__ == "RepeatForRangeStmt"
    assert stmt2.var == "y"
    assert stmt2.inclusive is False
    assert stmt2.step is None


def test_parse_repeat_for_range_missing_tokens():
    """
    Test that parsing fails appropriately when required tokens are missing.
    """
    # Missing 'from'
    src_no_from = """repeat for i 1 to 5
show i
end
"""
    with pytest.raises(RillParseError):
        Parser(Lexer(src_no_from).lex()).parse()
    
    # Missing 'to' or 'until'
    src_no_to = """repeat for i from 1 5
show i
end
"""
    with pytest.raises(RillParseError):
        Parser(Lexer(src_no_to).lex()).parse()
    
    # Missing 'end'
    src_no_end = """repeat for i from 1 to 5
show i
"""
    with pytest.raises(RillParseError):
        Parser(Lexer(src_no_end).lex()).parse()
    
    # Missing loop variable name
    src_no_var = """repeat for from 1 to 5
show i
end
"""
    with pytest.raises(RillParseError):
        Parser(Lexer(src_no_var).lex()).parse()


def test_parse_repeat_for_range_complex_expressions():
    """
    Test that start, end, and step can be complex expressions.
    """
    src = """repeat for i from 1 + 2 to 5 * 2 step 3 - 1
    show i
end
"""
    program = Parser(Lexer(src).lex()).parse()
    stmt = program.statements[0]
    assert stmt.__class__.__name__ == "RepeatForRangeStmt"
    # Verify that start, end, and step are BinaryExpr nodes
    assert stmt.start.__class__.__name__ == "BinaryExpr"
    assert stmt.end.__class__.__name__ == "BinaryExpr"
    assert stmt.step.__class__.__name__ == "BinaryExpr"


def test_parse_repeat_for_range_nested():
    """
    Test that nested for-range loops parse correctly.
    """
    src = """repeat for i from 1 to 3
    repeat for j from 1 to 2
        show i
        show j
    end
end
"""
    program = Parser(Lexer(src).lex()).parse()
    outer = program.statements[0]
    assert outer.__class__.__name__ == "RepeatForRangeStmt"
    assert len(outer.body) == 1
    inner = outer.body[0]
    assert inner.__class__.__name__ == "RepeatForRangeStmt"
    assert len(inner.body) == 2


def test_parse_repeat_for_range_with_other_statements():
    """
    Test that for-range loops can contain various statement types.
    """
    src = """repeat for i from 1 to 5
    set x to i * 2
    if x > 5
        show "big"
    otherwise
        show "small"
    end
    change x to x + 1
end
"""
    program = Parser(Lexer(src).lex()).parse()
    stmt = program.statements[0]
    assert stmt.__class__.__name__ == "RepeatForRangeStmt"
    assert len(stmt.body) == 3
    assert stmt.body[0].__class__.__name__ == "SetStmt"
    assert stmt.body[1].__class__.__name__ == "IfStmt"
    assert stmt.body[2].__class__.__name__ == "ChangeStmt"


def test_parse_repeat_for_range_descending():
    """
    Test parsing of descending ranges with negative steps.
    """
    src = """repeat for i from 10 to 1 step -2
    show i
end
"""
    program = Parser(Lexer(src).lex()).parse()
    stmt = program.statements[0]
    assert stmt.__class__.__name__ == "RepeatForRangeStmt"
    assert stmt.var == "i"
    assert stmt.inclusive is True
    # Verify step is a unary minus expression
    assert stmt.step.__class__.__name__ == "UnaryExpr"


def test_parse_repeat_for_range_variable_names():
    """
    Test that various valid identifier names work as loop variables.
    """
    src = """repeat for counter from 1 to 3
    show counter
end
repeat for item_index from 0 until 2
    show item_index
end
"""
    program = Parser(Lexer(src).lex()).parse()
    assert program.statements[0].__class__.__name__ == "RepeatForRangeStmt"
    assert program.statements[0].var == "counter"
    assert program.statements[1].__class__.__name__ == "RepeatForRangeStmt"
    assert program.statements[1].var == "item_index"


def test_parse_repeat_all_forms_together():
    """
    Test that all three repeat forms (times, while, for-range) can coexist and parse correctly.
    """
    src = """repeat 3 times
    show "a"
end
repeat while true
    stop
end
repeat for i from 1 to 5
    show i
end
"""
    program = Parser(Lexer(src).lex()).parse()
    assert program.statements[0].__class__.__name__ == "RepeatTimesStmt"
    assert program.statements[1].__class__.__name__ == "RepeatWhileStmt"
    assert program.statements[2].__class__.__name__ == "RepeatForRangeStmt"
