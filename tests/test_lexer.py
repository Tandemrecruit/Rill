import pytest

from rill.lexer import Lexer
from rill.token import TokenType

def types(src: str):
    return [t.type for t in Lexer(src).lex()]

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
    # ensure comment didn't create tokens
    assert all("#" not in t.lexeme for t in ts)

def test_modulo_token():
    src = "set r to 7 % 2\n"
    ts = Lexer(src).lex()
    assert TokenType.PERCENT in [t.type for t in ts]

def test_unterminated_string_raises():
    with pytest.raises(Exception):
        Lexer("set a to \"oops\n").lex()
