import contextlib, re
from dataclasses import dataclass, field
from .parsetree import *

## Tokens
WHITESPACE = re.compile(r'[^\S\r\n]*')
COMMENT = re.compile('(?m://.*$)?')
NEWLINE = re.compile(r'\r\n?|\n')
EOF = re.compile(r'$(?![\r\n])')
IDENTIFIER = re.compile(r'[a-zA-Z_]\w*[!?]?')
_STRING = r'(?:[^\\\n]|\\.)*?'
STRING = re.compile(fr'\'{_STRING}\'|\"{_STRING}\"')
BINARY = re.compile(r'0b(?:_?[01])+')
OCTAL = re.compile(r'0o(?:_?[0-7])+')
HEXADECIMAL = re.compile('0x(?:_?[0-9a-fA-F])+')
DECIMAL = re.compile(r'[0-9](?:_?[0-9])*(?:\.[0-9](?:_?[0-9])*)?(?:[eE][+-]?[0-9](?:_?[0-9])*)?[jJ]?')

ASSIGNMENT = '= |= ^= &= <<= >>= += -= *= /= %= **='.split()
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
class ParserError(Exception):
    'Base class for errors related to parsing'

    def __init__(self, error, location=()):
        if location:
            linenum, column = location
            self.message = f'{error} @ {linenum}:{column}'
        else:
            linenum, column = None, None
            self.message = error
        self.linenum = linenum
        self.column = column

    def __str__(self):
        return self.message

class ParseFailed(ParserError):
    'Exception to signify a parse attempt failed and backtracking should occur'

    def __init__(self, pattern, location=()):
        self.pattern = pattern
        super().__init__(f'failure matching {pattern}', location)

class InvalidSyntax(ParserError):
    def __init__(self, error, location=()):
        super().__init__(error, location)

def Expected(expected, got='', parser=None):
    error = f'expected {expected}'
    if got:
        error += f', got {got}'
    elif parser:
        if cursor < len(source):
            source, cursor = parser.source, parser.cursor
            error += f', got {source[cursor]}'
        else:
            error += ', got EOF'
    if parser:
        return InvalidSyntax(error, parser)
    else:
        return InvalidSyntax

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
    parsed: tuple = ()

    @property
    def location(parser):
        linenum = 1
        end = 0
        for newline in NEWLINE.finditer(parser.source, 0, parser.cursor):
            linenum += 1
            end = newline.end()
        return linenum, (parser.cursor-end)+1

    def __getitem__(parser, item):
        return parser.parsed[item]

    #
    def _with(parser, cursor=None, parsed=None):
        if cursor is None:
            cursor = parser.cursor
        if parsed is None:
            parsed = parser.parsed
        return Parser(parser.source, cursor, parsed)

    def addparsed(parser, *parsed):
        return parser._with(parsed=parser.parsed+parsed)

    def withnode(parser, nodeclass, args=0, location=()):
        if args > 0:
            parsed, node = parser[:-args], nodeclass(*parser[-args:])
        else:
            parsed, node = parser[:], nodeclass()
        if location:
            node.location = location
        return parser._with(parsed=parsed+(node,))

    # Basic matching methods
    def raw_match(parser, pattern, text, parse=False):
        match = pattern.match(parser.source, parser.cursor)
        if match is None:
            raise ParseFailed(text, parser.location)
        parser = parser._with(cursor=match.end())
        if parse:
            return parser.addparsed(match.group())
        else:
            return parser

    def skip(parser):
        return parser.raw_match(WHITESPACE, 'whitespace').raw_match(COMMENT, 'comment')

    def match(parser, pattern, text='', parse=False):
        if isinstance(pattern, str):
            text = text or repr(pattern)
            pattern = re.compile(re.escape(pattern))
        return parser.raw_match(pattern, text, parse).skip()

    def newline(parser):
        parser = parser.raw_match(NEWLINE, 'newline').skip()
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
        try:
            parser = item(parser)
        except ParseFailed:
            return parser.addparsed([])
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
        return parser.withnode(List, args=num)

    def delimitedlist(parser, item, forcelist=False):
        try:
            return parser.match('(').nodelist(item).match(')')
        except ParseFailed:
            if forcelist:
                return item(parser).withnode(List, args=1)
            else:
                return item(parser)

    def leftrecurse(parser, operators, operand):
        if isinstance(operators, str):
            operators = (operators,)
        location = parser.location
        parser = operand(parser)
        with OPTIONAL:
            while True:
                parser = operand(parser.choices(*operators, parse=True)) \
                        .withnode(BinaryOpNode, args=3, location=location)
        return parser

    def rightrecurse(parser, operators, operand):
        if isinstance(operators, str):
            operators = (operators,)
        location = parser.location
        parser = operand(parser)
        with OPTIONAL:
            parser = parser.choices(*operators, parse=True).rightrecurse(operators, operand) \
                           .withnode(BinaryOpNode, args=3, location=location)
        return parser

    # Node matching methods
    def program(parser):
        return parser.nodelist(Parser.expression).raw_match(EOF, 'eof') \
                     .withnode(BlockNode, args=1, location=parser.location) \
                     .withnode(ModuleNode, args=1, location=parser.location)

    def expression(parser):
        items = (
            Parser.assignment,
            Parser.keyword,
            Parser.lambda_,
            Parser.declaration,
            Parser.boolor
        )
        for item in items:
            try:
                return item(parser)
            except ParseFailed as e:
                exception = e
        raise exception

    def assignment(parser):
        return parser.delimitedlist(Parser.target).choices(*ASSIGNMENT, parse=True).expression() \
                     .withnode(AssignmentNode, args=3, location=parser.location)

    def target(parser):
        location = parser.location
        try:
            parser = parser.choices('nonlocal', 'const', parse=True)
        except ParseFailed:
            parser = parser.addparsed('')
        try:
            parser = parser.typehint()
        except ParseFailed:
            parser = parser.addparsed(None)
        return parser.identifier() \
                     .withnode(TargetNode, args=3, location=location)

    def typehint(parser):
        return parser.match('<').type().match('>')

    def type(parser):
        location = parser.location
        parser = parser.identifier()
        try:
            parser = parser.match('[').nodelist(Parser.type).match(']')
        except ParseFailed:
            parser = parser.addparsed([])
        return parser.withnode(TypeNode, args=2, location=location)

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
            Parser.pass_
        )
        for item in items:
            try:
                return item(parser)
            except ParseFailed as e:
                exception = e
        raise exception

    def if_(parser):
        location = parser.location
        parser = parser.match('if').expression().match('then').expression()
        try:
            parser = parser.match('else').expression()
        except ParseFailed:
            parser = parser.addparsed(None)
        return parser.withnode(IfNode, args=3, location=location)

    def case(parser):
        location = parser.location
        parser = parser.match('case').primary().match('in').mapping()
        try:
            parser = parser.match('else').expression()
        except ParseFailed:
            parser = parser.addparsed(None)
        return parser.withnode(CaseNode, args=3, location=location)

    def try_(parser):
        location = parser.location
        parser = parser.match('try').expression()
        try:
            parser = parser.addparsed([]).match('finally').expression()
        except ParseFailed:
            num = 0
            try:
                while True:
                    parser_ = parser.match('catch').identifier()
                    try:
                        parser_ = parser_.match('as').identifier()
                    except ParseFailed:
                        parser_ = parser_.addparsed(None)
                    parser = parser_.expression() \
                                    .withnode(CatchNode, args=3, location=parser.location)
                    num += 1
            except ParseFailed as e:
                if not num:
                    raise
            parser = parser.withnode(List, args=num)
            try:
                parser = parser.match('finally').expression()
            except ParseFailed:
                parser = parser.addparsed(None)
        return parser.withnode(TryNode, args=3, location=location)

    def for_(parser):
        return parser.match('for').delimitedlist(Parser.identifier).match('in').expression().block() \
                     .withnode(ForNode, args=3, location=parser.location)

    def while_(parser):
        return parser.match('while').expression().block() \
                     .withnode(WhileNode, args=2, location=parser.location)

    def iter(parser):
        location = parser.location
        parser = parser.match('iter')
        items = (
            Parser.for_,
            Parser.while_,
            Parser.list
        )
        for item in items:
            try:
                return item(parser).withnode(IterNode, args=1, location=location)
            except ParseFailed as e:
                exception = e
        raise exception

    def do(parser):
        return parser.match('do').block() \
                     .withnode(DoNode, args=1, location=parser.location)

    def object_(parser):
        return parser.match('object').block() \
                     .withnode(ObjectNode, args=1, location=parser.location)

    def enum(parser):
        location = parser.location
        parser = parser.match('enum')
        try:
            parser = parser.match('flags').addparsed(True)
        except ParseFailed:
            parser = parser.addparsed(False)
        return parser.match('{').nodelist(Parser.enumitem).match('}') \
                     .withnode(EnumNode, args=2, location=location)

    def enumitem(parser):
        location = parser.location
        parser = parser.identifier()
        try:
            parser = parser.match('=').number()
        except ParseFailed:
            parser = parser.addparsed(None)
        return parser.withnode(PairNode, args=2, location=location)

    def module(parser):
        return parser.match('module').block() \
                     .withnode(ModuleNode, args=1, location=parser.location)

    def exception(parser):
        return parser.match('exception').block() \
                     .withnode(ExceptionNode, args=1, location=parser.location)

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
                return item(parser).withnode(MutableNode, args=1, location=location)
            except ParseFailed as e:
                exception = e
        raise exception

    def throw(parser):
        return parser.match('throw').expression() \
                     .withnode(ThrowNode, args=1, location=parser.location)

    def return_(parser):
        return parser.match('return').expression() \
                     .withnode(ReturnNode, args=1, location=parser.location)

    def yield_(parser):
        return parser.match('yield').expression() \
                     .withnode(YieldNode, args=1, location=parser.location)

    def yieldfrom(parser):
        return parser.match('yield').match('from').expression() \
                     .withnode(YieldFromNode, args=1, location=parser.location)

    def break_(parser):
        return parser.match('break') \
                     .withnode(BreakNode, location=parser.location)

    def continue_(parser):
        return parser.match('continue') \
                     .withnode(ContinueNode, location=parser.location)

    def pass_(parser):
        return parser.match('pass') \
                     .withnode(PassNode, location=parser.location)

    def lambda_(parser):
        return parser.delimitedlist(Parser.param, True).match('->').expression() \
                     .withnode(LambdaNode, args=2, location=parser.location)

    def param(parser):
        location = parser.location
        try:
            parser = parser.choices('*', '**', parse=True)
            op = True
        except ParseFailed:
            op = False
        parser = parser.addparsed(False).typehint().identifier() \
                       .withnode(DeclarationNode, args=3, location=location)
        if op:
            return parser.withnode(UnaryOpNode, args=2, location=location)
        else:
            with OPTIONAL:
                parser = parser.match('=').expression() \
                               .withnode(PairNode, args=2, location=location)
            return parser

    def declaration(parser):
        try:
            parser = parser.match('const').addparsed(True)
        except ParseFailed:
            parser = parser.addparsed(False)
        return parser.typehint().identifier() \
                     .withnode(DeclarationNode, args=3, location=parser.location)

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
                            .withnode(BinaryOpNode, args=3, location=location)
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
                            .withnode(BinaryOpNode, args=3, location=location)
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
                         .withnode(UnaryOpNode, args=2, location=parser.location)
        except ParseFailed:
            return parser.primary()

    def primary(parser):
        location = parser.location
        parser = parser.atom()
        with OPTIONAL:
            while True:
                try:
                    parser = parser.match('.').identifier() \
                                   .withnode(LookupNode, args=2, location=location)
                except ParseFailed:
                    try:
                        parser = parser.match('(').nodelist(Parser.arg).match(')') \
                                       .withnode(CallNode, args=2, location=location)
                    except ParseFailed:
                        try:
                            _parser = parser.range()
                        except ParseFailed:
                            _parser = parser.list()
                        parser = _parser.withnode(SubscriptNode, args=2, location=location)
        return parser

    def arg(parser):
        try:
            return parser.choices('*', '**', parse=True).expression() \
                         .withnode(UnaryOpNode, args=2, location=parser.location)
        except ParseFailed:
            try:
                return parser.identifier().match('=').expression() \
                             .withnode(PairNode, args=2, location=parser.location)
            except ParseFailed:
                return parser.expression()

    def atom(parser):
        items = (
            Parser.mapping,
            Parser.block,
            Parser.list,
            Parser.grouping,
            Parser.tuple,
            Parser.literal,
            Parser.identifier
        )
        for item in items:
            try:
                return item(parser)
            except ParseFailed as e:
                exception = e
        raise exception

    def mapping(parser):
        return parser.match('{').nodelist(Parser.pair).match('}') \
                     .withnode(MappingNode, args=1, location=parser.location)

    def pair(parser):
        return parser.expression().match(':').expression() \
                     .withnode(PairNode, args=2, location=parser.location)

    def block(parser):
        return parser.match('{').nodelist(Parser.expression).match('}') \
                     .withnode(BlockNode, args=1, location=parser.location)

    def list(parser):
        try:
            return parser.match('[').range().match(']')
        except ParseFailed:
            return parser.match('[').nodelist(Parser.expression).match(']') \
                         .withnode(ListNode, args=1, location=parser.location)

    def range(parser):
        location = parser.location
        parser = parser.primary().match('..')
        try:
            parser = parser.primary()
        except ParseFailed:
            parser = parser.addparsed(None)
        try:
            parser = parser.match(',').primary()
        except ParseFailed:
            parser = parser.addparsed(None)
        return parser.withnode(RangeNode, args=3, location=location)

    def grouping(parser):
        return parser.match('(').expression().match(')')

    def tuple(parser):
        return parser.match('(').nodelist(Parser.expression).match(')') \
                     .withnode(TupleNode, args=1, location=parser.location)

    def literal(parser):
        items = (
            Parser.string,
            Parser.number,
            Parser.boolean,
            Parser.none
        )
        for item in items:
            try:
                return item(parser)
            except ParseFailed as e:
                exception = e
        raise exception

    def string(parser):
        return parser.match(STRING, 'string', parse=True) \
                     .withnode(StringNode, args=1, location=parser.location)

    def number(parser):
        return parser.choices(
                        (BINARY, 'binary'),
                        (OCTAL, 'octal'),
                        (HEXADECIMAL, 'hexadecimal'),
                        (DECIMAL, 'decimal'),
                        parse=True
                    ).withnode(NumberNode, args=1, location=parser.location)

    def boolean(parser):
        return parser.choices('true', 'false', parse=True) \
                     .withnode(BooleanNode, args=1, location=parser.location)

    def none(parser):
        return parser.match('none') \
                     .withnode(NoneNode, location=parser.location)

    def identifier(parser):
        location = parser.location
        parser = parser.match(IDENTIFIER, 'identifier', parse=True)
        if parser[-1] in RESERVED:
            raise ParseFailed('identifier', location)
        return parser.withnode(IdentifierNode, args=1, location=location)
