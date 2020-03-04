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
STRING = re.compile(fr'\'{STRING}\'|\"{STRING}\"')
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
    parsed: Any = None

    def __iter__(parser):
        return parser, parser.parsed

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

    def withnode(parser, nodeclass, *args, **kwargs):
        return parser._with(parsed=nodeclass(*args, **kwargs))

    # Basic matching methods
    def raw_match(parser, pattern, text, parse=False):
        match = pattern.match(parser.source, parser.cursor)
        if match is None:
            raise Expected(text, parser)
        cursor = match.end()
        column = parser.column + (cursor - parser.cursor)
        if parse:
            return parser._with(cursor=cursor, column=column, parsed=match.group())
        else:
            return parser._with(cursor=cursor, column=column)

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
        parser = parser.match(NEWLINE, 'newline')._with(linenum=parser.linenum+1, column=0)
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
        parser, _item = item(parser)
        try:
            items = []
            try:
                while True:
                    parser, _item = item(parser.newline())
                    items.append(_item)
            except InvalidSyntax:
                if not items:
                    raise
        except InvalidSyntax:
            items = []
            with OPTIONAL:
                while True:
                    _parser = parser.match(',')
                    with OPTIONAL:
                        _parser = _parser.newline()
                    parser, _item = item(_parser)
                    items.append(_item)
            with OPTIONAL:
                parser = parser.match(',')
        with OPTIONAL:
            parser = parser.newline()
        return parser._with(parsed=[item]+items])

    def leftrecurse(parser, operators, operand):
        parser, left = operand(parser)
        with OPTIONAL:
            while True:
                _parser, op = parser.choices(*operators, parse=True)
                parser, right = operand(_parser)
                left = BinaryOpNode(left, op, right)
        return parser._with(parsed=left)

    def rightrecurse(parser, operators, operand):
        parser, left = operand(parser)
        with OPTIONAL:
            _parser, op = parser.choices(*operators, parse=True)
            parser, right = _parser.rightrecurse(operators, operand)
            left = BinaryOpNode(left, op, right)
        return parser._with(parsed=left)

    # Node matching methods
    def program(parser):
        return BlockNode(parser.nodelist(Parser.assignment).raw_match(EOF, 'eof').parsed)

    def assignment(parser):
        try:
            try:
                _parser, targets = parser.match('(').nodelist(Parser.target).match(')')
            except InvalidSyntax:
                _parser, target = parser.target()
                targets = [target]
            _parser, value = _parser.match('=').assignment()
            return _parser.withnode(AssignmentNode, targets, value)
        except InvalidSyntax:
            try:
                _parser, target = parser.target()
                _parser, op = _parser.choices(*AUGMENTED_ASSIGNMENT, parse=True)
                _parser, value = _parser.assignment()
                value = BinaryOpNode(target, op.rstrip('='), value)
                return _parser.withnode(AssignmentNode, targets, value)
            except InvalidSyntax:
                return parser.declaration()

    def declaration(parser):
        try:
            _parser, typehint = parser.typehint()
            _parser, name = _parser.identifier()
            return _parser.withnode(DeclarationNode, typehint, name)
        except InvalidSyntax:
            return parser.keyword()

    def typehint(parser):
        return parser.match('<').type().match('>')

    def type(parser):
        parser, type = parser.identifier()
        with OPTIONAL:
            parser, params = parser.match('[').nodelist(Parser.type).match(']')
            type = TypeNode(type, params)
        return parser._with(parsed=type)

    def target(parser):
        mode = ''
        with OPTIONAL:
            parser, mode = parser.choices('nonlocal', 'const', parse=True)
        parser, name = parser.identifier()
        return parser.withnode(Target, mode, name)

    def keyword(parser):
        items = (
            Parser.if_,
            Parser.case,
            Parser.for_,
            Parser.while_,
            Parser.iter,
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
        parser, condition = parser.match('if').assignment()
        parser, then = parser.match('then').keyword()
        default = None
        with OPTIONAL:
            parser, default = parser.match('else').keyword()
        return parser.withnode(IfNode, condition, then, default)

    def case(parser):
        parser, value = parser.match('case').assignment()
        parser, cases = parser.match('in').mapping()
        default = None
        with OPTIONAL:
            parser, default = parser.match('else').keyword()
        return parser.withnode(CaseNode, value, cases, default)

    def for_(parser):
        parser, vars = parser.match('for').vars()
        parser, container = parser.match('in').keyword()
        parser, body = parser.block()
        return parser.withnode(ForNode, vars, container, body)

    def vars(parser):
        try:
            return parser.match('(').nodelist(Parser.identifier).match(')')
        except InvalidSyntax:
            return parser.identifier()

    def while_(parser):
        parser, condition = parser.match('while').assignment()
        parser, body = parser.block()
        return parser.withnode(WhileNode, condition, body)

    def iter(parser):
        parser, expression = parser.match('iter').keyword()
        return parser.withnode(IterNode, expression)

    def object_(parser):
        parser, definition = parser.match('object').block()
        return parser.withnode(ObjectNode, definition)

    def exception(parser):
        parser, definition = parser.match('exception').block()
        return parser.withnode(ExceptionNode, definition)

    def mutable(parser):
        parser, expression = parser.match('mutable').keyword()
        return parser.withnode(IterNode, expression)

    def return_(parser):
        parser, expression = parser.match('return').keyword()
        return parser.withnode(ReturnNode, expression)

    def yield_(parser):
        parser, expression = parser.match('yield').assignment()
        return parser.withnode(YieldNode, expression)

    def yieldfrom(parser):
        parser, expression = parser.match('yield').match('from').assignment()
        return parser.withnode(YieldFromNode, expression)

    def break_(parser):
        return parser.match('break').withnode(BreakNode)

    def continue_(parser):
        return parser.match('continue').withnode(ContinueNode)

    def lambda_(parser):
        parser, params = parser.match('(').nodelist(Parser.param).match(')')
        parser, returns = parser.match('->').keyword()
        return parser.withnode(LambdaNode, params, returns)

    def param(parser):
        try:
            return parser.kwparam()
        except InvalidSyntax:
            return parser.vparam()

    def kwparam(parser):
        parser, typehint = parser.typehint()
        try:
            parser, name = parser.match('**').identifier()
            return parser._with(parsed=UnaryOpNode('**', DeclarationNode(typehint, name)))
        except InvalidSyntax:
            parser, name = parser.identifier()
            parser, expression = parser.match('=').keyword()
            return parser.withnode(DeclarationNode, typehint, name)

    def vparam(parser):
        parser, typehint = parser.typehint()
        try:
            parser, name = parser.match('*').identifier()
            return parser._with(parsed=UnaryOpNode('*', DeclarationNode(typehint, name)))
        except InvalidSyntax:
            parser, name = parser.identifier()
            return parser.withnode(DeclarationNode, typehint, name)

    def boolor(parser):
        return parser.rightrecurse('or', Parser.boolxor)

    def boolxor(parser):
        return parser.recurse('xor', Parser.booland)

    def booland(parser):
        return parser.recurse('and', Parser.comparison)

    def comparison(parser):
        # Need to work out what to do with 'is', 'is not', 'in', 'not in'
        return parser.recurse(('<', '<=', '>', '>=', '==', '!='), Parser.bitor)

    def bitor(parser):
        return parser.recurse('|', Parser.bitxor)

    def bitxor(parser):
        return parser.recurse('^', Parser.bitand)

    def bitand(parser):
        return parser.recurse('&', Parser.shift)

    def shift(parser):
        return parser.recurse(('<<', '>>'), Parser.addition)

    def addition(parser):
        return parser.recurse(('+', '-'), Parser.product)

    def product(parser):
        return parser.recurse(('*', '/'), Parser.modulus)

    def modulus(parser):
        return parser.recurse('%', Parser.exponent)

    def exponent(parser):
        return parser.recurse('**', Parser.unary)

    def unary(parser):
        try:
            _parser, operator = parser.choices('not', '!', '-', parse=True)
            _parser, operand = _parser.unary()
            return _parser.withnode(UnaryOpNode, operator, operand)
        except InvalidSyntax:
            return parser.primary()

    def primary(parser):
        parser, obj = parser.atom()
        with OPTIONAL:
            while True:
                try:
                    parser, name = parser.match('.').identifier()
                    obj = LookupNode(obj, name)
                except InvalidSyntax:
                    try:
                        parser, args = parser.match('(').nodelist(Parser.arg).match(')')
                        obj = CallNode(obj, args)
                    except InvalidSyntax:
                        parser, subscript = parser.list()
                        obj = SubscriptNode(obj, subscript.items)
        return parser._with(parsed=obj)

    def arg(parser):
        try:
            return parser.kwarg()
        except InvalidSyntax:
            return parser.varg()

    def kwarg(parser):
        try:
            parser, expr = parser.match('**').keyword()
            return parser._with(parsed=UnaryOpNode('**', expr))
        except InvalidSyntax:
            parser, name = parser.identifier()
            parser, expr = parser.match('=').keyword()
            return parser._with(parsed=AssignmentNode([Target(name)], expr))

    def varg(parser):
        try:
            parser, expr = parser.match('*').keyword()
            return parser._with(parsed=UnaryOpNode('*', expr))
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
        parser, pairs = parser.match('{').nodelist(Parser.pair).match('}')
        return parser.withnode(MappingNode, pairs)

    def pair(parser):
        parser, key = parser.assignment()
        parser, value = parser.match(':').assignment()
        return parser._with(PairNode(key, value))

    def block(parser):
        parser, exprs = parser.match('{').nodelist(Parser.assignment).match('}')
        return parser.withnode(BlockNode, exprs)

    def list(parser):
        try:
            parser, range = parser.match('[').range().match(']')
            return parser._with(parsed=ListNode([range]))
        except InvalidSyntax:
            parser, items = parser.match('[').nodelist(Parser.assignment).match(']')
            return parser.withnode(ListNode, items)

    def range(parser):
        parser, start = parser.assignment().match('..')
        end = None
        step = 1
        with OPTIONAL:
            parser, end = parser.keyword()
        with OPTIONAL:
            parser, step = parser.match(',').keyword()
        return parser.withnode(Range, start, end, step)

    def group(parser):
        parser, expr = parser.match('(').keyword().match(')')
        return parser.withnode(GroupingNode, expr)

    def tuple(parser):
        parser, items = parser.match('(').nodelist(Parser.assignment).match(')')
        return parser.withnode(TupleNode, items)

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
        parser, name = parser.match(IDENTIFIER, 'identifier', parse=True)
        return parser.withnode(IdentifierNode, name)

    def string(parser):
        parser, string = parser.match(STRING, 'string', parse=True)
        return parser.withnode(StringNode, string)

    def number(parser):
        parser, number = parser.match(NUMBER, 'number', parse=True)
        return parser.withnode(NumberNode, number)

    def boolean(parser):
        parser, boolean = parser.choices('true', 'false', parse=True)
        return parser.withnode(BooleanNode, boolean)

    def none(parser):
        return parser.match('none').withnode(NoneNode)
