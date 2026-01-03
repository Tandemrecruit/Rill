from rill.lexer import Lexer
from rill.parser import Parser
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
