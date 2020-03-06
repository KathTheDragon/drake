import contextlib, re
from dataclasses import dataclass, field
from .parsetree2 import *

## Tokens
WHITESPACE = re.compile(r'[^\S\r\n]*')
COMMENT = re.compile('(?m)//.*$')
NEWLINE = re.compile(r'\r\n?|\n')
EOF = re.compile(r'$(?![\r\n])')
IDENTIFIER = re.compile(r'[a-zA-Z_]\w*[!?]?')
_STRING = r'(?:[^\\\n]|\\.)*?'
STRING = re.compile(fr'\'{_STRING}\'|\"{_STRING}\"')
BINARY = re.compile(r'0b(?:_?[01])+')
OCTAL = re.compile(r'0o(?:_?[0-7])+')
HEXADECIMAL = re.compile('0x(?:_?[0-9a-fA-F])+')
DECIMAL = re.compile(r'[0-9](?:_?[0-9])*(?:\.[0-9](?:_?[0-9])*)?(?:[eE][+-]?[0-9](?:_?[0-9])*)?[jJ]?')

AUGMENTED_ASSIGNMENT = '|= ^= &= <<= >>= += -= *= /= %= **='.split()
RESERVED = [
    'and',
    'as',
    'break',
    'case',
    'catch',
    'const',
    'continue',
    'do',
    'else',
    'enum',
    'exception',
    'false',
    'finally',
    'flags'
    'for',
    'from',
    'if',
    'in',
    'is',
    'iter',
    'module',
    'mutable',
    'none',
    'nonlocal',
    'not',
    'object',
    'or',
    'pass',
    'return',
    'self',
    'then',
    'throw',
    'true',
    'try',
    'while',
    'xor',
    'yield',
]

## Exceptions
class ParseFailed(Exception):
    'Exception to signify a parse attempt failed and backtracking should occur'

class InvalidSyntax(Exception):
    def __init__(self, error, parser):
        linenum, column = parser.linenum+1, parser.column+1
        self.message = f'{error} @ {linenum}:{column}'
        self.linenum = linenum
        self.column = column

    def __str__(self):
        return self.message

def Expected(expected, parser):
    source, cursor = parser.source, parser.cursor
    if cursor < len(source):
        error = f'expected {expected}, got {parser.source[parser.cursor]}'
    else:
        error = f'expected {expected}, got EOF'
    return InvalidSyntax(error, parser)

## Context managers
OPTIONAL = contextlib.suppress(ParseFailed)

## Helper functions
def List(*args):
    return list(args)

## Classes
@dataclass
class Parser:
    source: str
    cursor: int = 0
    linenum: int = 0
    column: int = 0
    parsed: tuple = ()

    @property
    def location(parser):
        return parser.linenum, parser.column

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
            parser.parsed, args = parsed[:-fromparsed], args+parsed[-fromparsed:]
        return parser.addparsed(nodeclass(*args, **kwargs))

    # Basic matching methods
    def raw_match(parser, pattern, text, parse=False):
        match = pattern.match(parser.source, parser.cursor)
        if match is None:
            raise ParseFailed()
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
            if isinstance(token, tuple):
                token, text = token
            else:
                text = ''
            try:
                return parser.match(token, text, parse=parse)
            except ParseFailed as e:
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
            except ParseFailed:
                if num == 1:
                    raise
        except ParseFailed:
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
        return parser.withnode(List, fromparsed=num)

    def leftrecurse(parser, operators, operand):
        location = parser.location
        parser = operand(parser)
        with OPTIONAL:
            while True:
                parser = operand(parser.choices(*operators, parse=True)) \
                        .withnode(BinaryOpNode, location, fromparsed=3)
        return parser

    def rightrecurse(parser, operators, operand):
        location = parser.location
        parser = operand(parser)
        with OPTIONAL:
            parser = parser.choices(*operators, parse=True).rightrecurse(operators, operand) \
                           .withnode(BinaryOpNode, location, fromparsed=3)
        return parser

    # Node matching methods
    def program(parser):
        return parser.nodelist(Parser.assignment).raw_match(EOF, 'eof') \
                     .withnode(BlockNode, parser.location, fromparsed=1)

    def assignment(parser):
        try:
            try:
                _parser = parser.match('(').nodelist(Parser.target).match(')')
            except ParseFailed:
                _parser = parser.target()
            return _parser.match('=').assignment() \
                          .withnode(AssignmentNode, parser.location, fromparsed=2)
        except ParseFailed:
            try:
                # There must be a better way
                _parser, target = parser.target().popparsed()
                _parser = _parser.choices(*AUGMENTED_ASSIGNMENT, parse=True).assignment() \
                                 .withnode(BinaryOpNode, parser.location, target, fromparsed=2)
                return _parser.withnode(AssignmentNode, parser.location, target, fromparsed=1)
            except ParseFailed:
                return parser.declaration()

    def target(parser):
        location = parser.location
        mode = ''
        with OPTIONAL:
            parser, mode = parser.choices('nonlocal', 'const', parse=True).popparsed()
        return parser.identifier() \
                     .withnode(Target, location, fromparsed=1, mode=mode)

    def declaration(parser):
        try:
            return parser.typehint().identifier() \
                         .withnode(DeclarationNode, parser.location, fromparsed=2)
        except ParseFailed:
            return parser.keyword()

    def typehint(parser):
        return parser.match('<').type().match('>')

    def type(parser):
        location = parser.location
        parser = parser.identifier() \
                       .withnode(TypeNode, location, fromparsed=1)
        with OPTIONAL:
            parser = parser.match('[').nodelist(Parser.type).match(']') \
                           .withnode(TypeNode, location, fromparsed=2)
        return parser

    def keyword(parser):
        items = (
            Parser.if_,
            Parser.case,
            Parser.try_,
            Parser.for_,
            Parser.while_,
            Parser.iter,
            Parser.do,
            Parser.object_,
            Parser.enum,
            Parser.module,
            Parser.exception,
            Parser.mutable,
            Parser.throw,
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
            except ParseFailed as e:
                exception = e
        raise exception

    def if_(parser):
        location = parser.location
        parser = parser.match('if').assignment().match('then').keyword()
        try:
            parser = parser.match('else').keyword()
        except ParseFailed:
            parser = parser.addparsed(None)
        return parser.withnode(IfNode, location, fromparsed=3)

    def case(parser):
        location = parser.location
        parser = parser.match('case').assignment().match('in').mapping()
        try:
            parser = parser.match('else').keyword()
        except ParseFailed:
            parser = parser.addparsed(None)
        return parser.withnode(CaseNode, location, fromparsed=3)

    def try_(parser):
        location = parser.location
        parser = parser.match('try').assignment()
        try:
            parser = parser.addparsed([]).match('finally').assignment()
        except ParseFailed:
            num = 0
            try:
                while True:
                    parser_ = parser.match('catch').identifier()
                    try:
                        parser_ = parser_.match('as').identifier()
                    except ParseFailed:
                        parser_ = parser_.addparsed(None)
                    parser = parser_.assignment() \
                                    .withnode(CatchNode, parser.location, fromparsed=3)
                    num += 1
            except ParseFailed as e:
                if not num:
                    raise
            parser = parser.withnode(List, fromparsed=num)
            try:
                parser = parser.match('finally').assignment()
            except ParseFailed:
                parser = parser.addparsed(None)
        return parser.withnode(TryNode, location, fromparsed=3)

    def for_(parser):
        return parser.match('for').vars().match('in').keyword().block() \
                     .withnode(ForNode, parser.location, fromparsed=3)

    def vars(parser):
        try:
            return parser.match('(').nodelist(Parser.identifier).match(')')
        except ParseFailed:
            return parser.identifier()

    def while_(parser):
        return parser.match('while').assignment().block() \
                     .withnode(WhileNode, parser.location, fromparsed=2)

    def iter(parser):
        return parser.match('iter').keyword() \
                     .withnode(IterNode, parser.location, fromparsed=1)

    def do(parser):
        return parser.match('do').block() \
                     .withnode(DoNode, parser.location, fromparsed=1)

    def object_(parser):
        return parser.match('object').block() \
                     .withnode(ObjectNode, parser.location, fromparsed=1)

    def enum(parser):
        location = parser.location
        parser = parser.match('enum')
        try:
            parser = parser.match('flags').addparsed(True)
        except ParseFailed:
            parser = parser.addparsed(False)
        return parser.match('{').nodelist(Parser.enumitem).match('}') \
                     .withnode(EnumNode, location, fromparsed=2)

    def enumitem(parser):
        location = parser.location
        parser = parser.identifier()
        try:
            parser = parser.match('=').number()
        except ParseFailed:
            parser = parser.addparsed(None)
        return parser.withnode(PairNode, location, fromparsed=2)

    def module(parser):
        return parser.match('module').block() \
                     .withnode(ModuleNode, parser.location, fromparsed=1)

    def exception(parser):
        return parser.match('exception').block() \
                     .withnode(ExceptionNode, parser.location, fromparsed=1)

    def mutable(parser):
        location = parser.location
        parser = parser.match('mutable')
        items = (
            Parser.object_,
            Parser.mapping,
            Parser.list,
            Parser.tuple,
            Parser.string
        )
        for item in items:
            try:
                return item(parser).withnode(MutableNode, location, fromparsed=1)
            except ParseFailed as e:
                exception = e
        raise exception

    def throw(parser):
        return parser.match('throw').keyword() \
                     .withnode(ThrowNode, parser.location, fromparsed=1)

    def return_(parser):
        return parser.match('return').keyword() \
                     .withnode(ReturnNode, parser.location, fromparsed=1)

    def yield_(parser):
        return parser.match('yield').assignment() \
                     .withnode(YieldNode, parser.location, fromparsed=1)

    def yieldfrom(parser):
        return parser.match('yield').match('from').assignment() \
                     .withnode(YieldFromNode, parser.location, fromparsed=1)

    def break_(parser):
        return parser.match('break') \
                     .withnode(BreakNode, parser.location)

    def continue_(parser):
        return parser.match('continue') \
                     .withnode(ContinueNode, parser.location)

    def pass_(parser):
        return parser.match('pass') \
                     .withnode(PassNode, parser.location)

    def lambda_(parser):
        return parser.match('(').nodelist(Parser.param).match(')').match('->').keyword() \
                     .withnode(LambdaNode, parser.location, fromparsed=2)

    def param(parser):
        try:
            return parser.kwparam()
        except ParseFailed:
            return parser.vparam()

    def kwparam(parser):
        location = parser.location
        parser = parser.typehint()
        try:
            return parser.match('**').identifier() \
                         .withnode(DeclarationNode, location, fromparsed=2) \
                         .withnode(UnaryOpNode, location, '**', fromparsed=1)
        except ParseFailed:
            return parser.identifier() \
                         .withnode(DeclarationNode, location, fromparsed=2) \
                         .match('=').keyword() \
                         .withnode(PairNode, location, fromparsed=2)

    def vparam(parser):
        location = parser.location
        parser = parser.typehint()
        try:
            return parser.match('*').identifier() \
                         .withnode(DeclarationNode, location, fromparsed=2) \
                         .withnode(UnaryOpNode, location, '*', fromparsed=1)
        except ParseFailed:
            return parser.identifier() \
                         .withnode(DeclarationNode, location, fromparsed=2)

    def boolor(parser):
        return parser.rightrecurse('or', Parser.boolxor)

    def boolxor(parser):
        return parser.rightrecurse('xor', Parser.booland)

    def booland(parser):
        return parser.rightrecurse('and', Parser.inclusion)

    # Have to special-case these two because of the multi-word operators
    def inclusion(parser):
        location = parser.location
        parser = parser.identity()
        with OPTIONAL:
            try:
                _parser = parser.match('not').match('in').addparsed('not in')
            except ParseFailed:
                _parser = parser.match('in', parse=True)
            parser = _parser.inclusion() \
                            .withnode(BinaryOpNode, location, fromparsed=3)
        return parser

    def identity(parser):
        location = parser.location
        parser = parser.comparison()
        with OPTIONAL:
            try:
                _parser = parser.match('is').match('not').addparsed('is not')
            except ParseFailed:
                _parser = parser.match('is', parse=True)
            parser = _parser.identity() \
                            .withnode(BinaryOpNode, location, fromparsed=3)
        return parser

    def comparison(parser):
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
                         .withnode(UnaryOpNode, parser.location, fromparsed=2)
        except ParseFailed:
            return parser.primary()

    def primary(parser):
        location = parser.location
        parser = parser.atom()
        with OPTIONAL:
            while True:
                try:
                    parser = parser.match('.').identifier() \
                                   .withnode(LookupNode, location, fromparsed=2)
                except ParseFailed:
                    try:
                        parser = parser.match('(').nodelist(Parser.arg).match(')') \
                                       .withnode(CallNode, location, fromparsed=2)
                        obj = CallNode(obj, args)
                    except ParseFailed:
                        # Might change SubscriptNode
                        parser, subscript = parser.list().popparsed()
                        parser = parser.withnode(SubscriptNode, location, fromparsed=1, subscript=subscript.items)
        return parser

    def arg(parser):
        try:
            return parser.kwarg()
        except ParseFailed:
            return parser.varg()

    def kwarg(parser):
        try:
            return parser.match('**').keyword() \
                         .withnode(UnaryOpNode, parser.location, '**', fromparsed=1)
        except ParseFailed:
            return parser.identifier().match('=').keyword() \
                         .withnode(PairNode, parser.location, fromparsed=2)

    def varg(parser):
        try:
            return parser.match('*').keyword() \
                         .withnode(UnaryOpNode, parser.location, '*', fromparsed=1)
        except ParseFailed:
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
            except ParseFailed as e:
                exception = e
        raise exception

    def mapping(parser):
        return parser.match('{').nodelist(Parser.pair).match('}') \
                     .withnode(MappingNode, parser.location, fromparsed=1)

    def pair(parser):
        return parser.assignment().match(':').assignment() \
                     .withnode(PairNode, parser.location, fromparsed=2)

    def block(parser):
        return parser.match('{').nodelist(Parser.assignment).match('}') \
                     .withnode(BlockNode, parser.location, fromparsed=1)

    def list(parser):
        try:
            return parser.match('[').range().match(']') \
                         .withnode(ListNode, parser.location, fromparsed=1)
        except ParseFailed:
            return parser.match('[').nodelist(Parser.assignment).match(']') \
                         .withnode(ListNode, parser.location, fromparsed=1)

    def range(parser):
        location = parser.location
        parser = parser.assignment().match('..')
        try:
            parser = parser.keyword()
        except ParseFailed:
            parser = parser.addparsed(None)
        try:
            parser = parser.match(',').keyword()
        except ParseFailed:
            parser = parser.addparsed(1)
        return parser.withnode(Range, location, fromparsed=3)

    def group(parser):
        return parser.match('(').keyword().match(')') \
                     .withnode(GroupingNode, parser.location, fromparsed=1)

    def tuple(parser):
        return parser.match('(').nodelist(Parser.assignment).match(')') \
                     .withnode(TupleNode, parser.location, fromparsed=1)

    def literal(parser):
        items = (
            Parser.string,
            Parser.number,
            Parser.boolean,
            Parser.none,
            Parser.identifier
        )
        for item in items:
            try:
                return item(parser)
            except ParseFailed as e:
                exception = e
        raise exception

    def string(parser):
        return parser.match(STRING, 'string', parse=True) \
                     .withnode(StringNode, parser.location, fromparsed=1)

    def number(parser):
        return parser.choices(
                        (BINARY, 'binary'),
                        (OCTAL, 'octal'),
                        (HEXADECIMAL, 'hexadecimal'),
                        (DECIMAL, 'decimal'),
                        parse=True
                    ).withnode(NumberNode, parser.location, fromparsed=1)

    def boolean(parser):
        return parser.choices('true', 'false', parse=True) \
                     .withnode(BooleanNode, parser.location, fromparsed=1)

    def none(parser):
        return parser.match('none') \
                     .withnode(NoneNode, parser.location)

    def identifier(parser):
        location = parser.location
        parser, name = parser.match(IDENTIFIER, 'identifier', parse=True).popparsed()
        if name in RESERVED:
            raise ParseFailed()
        return parser.withnode(IdentifierNode, location, name)
