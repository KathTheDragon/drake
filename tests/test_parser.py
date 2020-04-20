import pytest
import re
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from drake import parser
from drake.parser import Parser, ParseFailed
from drake.parsetree import *

ASSIGNMENT = AssignmentNode(TargetNode('', None, IdentifierNode('a')), '=', NumberNode('0'))
NUMBER_TYPE = TypeNode(IdentifierNode('Number'))

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
        p = Parser('none').leftrecurse(Parser.none, '+')
        assert p[-1] == NoneNode()
        # Test any given operator can be matched
        p = Parser('none + none').leftrecurse(Parser.none, '+', '-')
        assert p[-1] == BinaryOpNode(NoneNode(), '+', NoneNode())
        p = Parser('none - none').leftrecurse(Parser.none, '+', '-')
        assert p[-1] == BinaryOpNode(NoneNode(), '-', NoneNode())
        # Test multiple operations
        p = Parser('none + none - none').leftrecurse(Parser.none, '+', '-')
        assert p[-1] == BinaryOpNode(BinaryOpNode(NoneNode(), '+', NoneNode()), '-', NoneNode())

    def test_rightrecurse(self):
        # Test no operations
        p = Parser('none').rightrecurse(Parser.none, '+')
        assert p[-1] == NoneNode()
        # Test any given operator can be matched
        p = Parser('none + none').rightrecurse(Parser.none, '+', '-')
        assert p[-1] == BinaryOpNode(NoneNode(), '+', NoneNode())
        p = Parser('none - none').rightrecurse(Parser.none, '+', '-')
        assert p[-1] == BinaryOpNode(NoneNode(), '-', NoneNode())
        # Test multiple operations
        p = Parser('none + none - none').rightrecurse(Parser.none, '+', '-')
        assert p[-1] == BinaryOpNode(NoneNode(), '+', BinaryOpNode(NoneNode(), '-', NoneNode()))

class TestParserNodeMatching:
    def test_program(self):
        # Test single expression
        p = Parser('a=0').program()
        assert p.cursor == 3
        assert p[-1] == ModuleNode(BlockNode([ASSIGNMENT]))
        # Test multiple expressions
        p = Parser('a=0, a=0').program()
        assert p.cursor == 8
        assert p[-1] == ModuleNode(BlockNode([ASSIGNMENT]*2))
    
    def test_expression(self):
        assert Parser('a=0').expression() == Parser('a=0').assignment()
        assert Parser('do {}').expression() == Parser('do {}').keyword()
        assert Parser('() -> 0').expression() == Parser('() -> 0').lambda_()
        assert Parser('<T> a').expression() == Parser('<T> a').declaration()
        assert Parser('a or b').expression() == Parser('a or b').boolor()

    def test_assignment(self):
        # Test simple assignment
        p = Parser('a = 0').assignment()
        assert p.cursor == 5
        assert p[-1] == AssignmentNode(TargetNode('', None, IdentifierNode('a')), '=', NumberNode('0'))
        # Test augmented assignment
        p = Parser('a += 0').assignment()
        assert p.cursor == 6
        assert p[-1] == AssignmentNode(TargetNode('', None, IdentifierNode('a')), '+=', NumberNode('0'))
        # Test multiple assignment
        p = Parser('(a,b) = 0').assignment()
        assert p.cursor == 9
        assert p[-1] == AssignmentNode(
            [
                TargetNode('', None, IdentifierNode('a')),
                TargetNode('', None, IdentifierNode('b'))
            ], '=', NumberNode('0')
        )
        # Test chained assignment
        p = Parser('a = b = 0').assignment()
        assert p.cursor == 9
        assert p[-1] == AssignmentNode(
            TargetNode('', None, IdentifierNode('a')), '=',
            AssignmentNode(TargetNode('', None, IdentifierNode('b')), '=', NumberNode('0'))
        )

    def test_target(self):
        # Test bare identifier
        p = Parser('a').target()
        assert p.cursor == 1
        assert p[-1] == TargetNode('', None, IdentifierNode('a'))
        # Test mode + identifier
        p = Parser('const a').target()
        assert p.cursor == 7
        assert p[-1] == TargetNode('const', None, IdentifierNode('a'))
        # Test type + identifier
        p = Parser('<T> a').target()
        assert p.cursor == 5
        assert p[-1] == TargetNode('', TypeNode(IdentifierNode('T')), IdentifierNode('a'))
        # Test full target
        p = Parser('const <T> a').target()
        assert p.cursor == 11
        assert p[-1] == TargetNode('const', TypeNode(IdentifierNode('T')), IdentifierNode('a'))

    def test_typehint(self):
        p = Parser('<T>').typehint()
        assert p.cursor == 3
        assert p[-1] == TypeNode(IdentifierNode('T'))

    def test_type(self):
        # Test unparametrised type
        p = Parser('T').type()
        assert p.cursor == 1
        assert p[-1] == TypeNode(IdentifierNode('T'))
        # Test parametrised type
        p = Parser('T[A,B]').type()
        assert p.cursor == 6
        assert p[-1] == TypeNode(
            IdentifierNode('T'), [
                TypeNode(IdentifierNode('A')),
                TypeNode(IdentifierNode('B'))
            ]
        )

    def test_keyword(self):
        assert Parser('if a then b').keyword() == Parser('if a then b').if_()
        assert Parser('case a in {}').keyword() == Parser('case a in {}').case()
        assert Parser('try a finally b').keyword() == Parser('try a finally b').try_()
        assert Parser('for a in b {}').keyword() == Parser('for a in b {}').for_()
        assert Parser('while a {}').keyword() == Parser('while a {}').while_()
        assert Parser('iter []').keyword() == Parser('iter []').iter()
        assert Parser('do {}').keyword() == Parser('do {}').do()
        assert Parser('object {}').keyword() == Parser('object {}').object_()
        assert Parser('enum {}').keyword() == Parser('enum {}').enum()
        assert Parser('module {}').keyword() == Parser('module {}').module()
        assert Parser('exception {}').keyword() == Parser('exception {}').exception()
        assert Parser('mutable []').keyword() == Parser('mutable []').mutable()
        assert Parser('throw a').keyword() == Parser('throw a').throw()
        assert Parser('return a').keyword() == Parser('return a').return_()
        assert Parser('yield a').keyword() == Parser('yield a').yield_()
        assert Parser('yield from a').keyword() == Parser('yield from a').yieldfrom()
        assert Parser('break').keyword() == Parser('break').break_()
        assert Parser('continue').keyword() == Parser('continue').continue_()
        assert Parser('pass').keyword() == Parser('pass').pass_()

    def test_if(self):
        # Test no default
        p = Parser('if a=0 then a=0').if_()
        assert p.cursor == 15
        assert p[-1] == IfNode(ASSIGNMENT, ASSIGNMENT, None)
        # Test with default
        p = Parser('if a=0 then a=0 else a=0').if_()
        assert p.cursor == 24
        assert p[-1] == IfNode(ASSIGNMENT, ASSIGNMENT, ASSIGNMENT)

    def test_case(self):
        # Test no default
        p = Parser('case a in {}').case()
        assert p.cursor == 12
        assert p[-1] == CaseNode(IdentifierNode('a'), MappingNode([]), None)
        # Test with default
        p = Parser('case a in {} else a=0').case()
        assert p.cursor == 21
        assert p[-1] == CaseNode(IdentifierNode('a'), MappingNode([]), ASSIGNMENT)

    def test_try(self):
        # Test try-finally
        p = Parser('try a=0 finally a=0').try_()
        assert p.cursor == 19
        assert p[-1] == TryNode(ASSIGNMENT, [], ASSIGNMENT)
        # Test try-catch
        p = Parser('try a=0 catch a a=0').try_()
        assert p.cursor == 19
        assert p[-1] == TryNode(ASSIGNMENT, [CatchNode(IdentifierNode('a'), None, ASSIGNMENT)], None)
        # Test try-catch-as
        p = Parser('try a=0 catch a as b a=0').try_()
        assert p.cursor == 24
        assert p[-1] == TryNode(ASSIGNMENT, [CatchNode(IdentifierNode('a'), IdentifierNode('b'), ASSIGNMENT)], None)
        # Test try-catch-finally
        p = Parser('try a=0 catch a a=0 finally a=0').try_()
        assert p.cursor == 31
        assert p[-1] == TryNode(ASSIGNMENT, [CatchNode(IdentifierNode('a'), None, ASSIGNMENT)], ASSIGNMENT)

    def test_for(self):
        # Test single loop variable
        p = Parser('for a in a=0 {}').for_()
        assert p.cursor == 15
        assert p[-1] == ForNode(IdentifierNode('a'), ASSIGNMENT, BlockNode([]))
        # Test multiple loop variables
        p = Parser('for (a,b) in a=0 {}').for_()
        assert p.cursor == 19
        assert p[-1] == ForNode([IdentifierNode('a'), IdentifierNode('b')], ASSIGNMENT, BlockNode([]))

    def test_while(self):
        p = Parser('while a=0 {}').while_()
        assert p.cursor == 12
        assert p[-1] == WhileNode(ASSIGNMENT, BlockNode([]))

    def test_iter(self):
        # Test iter-for
        p = Parser('iter for a in a=0 {}').iter()
        assert p.cursor == 20
        assert p[-1] == IterNode(ForNode(IdentifierNode('a'), ASSIGNMENT, BlockNode([])))
        # Test iter-while
        p = Parser('iter while a=0 {}').iter()
        assert p.cursor == 17
        assert p[-1] == IterNode(WhileNode(ASSIGNMENT, BlockNode([])))
        # Test iter-list
        p = Parser('iter []').iter()
        assert p.cursor == 7
        assert p[-1] == IterNode(ListNode([]))

    def test_do(self):
        p = Parser('do {}').do()
        assert p.cursor == 5
        assert p[-1] == DoNode(BlockNode([]))

    def test_object(self):
        p = Parser('object {}').object_()
        assert p.cursor == 9
        assert p[-1] == ObjectNode(BlockNode([]))

    def test_enum(self):
        # Test non-flag enum
        p = Parser('enum {}').enum()
        assert p.cursor == 7
        assert p[-1] == EnumNode(False, [])
        # Test flag enum
        p = Parser('enum flags {}').enum()
        assert p.cursor == 13
        assert p[-1] == EnumNode(True, [])

    def test_enumitem(self):
        # Test implicit value
        p = Parser('a').enumitem()
        assert p.cursor == 1
        assert p[-1] == PairNode(IdentifierNode('a'), None)
        # Test explicit value
        p = Parser('a = 0').enumitem()
        assert p.cursor == 5
        assert p[-1] == PairNode(IdentifierNode('a'), NumberNode('0'))

    def test_module(self):
        p = Parser('module {}').module()
        assert p.cursor == 9
        assert p[-1] == ModuleNode(BlockNode([]))

    def test_exception(self):
        p = Parser('exception {}').exception()
        assert p.cursor == 12
        assert p[-1] == ExceptionNode(BlockNode([]))

    def test_mutable(self):
        # Test mutable object
        p = Parser('mutable object {}').mutable()
        assert p.cursor == 17
        assert p[-1] == MutableNode(ObjectNode(BlockNode([])))
        # Test mutable mapping
        p = Parser('mutable {}').mutable()
        assert p.cursor == 10
        assert p[-1] == MutableNode(MappingNode([]))
        # Test mutable list
        p = Parser('mutable []').mutable()
        assert p.cursor == 10
        assert p[-1] == MutableNode(ListNode([]))
        # Test mutable tuple
        p = Parser('mutable ()').mutable()
        assert p.cursor == 10
        assert p[-1] == MutableNode(TupleNode([]))
        # Test mutable string
        p = Parser('mutable ""').mutable()
        assert p.cursor == 10
        assert p[-1] == MutableNode(StringNode('""'))

    def test_throw(self):
        p = Parser('throw a=0').throw()
        assert p.cursor == 9
        assert p[-1] == ThrowNode(ASSIGNMENT)

    def test_return(self):
        p = Parser('return a=0').return_()
        assert p.cursor == 10
        assert p[-1] == ReturnNode(ASSIGNMENT)

    def test_yield(self):
        p = Parser('yield a=0').yield_()
        assert p.cursor == 9
        assert p[-1] == YieldNode(ASSIGNMENT)

    def test_yieldfrom(self):
        p = Parser('yield from a=0').yieldfrom()
        assert p.cursor == 14
        assert p[-1] == YieldFromNode(ASSIGNMENT)

    def test_break(self):
        p = Parser('break').break_()
        assert p.cursor == 5
        assert p[-1] == BreakNode()

    def test_continue(self):
        p = Parser('continue').continue_()
        assert p.cursor == 8
        assert p[-1] == ContinueNode()

    def test_pass(self):
        p = Parser('pass').pass_()
        assert p.cursor == 4
        assert p[-1] == PassNode()

    def test_lambda(self):
        # Test delimited params
        p = Parser('(<Number> a, <Number> b) -> a=0').lambda_()
        assert p[-1] == LambdaNode(
            [
                DeclarationNode(False, NUMBER_TYPE, IdentifierNode('a')),
                DeclarationNode(False, NUMBER_TYPE, IdentifierNode('b'))
            ],
            ASSIGNMENT
        )
        # Test non-delimited param
        p = Parser('<Number> a -> a=0').lambda_()
        assert p[-1] == LambdaNode(
            [DeclarationNode(False, NUMBER_TYPE, IdentifierNode('a'))],
            ASSIGNMENT
        )

    def test_param(self):
        # Test starred parameter
        p = Parser('*<Number> a').param()
        assert p[-1] == UnaryOpNode(
            '*',
            DeclarationNode(
                False,
                TypeNode(IdentifierNode('Number')),
                IdentifierNode('a')
            )
        )
        # Test keyword parameter
        p = Parser('<Number> a=0').param()
        assert p[-1] == PairNode(
            DeclarationNode(
                False,
                TypeNode(IdentifierNode('Number')),
                IdentifierNode('a')
            ),
            NumberNode('0')
        )
        # Test declaration parameter
        p = Parser('<Number> a').param()
        assert p[-1] == DeclarationNode(
            False,
            TypeNode(IdentifierNode('Number')),
            IdentifierNode('a')
        )

    def test_declaration(self):
        p = Parser('const <Number> a').declaration()
        assert p[-1] == DeclarationNode(
            True,
            TypeNode(IdentifierNode('Number')),
            IdentifierNode('a')
        )

    def test_boolor(self):
        # Test recursion
        p = Parser('a or b or c').boolor()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            'or',
            BinaryOpNode(IdentifierNode('b'), 'or', IdentifierNode('c'))
        )
        # Test precedence
        p = Parser('a xor b or c').boolor()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), 'xor', IdentifierNode('b')),
            'or',
            IdentifierNode('c')
        )

    def test_boolxor(self):
        # Test recursion
        p = Parser('a xor b xor c').boolxor()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            'xor',
            BinaryOpNode(IdentifierNode('b'), 'xor', IdentifierNode('c'))
        )
        # Test precedence
        p = Parser('a and b xor c').boolxor()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), 'and', IdentifierNode('b')),
            'xor',
            IdentifierNode('c')
        )

    def test_booland(self):
        # Test recursion
        p = Parser('a and b and c').booland()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            'and',
            BinaryOpNode(IdentifierNode('b'), 'and', IdentifierNode('c'))
        )
        # Test precedence
        p = Parser('a in b and c').booland()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), 'in', IdentifierNode('b')),
            'and',
            IdentifierNode('c')
        )

    def test_inclusion(self):
        # Test recursion
        p = Parser('a in b in c').inclusion()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            'in',
            BinaryOpNode(IdentifierNode('b'), 'in', IdentifierNode('c'))
        )
        # Test precedence
        p = Parser('a is b in c').inclusion()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), 'is', IdentifierNode('b')),
            'in',
            IdentifierNode('c')
        )

    def test_identity(self):
        # Test recursion
        p = Parser('a is b is c').identity()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            'is',
            BinaryOpNode(IdentifierNode('b'), 'is', IdentifierNode('c'))
        )
        # Test precedence
        p = Parser('a < b is c').identity()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '<', IdentifierNode('b')),
            'is',
            IdentifierNode('c')
        )

    def test_comparison(self):
        # Test recursion
        p = Parser('a < b < c').comparison()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '<',
            BinaryOpNode(IdentifierNode('b'), '<', IdentifierNode('c'))
        )
        # Test precedence
        p = Parser('a | b < c').comparison()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '|', IdentifierNode('b')),
            '<',
            IdentifierNode('c')
        )

    def test_bitor(self):
        # Test recursion
        p = Parser('a | b | c').bitor()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '|', IdentifierNode('b')),
            '|',
            IdentifierNode('c')
        )
        # Test precedence
        p = Parser('a | b ^ c').bitor()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '|',
            BinaryOpNode(IdentifierNode('b'), '^', IdentifierNode('c'))
        )

    def test_bitxor(self):
        # Test recursion
        p = Parser('a ^ b ^ c').bitxor()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '^', IdentifierNode('b')),
            '^',
            IdentifierNode('c')
        )
        # Test precedence
        p = Parser('a ^ b & c').bitxor()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '^',
            BinaryOpNode(IdentifierNode('b'), '&', IdentifierNode('c'))
        )

    def test_bitand(self):
        # Test recursion
        p = Parser('a & b & c').bitand()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '&', IdentifierNode('b')),
            '&',
            IdentifierNode('c')
        )
        # Test precedence
        p = Parser('a & b << c').bitand()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '&',
            BinaryOpNode(IdentifierNode('b'), '<<', IdentifierNode('c'))
        )

    def test_shift(self):
        # Test recursion
        p = Parser('a << b << c').shift()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '<<', IdentifierNode('b')),
            '<<',
            IdentifierNode('c')
        )
        # Test precedence
        p = Parser('a << b + c').shift()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '<<',
            BinaryOpNode(IdentifierNode('b'), '+', IdentifierNode('c'))
        )

    def test_addition(self):
        # Test recursion
        p = Parser('a + b + c').addition()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '+', IdentifierNode('b')),
            '+',
            IdentifierNode('c')
        )
        # Test precedence
        p = Parser('a + b * c').addition()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '+',
            BinaryOpNode(IdentifierNode('b'), '*', IdentifierNode('c'))
        )

    def test_product(self):
        # Test recursion
        p = Parser('a * b * c').product()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '*', IdentifierNode('b')),
            '*',
            IdentifierNode('c')
        )
        # Test precedence
        p = Parser('a * b % c').product()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '*',
            BinaryOpNode(IdentifierNode('b'), '%', IdentifierNode('c'))
        )

    def test_modulus(self):
        # Test recursion
        p = Parser('a % b % c').modulus()
        assert p[-1] == BinaryOpNode(
            BinaryOpNode(IdentifierNode('a'), '%', IdentifierNode('b')),
            '%',
            IdentifierNode('c')
        )
        # Test precedence
        p = Parser('a % b ** c').modulus()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '%',
            BinaryOpNode(IdentifierNode('b'), '**', IdentifierNode('c'))
        )

    def test_exponent(self):
        # Test recursion
        p = Parser('a ** b ** c').exponent()
        assert p[-1] == BinaryOpNode(
            IdentifierNode('a'),
            '**',
            BinaryOpNode(IdentifierNode('b'), '**', IdentifierNode('c'))
        )
        # Test precedence
        p = Parser('-a ** b').exponent()
        assert p[-1] == BinaryOpNode(
            UnaryOpNode('-', IdentifierNode('a')),
            '**',
            IdentifierNode('b')
        )

    def test_unary(self):
        p = Parser('- ! a.b').unary()
        assert p[-1] == UnaryOpNode(
            '-',
            UnaryOpNode(
                '!',
                LookupNode(IdentifierNode('a'), IdentifierNode('b'))
            )
        )

    def test_primary(self):
        p = Parser('a.b(c)[d]').primary()
        assert p[-1] == SubscriptNode(
            CallNode(
                LookupNode(IdentifierNode('a'), IdentifierNode('b')),
                [IdentifierNode('c')]
            ),
            ListNode([IdentifierNode('d')])
        )
        # Test range subscript
        p = Parser('a[b..]').primary()
        assert p[-1] == SubscriptNode(
            IdentifierNode('a'),
            RangeNode(IdentifierNode('b'))
        )

    def test_arg(self):
        # Test starred argument
        p = Parser('*nonlocal a=0').arg()
        assert p[-1] == UnaryOpNode(
            '*',
            AssignmentNode(
                TargetNode('nonlocal', None, IdentifierNode('a')),
                '=',
                NumberNode('0')
            )
        )
        # Test keyword argument
        p = Parser('a=0').arg()
        assert p[-1] == PairNode(IdentifierNode('a'), NumberNode('0'))
        # Test expression
        p = Parser('0').arg()
        assert p[-1] == NumberNode('0')

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
        assert p[-1] == Parser('0..').range()[-1]
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
