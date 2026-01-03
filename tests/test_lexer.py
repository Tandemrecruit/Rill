import pytest

from rill.lexer import Lexer
from rill.token import TokenType


def test_keywords_and_identifiers():
    src = "set total to 0\nchange total to total + 1\n"
    ts = Lexer(src).lex()

    assert ts[0].type == TokenType.SET
    assert ts[1].type == TokenType.IDENT
    assert ts[2].type == TokenType.TO
    assert ts[3].type == TokenType.NUMBER
    assert TokenType.NEWLINE in [t.type for t in ts]


def test_numbers_int_and_float():
    src = "set a to 12\nset b to 3.14\n"
    ts = Lexer(src).lex()
    nums = [t for t in ts if t.type == TokenType.NUMBER]
    assert nums[0].literal == 12
    assert nums[1].literal == 3.14


def test_strings_single_and_double():
    src = "set a to \"It\\'s ok\"\nset b to 'She said \"hello\"'\n"
    ts = Lexer(src).lex()
    strs = [t for t in ts if t.type == TokenType.STRING]
    assert strs[0].literal == "It's ok"
    assert strs[1].literal == 'She said "hello"'


def test_inline_comment():
    src = "set x to 10  # comment\nshow x\n"
    ts = Lexer(src).lex()
    assert TokenType.EOF in [t.type for t in ts]
    assert all("#" not in t.lexeme for t in ts)


def test_modulo_token():
    src = "set r to 7 % 2\n"
    ts = Lexer(src).lex()
    assert TokenType.PERCENT in [t.type for t in ts]


def test_crlf_newlines():
    src = "set x to 1\r\nshow x\r\n"
    ts = Lexer(src).lex()
    newlines = [t for t in ts if t.type == TokenType.NEWLINE]
    assert len(newlines) == 2
    assert newlines[0].lexeme == "\r\n"
    # "show" should start on line 2, col 1
    show_tok = next(t for t in ts if t.type == TokenType.SHOW)
    assert show_tok.line == 2
    assert show_tok.col == 1


def test_token_lexeme_matches_source_slice():
    src = "set s to \"She said \\\"hello\\\"\"\n"
    ts = Lexer(src).lex()
    for t in ts:
        assert t.lexeme == src[t.start_index : t.end_index]


def test_unterminated_string_raises():
    with pytest.raises(Exception):
        Lexer("set a to \"oops\n").lex()


def test_while_and_times_keywords():
    src = "repeat 3 times\nrepeat while true\n"
    ts = Lexer(src).lex()
    types = [t.type for t in ts]
    assert TokenType.REPEAT in types
    assert TokenType.TIMES in types
    assert TokenType.WHILE in types
