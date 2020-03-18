import pytest
import re
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from drake import parser
from drake.parser import Parser, ParseFailed
from drake.parsetree import *

ASSIGNMENT = AssignmentNode(TargetNode('', None, IdentifierNode('a')), '=', NumberNode('0'))

class TestParserAttributes:
    def test_location(self):
        p = Parser('\n\n\n01234567', cursor=9)
        assert p.location == (4, 7)

    def test_getitem(self):
        p = Parser('', parsed=('a', 'b', 'c', 'd'))
        assert p[0] == 'a'
        assert p[3] == p[-1] == 'd'
        assert p[1:3] == ('b', 'c')

class TestParserInternal:
    def test__with(self):
        p = Parser('test string', 3, ('test',))
        # Test that missing arguments have no effect
        assert p._with() == p
        # Test that supplying arguments overwrites existing attributes, except .source
        p = p._with(cursor=5, parsed=())
        assert p.source == 'test string'
        assert p.cursor == 5
        assert p.parsed == ()

    def test_addparsed(self):
        p = Parser('test string', parsed=('test',))
        # Test that .parsed gets extended
        assert p.addparsed('a', 'b', 'c').parsed == ('test', 'a', 'b', 'c')

    def test_withnode(self):
        p = Parser('test string', parsed=('test', 'a'))
        class TestClass:
            def __init__(self, *args):
                self.args = args
        # Test that the args are removed from .parsed in order
        p = p.withnode(TestClass, args=2)
        item = p[-1]
        assert item.args == ('test', 'a')
        assert p.parsed == (item,)

class TestParserBasicMatching:
    def test_raw_match(self):
        p = Parser('test string')
        # Test that an invalid match raises ParseFailed
        with pytest.raises(ParseFailed):
            p.raw_match(parser.DECIMAL, 'decimal')
        # Test that parse=False does not add the match to .parsed
        assert p.raw_match(parser.IDENTIFIER, 'identifier').parsed == ()
        # Test that parse=True does add the match to .parsed
        p = p.raw_match(parser.IDENTIFIER, 'identifier', parse=True)
        assert p.parsed == ('test',)
        # Test that the cursor has been advanced correctly
        assert p.cursor == 4

    def test_skip(self):
        assert Parser('   // comment').skip().cursor == 13
        assert Parser('   test   // comment').skip().cursor == 3

    def test_match(self):
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

    def test_newline(self):
        # Test that \n, \r\n, and \r are all treated as newlines
        p = Parser('\n').newline()
        assert p.cursor == 1
        assert p.location == (2, 1)
        p = Parser('\r').newline()
        assert p.cursor == 1
        assert p.location == (2, 1)
        p = Parser('\r\n').newline()
        assert p.cursor == 2
        assert p.location == (2, 1)
        # Test that following whitespace is skipped
        p = Parser('\n   ').newline()
        assert p.cursor == 4
        assert p.location == (2, 4)
        # Test that following blank lines are skipped
        p = Parser('\n \n a').newline()
        assert p.cursor == 4
        assert p.location == (3, 2)

    def test_choices(self):
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

class TestParserGenericMatching:
    def test_nodelist(self):
        # Test single item
        assert Parser('none').nodelist(Parser.none)[-1] == [NoneNode()]
        assert Parser('none,').nodelist(Parser.none)[-1] == [NoneNode()]
        # Test multiple items
        assert Parser('none\nnone').nodelist(Parser.none)[-1] == [NoneNode()]*2
        assert Parser('none,none').nodelist(Parser.none)[-1] == [NoneNode()]*2
        assert Parser('none,none,').nodelist(Parser.none)[-1] == [NoneNode()]*2
        assert Parser('none,\nnone').nodelist(Parser.none)[-1] == [NoneNode()]*2
        assert Parser('none,\nnone,').nodelist(Parser.none)[-1] == [NoneNode()]*2
        # Test optional leading and trailing newlines
        assert Parser('\nnone\n').nodelist(Parser.none)[-1] == [NoneNode()]

    def test_delimitedlist(self):
        # Test delimited multiple items
        p = Parser('(none, none, none)').delimitedlist(Parser.none)
        assert p[-1] == [NoneNode()]*3
        # Test delimited single item
        p = Parser('(none)').delimitedlist(Parser.none)
        assert p[-1] == [NoneNode()]
        # Test non-delimited item forced to list
        p = Parser('none').delimitedlist(Parser.none, True)
        assert p[-1] == [NoneNode()]
        # Test non-delimited item
        p = Parser('none').delimitedlist(Parser.none)
        assert p[-1] == NoneNode()

    def test_leftrecurse(self):
        # Test no operations
        p = Parser('none').leftrecurse(('+',), Parser.none)
        assert p[-1] == NoneNode()
        # Test any given operator can be matched
        p = Parser('none + none').leftrecurse(('+', '-'), Parser.none)
        assert p[-1] == BinaryOpNode(NoneNode(), '+', NoneNode())
        p = Parser('none - none').leftrecurse(('+', '-'), Parser.none)
        assert p[-1] == BinaryOpNode(NoneNode(), '-', NoneNode())
        # Test multiple operations
        p = Parser('none + none - none').leftrecurse(('+', '-'), Parser.none)
        assert p[-1] == BinaryOpNode(BinaryOpNode(NoneNode(), '+', NoneNode()), '-', NoneNode())

    def test_rightrecurse(self):
        # Test no operations
        p = Parser('none').rightrecurse(('+',), Parser.none)
        assert p[-1] == NoneNode()
        # Test any given operator can be matched
        p = Parser('none + none').rightrecurse(('+', '-'), Parser.none)
        assert p[-1] == BinaryOpNode(NoneNode(), '+', NoneNode())
        p = Parser('none - none').rightrecurse(('+', '-'), Parser.none)
        assert p[-1] == BinaryOpNode(NoneNode(), '-', NoneNode())
        # Test multiple operations
        p = Parser('none + none - none').rightrecurse(('+', '-'), Parser.none)
        assert p[-1] == BinaryOpNode(NoneNode(), '+', BinaryOpNode(NoneNode(), '-', NoneNode()))

class TestParserNodeMatching:
    def test_atom(self):
        # Test mapping
        assert Parser('{0:0}').atom() == Parser('{0:0}').mapping()
        # Test block
        assert Parser('{0}').atom() == Parser('{0}').block()
        # Test list
        assert Parser('[0]').atom() == Parser('[0]').list()
        # Test grouping
        assert Parser('(0)').atom() == Parser('(0)').grouping()
        # Test tuple
        assert Parser('(0,)').atom() == Parser('(0,)').tuple()
        # Test literal
        assert Parser('0').atom() == Parser('0').literal()
        # Test identifier
        assert Parser('t').atom() == Parser('t').identifier()

    def test_mapping(self):
        p = Parser('{0:0, 0:0}').mapping()
        assert p.cursor == 10
        assert p[-1] == MappingNode([Parser('0:0').pair()[-1]]*2)

    def test_pair(self):
        p = Parser('a=0:a=0').pair()
        assert p.cursor == 7
        assert p[-1] == PairNode(ASSIGNMENT, ASSIGNMENT)

    def test_block(self):
        p = Parser('{a=0,a=0}').block()
        assert p.cursor == 9
        assert p[-1] == BlockNode([ASSIGNMENT]*2)

    def test_list(self):
        # range
        p = Parser('[0..]').list()
        assert p.cursor == 5
        assert p[-1] == ListNode(Parser('0..').range()[-1])
        # list
        p = Parser('[a=0,a=0]').list()
        assert p.cursor == 9
        assert p[-1] == ListNode([ASSIGNMENT]*2)

    def test_range(self):
        # start, end, step
        p = Parser('none..none, none').range()
        assert p.cursor == 16
        assert p[-1] == RangeNode(NoneNode(), NoneNode(), NoneNode())
        # start, end
        p = Parser('none..none').range()
        assert p.cursor == 10
        assert p[-1] == RangeNode(NoneNode(), NoneNode())
        # start, step
        p = Parser('none.., none').range()
        assert p.cursor == 12
        assert p[-1] == RangeNode(NoneNode(), step=NoneNode())
        # start
        p = Parser('none..').range()
        assert p.cursor == 6
        assert p[-1] == RangeNode(NoneNode())

    def test_grouping(self):
        p = Parser('(a=0)').grouping()
        assert p.cursor == 5
        assert p[-1] == ASSIGNMENT

    def test_tuple(self):
        p = Parser('(a=0, a=0)').tuple()
        assert p.cursor == 10
        assert p[-1] == TupleNode([ASSIGNMENT]*2)
        # Test that a syntactic grouping is also valid - this is dealt with by attempting to parse a grouping *first*
        p = Parser('(a=0)').tuple()
        assert p.cursor == 5
        assert p[-1] == TupleNode([ASSIGNMENT])

    def test_literal(self):
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

    def test_string(self):
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

    def test_number(self):
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

    def test_boolean(self):
        p = Parser('true').boolean()
        assert p.cursor == 4
        assert p[-1] == BooleanNode('true')
        # Test non-bool
        with pytest.raises(ParseFailed):
            Parser('ture').boolean()

    def test_none(self):
        p = Parser('none').none()
        assert p.cursor == 4
        assert p[-1] == NoneNode()
        # Test non-none
        with pytest.raises(ParseFailed):
            Parser('non').none()

    def test_identifier(self):
        p = Parser('_test2?').identifier()
        assert p.cursor == 7
        assert p[-1] == IdentifierNode('_test2?')
        # Test reserved words don't parse
        with pytest.raises(ParseFailed):
            Parser('true').identifier()
