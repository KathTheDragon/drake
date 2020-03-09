import pytest
import re
import sys
from drake.drake import parser2 as parser
from drake.drake.parser2 import Parser, ParseFailed
from drake.drake.parsetree2 import *

ASSIGNMENT = Parser('a=0').assignment()[-1]

def test_Parser__with():
    p = Parser('test string', 3, 0, 3, ('test',))
    # Test that missing arguments have no effect
    assert p._with() == p
    # Test that supplying arguments overwrites existing attributes, except .source
    p = p._with(cursor=5, linenum=2, column=0, parsed=())
    assert p.source == 'test string'
    assert p.cursor == 5
    assert p.linenum == 2
    assert p.column == 0
    assert p.parsed == ()

def test_Parser_addparsed():
    p = Parser('test string', parsed=('test',))
    # Test that .parsed gets extended
    assert p.addparsed('a', 'b', 'c').parsed == ('test', 'a', 'b', 'c')

def test_Parser_popparsed():
    p = Parser('test string', parsed=('test', 'a'))
    # Test that the last item in .parsed is removed and returned
    p, item = p.popparsed()
    assert p.parsed == ('test',)
    assert item == 'a'

def test_Parser_withnode():
    p = Parser('test string', parsed=('test', 'a'))
    class TestClass:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
    # Test that the args are applied in order, before arguments taken from .parsed
    p, item = p.withnode(TestClass, 1, 2, fromparsed=2, test=3).popparsed()
    assert item.args == (1, 2, 'test', 'a')
    assert item.kwargs == {'test': 3}
    assert p.parsed == ()

def test_Parser_raw_match():
    p = Parser('test string')
    # Test that an invalid match raises ParseFailed
    with pytest.raises(ParseFailed):
        p.raw_match(parser.DECIMAL, 'decimal')
    # Test that parse=False does not add the match to .parsed
    assert p.raw_match(parser.IDENTIFIER, 'identifier').parsed == ()
    # Test that parse=True does add the match to .parsed
    p = p.raw_match(parser.IDENTIFIER, 'identifier', parse=True)
    assert p.parsed == ('test',)
    # Test that the cursor and column have been advanced correctly
    assert p.cursor == p.column == 4

def test_Parser_skip():
    assert Parser('   // comment').skip().cursor == 13
    assert Parser('   test   // comment').skip().cursor == 3

def test_Parser_match():
    p = Parser('test string')
    # Test that match accepts strings or patterns
    p1 = p.match('test')
    p2 = p.match(parser.IDENTIFIER)
    # Test that match also skips whitespace
    assert p1.cursor == p2.cursor == 5
    # Test that an invalid match raises ParseFailed
    with pytest.raises(ParseFailed):
        p.match('foo')
    # Test that parse=False does not add the match to .parsed
    assert p.match(parser.IDENTIFIER, 'identifier').parsed == ()
    # Test that parse=True does add the match to .parsed
    assert p.match(parser.IDENTIFIER, 'identifier', parse=True).parsed == ('test',)

def test_Parser_newline():
    # Test that \n, \r\n, and \r are all treated as newlines
    p = Parser('\n').newline()
    assert p.cursor == 1
    assert p.linenum == 1
    assert p.column == 0
    p = Parser('\r').newline()
    assert p.cursor == 1
    assert p.linenum == 1
    assert p.column == 0
    p = Parser('\r\n').newline()
    assert p.cursor == 2
    assert p.linenum == 1
    assert p.column == 0
    # Test that following whitespace is skipped
    p = Parser('\n   ').newline()
    assert p.cursor == 4
    assert p.column == 3
    # Test that following blank lines are skipped
    p = Parser('\n \n a').newline()
    assert p.cursor == 4
    assert p.linenum == 2
    assert p.column == 1

def test_Parser_choices():
    # Test no positional arguments raises Value Error
    with pytest.raises(ValueError):
        Parser('').choices()
    # Test any positional argument can be matched
    Parser('ab').choices('a', 'b')
    Parser('ba').choices('a', 'b')
    # Test that a tuple of (pattern, text) can be given
    Parser('test string').choices((parser.IDENTIFIER, 'identifier'))
    # Test that giving parse=False does not add to .parsed
    assert Parser('a').choices('a').parsed == ()
    # Test that giving parse=True does add to .parsed
    assert Parser('a').choices('a', parse=True).parsed == ('a',)
    # Test that if no positional argument is matched, ParseFailed is raised
    with pytest.raises(ParseFailed):
        Parser('c').choices('a', 'b')

def test_Parser_literal():
    # Test string
    assert Parser("'test'").literal()[-1] == StringNode("'test'")
    # Test number
    assert Parser('0').literal()[-1] == NumberNode('0')
    # Test boolean
    assert Parser('false').literal()[-1] == BooleanNode('false')
    # Test none
    assert Parser('none').literal()[-1] == NoneNode()
    # Test non-literal
    with pytest.raises(ParseFailed):
        Parser('test').literal()

def test_Parser_string():
    # Test single quotes
    p = Parser("'test string'").string()
    assert p.cursor == 13
    assert p[-1] == StringNode("'test string'")
    # Test double quotes
    p = Parser('"test string"').string()
    assert p.cursor == 13
    assert p[-1] == StringNode('"test string"')
    # Test non-string
    with pytest.raises(ParseFailed):
        Parser('test').string()

def test_Parser_number():
    # Test decimal
    p = Parser('0_12.34_5e7_89j').number()
    assert p.cursor == 15
    assert p[-1] == NumberNode('0_12.34_5e7_89j')
    # Test case-insensitivity
    assert Parser('1E2J').number()[-1] == NumberNode('1E2J')
    # Test binary
    assert Parser('0b_10').number()[-1] == NumberNode('0b_10')
    # with pytest.raises(ParseFailed):
    #     Parser('0b2').number()[-1]
    # Test octal
    assert Parser('0o1_7').number()[-1] == NumberNode('0o1_7')
    # with pytest.raises(ParseFailed):
    #     Parser('0o8').number()[-1]
    # Test hex
    assert Parser('0x3f').number()[-1] == NumberNode('0x3f')
    # with pytest.raises(ParseFailed):
    #     Parser('0xg').number()
    # Test non-number
    with pytest.raises(ParseFailed):
        Parser('_0').number()

def test_Parser_boolean():
    p = Parser('true').boolean()
    assert p.cursor == 4
    assert p[-1] == BooleanNode('true')
    # Test non-bool
    with pytest.raises(ParseFailed):
        Parser('ture').boolean()

def test_Parser_none():
    p = Parser('none').none()
    assert p.cursor == 4
    assert p[-1] == NoneNode()
    # Test non-none
    with pytest.raises(ParseFailed):
        Parser('non').none()

def test_Parser_identifier():
    p = Parser('_test2?').identifier()
    assert p.cursor == 7
    assert p[-1] == IdentifierNode('_test2?')
    # Test reserved words don't parse
    with pytest.raises(ParseFailed):
        Parser('true').identifier()
