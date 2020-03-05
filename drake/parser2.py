import contextlib, re
from dataclasses import dataclass, field
from typing import Any
from .parsetree2 import *

## Tokens
WHITESPACE = re.compile(r'[^\S\r\n]*')
COMMENT = re.compile('//.*$')
NEWLINE = re.compile(r'\r\n?|\n')
EOF = re.compile(r'$(?![\r\n])')
IDENTIFIER = re.compile(r'[a-zA-Z_]\w*[!?]?')
_STRING = r'(?:[^\\\n]|\\.)*?'
STRING = re.compile(fr'\'{_STRING}\'|\"{_STRING}\"')
NUMBER = re.compile(r'(?:0|[1-9]\d*)(?:\.\d*[1-9])?j?')

AUGMENTED_ASSIGNMENT = '|= ^= &= <<= >>= += -= *= /= %= **='.split()

## Exceptions
class ParseFailed(Exception):
    'Exception to signify a parse attempt failed and backtracking should occur'

class InvalidSyntax(Exception):
    def __init__(self, error, parser):
        linenum, column = parser.linenum, parser.column
        self.message = f'{error} @ {linenum}:{column}'
        self.linenum = linenum
        self.column = column

    def __str__(self):
        return self.message

def Expected(expected, parser):
    error = f'expected {expected}, got {parser.source[parser.cursor]}'
    return InvalidSyntax(error, parser)

## Context managers
OPTIONAL = contextlib.suppress(InvalidSyntax)

## Classes
@dataclass
class Parser:
    source: str
    cursor: int = 0
    linenum: int = 0
    column: int = 0
    parsed: tuple = ()

    def __iter__(parser):
        yield parser
        yield from parser.parsed

    def _with(parser, cursor=None, linenum=None, column=None, parsed=None):
        if cursor is None:
            cursor = parser.cursor
        if linenum is None:
            linenum = parser.linenum
        if column is None:
            column = parser.column
        if parsed is None:
            parsed = parser.parsed
        return Parser(parser.source, cursor, linenum, column, parsed)

    def addparsed(parser, *parsed):
        return parser._with(parsed=parser.parsed+parsed)

    def popparsed(parser):
        return parser._with(parsed=parser.parsed[:-1]), parser.parsed[-1]

    def withnode(parser, nodeclass, *args, fromparsed=None, **kwargs):
        parsed = parser.parsed
        if fromparsed is not None:
            parsed, args = parsed[:-fromparsed], args+parsed[-fromparsed:]
        return parser.addparsed(nodeclass(*args, **kwargs))

    # Basic matching methods
    def raw_match(parser, pattern, text, parse=False):
        match = pattern.match(parser.source, parser.cursor)
        if match is None:
            raise Expected(text, parser)
        cursor = match.end()
        column = parser.column + (cursor - parser.cursor)
        parser = parser._with(cursor=cursor, column=column)
        if parse:
            return parser.addparsed(match.group())
        else:
            return parser

    def skip(parser):
        with OPTIONAL:
            parser = parser.raw_match(WHITESPACE, 'whitespace')
        with OPTIONAL:
            parser = parser.raw_match(COMMENT, 'comment')
        return parser

    def match(parser, pattern, text='', parse=False):
        if isinstance(pattern, str):
            text = text or pattern
            pattern = re.compile(re.escape(pattern))
        return parser.raw_match(pattern, text, parse).skip()

    def newline(parser):
        parser = parser.raw_match(NEWLINE, 'newline')._with(linenum=parser.linenum+1, column=0).skip()
        with OPTIONAL:
            parser = parser.newline()
        return parser

    def choices(parser, *tokens, parse=False):
        exception = ValueError('items cannot be empty')
        for token in tokens:
            try:
                return parser.match(token, parse=parse)
            except InvalidSyntax as e:
                exception = e
        raise exception

    # Generic matching methods
    def nodelist(parser, item):
        with OPTIONAL:
            parser = parser.newline()
        parser = item(parser)
        num = 1
        try:
            try:
                while True:
                    parser = item(parser.newline())
                    num += 1
            except InvalidSyntax:
                if num == 1:
                    raise
        except InvalidSyntax:
            with OPTIONAL:
                while True:
                    _parser = parser.match(',')
                    with OPTIONAL:
                        _parser = _parser.newline()
                    parser = item(_parser)
                    num += 1
            with OPTIONAL:
                parser = parser.match(',')
        with OPTIONAL:
            parser = parser.newline()
        def List(*args):
            return list(args)
        return parser.withnode(List, fromparsed=num)

    def leftrecurse(parser, operators, operand):
        parser = operand(parser)
        with OPTIONAL:
            while True:
                parser = operand(parser.choices(*operators, parse=True)) \
                        .withnode(BinaryOpNode, fromparsed=3)
        return parser

    def rightrecurse(parser, operators, operand):
        parser = operand(parser)
        with OPTIONAL:
            parser = parser.choices(*operators, parse=True) \
                           .rightrecurse(operators, operand) \
                           .withnode(BinaryOpNode, fromparsed=3)
        return parser

    # Node matching methods
    def program(parser):
        return parser.nodelist(Parser.assignment) \
                     .raw_match(EOF, 'eof') \
                     .withnode(BlockNode, fromparsed=1)

    def assignment(parser):
        try:
            try:
                _parser = parser.match('(').nodelist(Parser.target).match(')')
            except InvalidSyntax:
                _parser = parser.target()
            return _parser.match('=').assignment() \
                          .withnode(AssignmentNode, fromparsed=2)
        except InvalidSyntax:
            try:
                # There must be a better way
                _parser, target = parser.target().popparsed()
                _parser = _parser.choices(*AUGMENTED_ASSIGNMENT, parse=True).assignment() \
                                 .withnode(BinaryOpNode, target, fromparsed=2)
                return _parser.withnode(AssignmentNode, target, fromparsed=1)
            except InvalidSyntax:
                return parser.declaration()

    def declaration(parser):
        try:
            return parser.typehint().identifier() \
                         .withnode(DeclarationNode, fromparsed=2)
        except InvalidSyntax:
            return parser.keyword()

    def typehint(parser):
        return parser.match('<').type().match('>')

    def type(parser):
        parser = parser.identifier().withnode(TypeNode, fromparsed=1)
        with OPTIONAL:
            parser = parser.match('[').nodelist(Parser.type).match(']') \
                           .withnode(TypeNode, fromparsed=2)
        return parser

    def target(parser):
        mode = ''
        with OPTIONAL:
            parser, mode = parser.choices('nonlocal', 'const', parse=True).popparsed()
        return parser.identifier() \
                     .withnode(Target, fromparsed=1, mode=mode)

    def keyword(parser):
        items = (
            Parser.if_,
            Parser.case,
            Parser.for_,
            Parser.while_,
            Parser.iter,
            Parser.do,
            Parser.object_,
            Parser.exception,
            Parser.mutable,
            Parser.return_,
            Parser.yield_,
            Parser.yieldfrom,
            Parser.break_,
            Parser.continue_,
            Parser.lambda_,
            Parser.boolor
        )
        for item in items:
            try:
                return item(parser)
            except InvalidSyntax as e:
                exception = e
        raise exception

    def if_(parser):
        parser = parser.match('if').assignment().match('then').keyword()
        try:
            parser = parser.match('else').keyword()
        except InvalidSyntax:
            parser = parser.addparsed(None)
        return parser.withnode(IfNode, fromparsed=3)

    def case(parser):
        parser = parser.match('case').assignment().match('in').mapping()
        try:
            parser = parser.match('else').keyword()
        except InvalidSyntax:
            parser = parser.addparsed(None)
        return parser.withnode(CaseNode, fromparsed=3)

    def for_(parser):
        return parser.match('for').vars().match('in').keyword().block() \
                     .withnode(ForNode, fromparsed=3)

    def vars(parser):
        try:
            return parser.match('(').nodelist(Parser.identifier).match(')')
        except InvalidSyntax:
            return parser.identifier()

    def while_(parser):
        return parser.match('while').assignment().block() \
                     .withnode(WhileNode, fromparsed=2)

    def iter(parser):
        return parser.match('iter').keyword() \
                     .withnode(IterNode, fromparsed=1)

    def do(parser):
        return parser.match('do').block() \
                     .withnode(DoNode, fromparsed=1)

    def object_(parser):
        return parser.match('object').block() \
                     .withnode(ObjectNode, fromparsed=1)

    def exception(parser):
        return parser.match('exception').block() \
                     .withnode(ExceptionNode, fromparsed=1)

    def mutable(parser):
        return parser.match('mutable').keyword() \
                     .withnode(IterNode, fromparsed=1)

    def return_(parser):
        return parser.match('return').keyword() \
                     .withnode(ReturnNode, fromparsed=1)

    def yield_(parser):
        return parser.match('yield').assignment() \
                     .withnode(YieldNode, fromparsed=1)

    def yieldfrom(parser):
        return parser.match('yield').match('from').assignment() \
                     .withnode(YieldFromNode, fromparsed=1)

    def break_(parser):
        return parser.match('break') \
                     .withnode(BreakNode)

    def continue_(parser):
        return parser.match('continue') \
                     .withnode(ContinueNode)

    def lambda_(parser):
        parser, params = parser
        parser, returns = parser
        return parser.match('(').nodelist(Parser.param).match(')').match('->').keyword() \
                     .withnode(LambdaNode, fromparsed=2)

    def param(parser):
        try:
            return parser.kwparam()
        except InvalidSyntax:
            return parser.vparam()

    def kwparam(parser):
        parser = parser.typehint()
        try:
            return parser.match('**').identifier() \
                         .withnode(DeclarationNode, fromparsed=2) \
                         .withnode(UnaryOpNode, '**', fromparsed=1)
        except InvalidSyntax:
            parser, typehint = parser.popparsed()
            return parser.identifier() \
                         .withnode(Target, fromparsed=1, typehint=typehint)
                         .match('=').keyword() \
                         .withnode(AssignmentNode, fromparsed=2)

    def vparam(parser):
        parser = parser.typehint()
        try:
            return parser.match('*').identifier() \
                         .withnode(DeclarationNode, fromparsed=2) \
                         .withnode(UnaryOpNode, '*', fromparsed=1)
        except InvalidSyntax:
            return parser.identifier() \
                         .withnode(DeclarationNode, fromparsed=2)

    def boolor(parser):
        return parser.rightrecurse('or', Parser.boolxor)

    def boolxor(parser):
        return parser.rightrecurse('xor', Parser.booland)

    def booland(parser):
        return parser.rightrecurse('and', Parser.comparison)

    def comparison(parser):
        # Need to work out what to do with 'is', 'is not', 'in', 'not in'
        return parser.rightrecurse(('<', '<=', '>', '>=', '==', '!='), Parser.bitor)

    def bitor(parser):
        return parser.leftrecurse('|', Parser.bitxor)

    def bitxor(parser):
        return parser.leftrecurse('^', Parser.bitand)

    def bitand(parser):
        return parser.leftrecurse('&', Parser.shift)

    def shift(parser):
        return parser.leftrecurse(('<<', '>>'), Parser.addition)

    def addition(parser):
        return parser.leftrecurse(('+', '-'), Parser.product)

    def product(parser):
        return parser.leftrecurse(('*', '/'), Parser.modulus)

    def modulus(parser):
        return parser.leftrecurse('%', Parser.exponent)

    def exponent(parser):
        return parser.rightrecurse('**', Parser.unary)

    def unary(parser):
        try:
            return parser.choices('not', '!', '-', parse=True).unary() \
                         .withnode(UnaryOpNode, fromparsed=2)
        except InvalidSyntax:
            return parser.primary()

    def primary(parser):
        parser = parser.atom()
        with OPTIONAL:
            while True:
                try:
                    parser = parser.match('.').identifier() \
                                   .withnode(LookupNode, fromparsed=2)
                except InvalidSyntax:
                    try:
                        parser = parser.match('(').nodelist(Parser.arg).match(')') \
                                       .withnode(CallNode, fromparsed=2)
                        obj = CallNode(obj, args)
                    except InvalidSyntax:
                        # Might change SubscriptNode
                        parser, subscript = parser.list().popparsed()
                        parser = parser.withnode(SubscriptNode, fromparsed=1, subscript=subscript.items)
        return parser

    def arg(parser):
        try:
            return parser.kwarg()
        except InvalidSyntax:
            return parser.varg()

    def kwarg(parser):
        try:
            return parser.match('**').keyword() \
                         .withnode(UnaryOpNode, '**', fromparsed=1)
        except InvalidSyntax:
            return parser.identifier() \
                         .withnode(Target, fromparsed=1) \
                         .match('=').keyword() \
                         .withnode(AssignmentNode, fromparsed=2)

    def varg(parser):
        try:
            return parser.match('*').keyword() \
                         .withnode(UnaryOpNode, '*', fromparsed=1)
        except InvalidSyntax:
            return parser.keyword()

    def atom(parser):
        items = (
            Parser.mapping,
            Parser.block,
            Parser.list,
            Parser.group,
            Parser.tuple,
            Parser.literal
        )
        for item in items:
            try:
                return item(parser)
            except InvalidSyntax as e:
                exception = e
        raise exception

    def mapping(parser):
        parser = parser
        return parser.match('{').nodelist(Parser.pair).match('}') \
                     .withnode(MappingNode, fromparsed=1)

    def pair(parser):
        return parser.assignment().match(':').assignment() \
                     .withnode(PairNode, fromparsed=2)

    def block(parser):
        return parser.match('{').nodelist(Parser.assignment).match('}') \
                     .withnode(BlockNode, fromparsed=1)

    def list(parser):
        try:
            return parser.match('[').range().match(']') \
                         .withnode(ListNode, fromparsed=1)
        except InvalidSyntax:
            return parser.match('[').nodelist(Parser.assignment).match(']') \
                         .withnode(ListNode fromparsed=1)

    def range(parser):
        parser = parser.assignment().match('..')
        try:
            parser = parser.keyword()
        except InvalidSyntax:
            parser = parser.addparsed(None)
        try:
            parser = parser.match(',').keyword()
        except InvalidSyntax:
            parser = parser.addparsed(1)
        return parser.withnode(Range, fromparsed=3)

    def group(parser):
        return parser.match('(').keyword().match(')') \
                     .withnode(GroupingNode, fromparsed=1)

    def tuple(parser):
        return parser.match('(').nodelist(Parser.assignment).match(')') \
                     .withnode(TupleNode, fromparsed=1)

    def literal(parser):
        items = (
            Parser.identifier,
            Parser.string,
            Parser.number,
            Parser.boolean,
            Parser.none
        )
        for item in items:
            try:
                return item(parser)
            except InvalidSyntax as e:
                exception = e
        raise exception

    def identifier(parser):
        return parser.match(IDENTIFIER, 'identifier', parse=True) \
                     .withnode(IdentifierNode, fromparsed=1)

    def string(parser):
        return parser.match(STRING, 'string', parse=True) \
                     .withnode(StringNode, string)

    def number(parser):
        return parser.match(NUMBER, 'number', parse=True) \
                     .withnode(NumberNode, number)

    def boolean(parser):
        return parser.choices('true', 'false', parse=True) \
                     .withnode(BooleanNode, boolean)

    def none(parser):
        return parser.match('none').withnode(NoneNode)
